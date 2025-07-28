import time
import json

import numpy as np
from enum import Enum

from qm import QuantumMachinesManager
from qm.octave import QmOctaveConfig
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.units import unit
u = unit(coerce_to_integer=True)

import qtl_control.qtl_station.station_nodes as qtl_nodes
from qtl_control.qtl_station.qm_config import generate_config

# === Taking care to kill QM whatever happens ===
import sys
import atexit
import signal
def kill_handler(*args):
    sys.exit(0)

signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)
# === END ===


class MockResHandles():
    mock_data = [np.array([1]), np.array([1]), 1]

    def __init__(self):
        self.gen = (_ for _ in [True, False])

    def wait_for_all_values(self):
        pass

    def get(self, measurement_key):
        class MockData:
            def fetch_all():
                return self.mock_data
        return MockData()
    
    def is_processing(self):
        return next(self.gen)

    def fetch_all(self):
        return self.mock_data
    
    def get_start_time(self):
        return time.time()

class MockQMJob():
    def __init__(self):
        self.result_handles = MockResHandles()

class MockQM():
    def execute(sefl, program):
        # Execute mock program
        return MockQMJob()

class MockQMManager():
    pass


class ReadoutType(Enum):
    average = 1
    single_shot = 2


class QTLStation:
    def __init__(self, config):
        # QM specific part
        qm_config = config["QMManager"]
        self.mock = qm_config.get("mock") or False

        # Get qm channel inputs and outputs
        hw_settings = qm_config["channels"]
        hw_rf_inputs = hw_settings["RF_in"]
        hw_rf_outputs = hw_settings["RF_out"]
        hw_analog_out = hw_settings["analog_out"]

        # Make channels
        self.rf_output_channels = {id: qtl_nodes.OctaveRFChannel(id) for id in hw_rf_outputs}
        self.rf_input_channels = {id: qtl_nodes.OctaveRFChannel(id) for id in hw_rf_inputs}
        self.analog_output_channels = {id: qtl_nodes.OPXAnalogChannel(id) for id in hw_analog_out}        
        
        # Get cryo connectivity
        cryo_config = config["cryostat"]

        # Get chip connectivity
        chip_config = config["chip"]
        
        # Make PL 
        # TODO: Currently assumes one probe line as magic 'PL' - might need to improve this
        pl_chip_config = chip_config.pop("PL")
        self.pl_config = {
            "PL": qtl_nodes.ProbeLine(
                self.rf_output_channels[cryo_config[pl_chip_config["input"]]],
                self.rf_input_channels[cryo_config[pl_chip_config["output"]]],
            )
        }
        # Make qubit config
        self.qubit_config = {
            id: qtl_nodes.TransmonQubit(
                drive=self.rf_output_channels[cryo_config[val["drive"]]],
                flux=self.analog_output_channels[cryo_config[fval]] if (fval:=val.get("flux")) else None
            ) for id, val in chip_config.items()
        }

        self.elements = []
        self.config = self.pl_config | self.qubit_config

        # Make config
        configuration = generate_config(
            self.elements,
            self.rf_output_channels,
            self.rf_input_channels,
            self.analog_output_channels,
            self.qubit_config
        )

        # For debug purposes
        with open("qtl_qm_config.json", "w+") as f:
            json.dump(configuration, f)

        if not self.mock:
            octave_config = QmOctaveConfig()
            octave_config.set_calibration_db("")
            self.qm_manager = QuantumMachinesManager(
                host=qm_config["host"],
                port=qm_config["port"],
                cluster_name=qm_config["cluster_name"],
                octave=octave_config
            )

            self.qm = self.qm_manager.open_qm(configuration)
            def exit_handler():
                print("Cleaning up, closing QM")
                self.qm.close()
            atexit.register(exit_handler)
        else:
            self.qm = MockQM()
            self.qm_manager = MockQMManager()


    def reload_config(self, elements, new_settings=None):
        self.elements = elements

        new_settings = new_settings or dict()
        # TODO: Only supports depth 2 dicts
        for elem, settings in new_settings.items():
            subtree = self.config[elem]
            for k, v in settings.items():
                if type(v) is dict:
                    for kk, vv in v.items():
                        subtree[k][kk] = vv
                else:
                    subtree[k] = v

        configuration = generate_config(
            self.elements,
            self.rf_output_channels,
            self.rf_input_channels,
            self.analog_output_channels,
            self.qubit_config
        )

        with open("qtl_qm_config.json", "w+") as f:
            json.dump(configuration, f)

        if not self.mock:
            self.qm.close()
            self.qm = self.qm_manager.open_qm(configuration)
        else:
            self.qm = MockQM()

    def print_tree(self):
        for element in self.elements:
            print(f"{element}:\n{self.config[element].get_tree(indent=1)}")
        print(f"PL:\n{self.pl_config["PL"].get_tree(indent=1)}")

    def execute(self, element, program, Navg, readout_type):
        if readout_type == ReadoutType.single_shot: # Single shot
            job = self.qm.execute(program)
            res_handles = job.result_handles
            res_handles.wait_for_all_values()
            I = res_handles.get("I").fetch_all()["value"]
            Q = res_handles.get("Q").fetch_all()["value"]

            S = u.demod2volts(I + 1.j * Q, self.config[element].readout_len)

        else: # Averaged
            job = self.qm.execute(program)
            results = fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live") if not self.mock else MockResHandles()
            while results.is_processing():
                I, Q, iteration = results.fetch_all()
                S = u.demod2volts(I + 1.j * Q, self.config[element].readout_len)
                progress_counter(iteration, Navg, start_time=results.get_start_time())

        return S


class change_station:
    def __init__(self, station):
        self.station = station

    def __enter__(self):
        pass

    def __exit__(self, exc_Type, exc_val, exc_tb):
        self.station.reload_config(self.station.elements)