import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
import yaml

from dataclasses import dataclass, fields
from typing import Optional

from qm.qua import *
from qm import QuantumMachinesManager
from qm.octave import QmOctaveConfig
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.units import unit
u = unit(coerce_to_integer=True)

from qtl_control.qtl_simple_experiments.qm_config import generate_config
from qtl_control.qtl_simple_experiments.database import FileSystemDB

import sys
import atexit
import signal
def kill_handler(*args):
    sys.exit(0)

signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)


class StationNode:
    def get_tree(self, indent=0):
        return "\n".join([
            f"{'\t'*indent}{field.name}: {self[field.name]}" if not issubclass(type(self[field.name]), StationNode)
            else f"{'\t'*indent}{field.name}:\n{self[field.name].get_tree(indent+1)}"
        for field in fields(self)
        ])

    def __getitem__(self, item):
        return getattr(self, item)
    
    def __setitem__(self, key, val):
        if hasattr(self, key):
            setattr(self, key, val)
        else:
            print(f"No attr {key}")


@dataclass
class OctaveRF(StationNode):
    channel_id: str
    LO_frequency: float
    gain: int


@dataclass
class OPXAnalog(StationNode):
    channel_id: str
    dc_volt: float


@dataclass
class ProbeLine(StationNode):
    input: OctaveRF
    output: OctaveRF
    LO_frequency: float

    def __setitem__(self, key, val):
        if getattr(self, key):
            if key == "LO_frequency":
                self.input.LO_frequency = val
                self.output.LO_frequency = val
            setattr(self, key, val)

@dataclass
class ReadoutDisc(StationNode):
    param_0: complex
    param_1: complex

    def discriminate_data(self, data):
        data["e_state"] = ((data["iq"] - self.param_0) * self.param_1).real


@dataclass
class TransmonQubit(StationNode):
    drive: OctaveRF
    frequency: float = 5.8e9
    X180_duration: int = 100
    X180_amplitude: float = 0.5
    flux: Optional[OPXAnalog] = None
    readout_frequency: float = 5.8e9
    readout_amplitude: float = 0.1
    readout_len: int = 2000
    readout_discriminator: Optional[ReadoutDisc] = None


class QTLQMSimpleStation:
    def __init__(self, config):
        qm_config = config["QMManager"]

        octave_config = QmOctaveConfig()
        octave_config.set_calibration_db("")
        self.qm_manager = QuantumMachinesManager(
            host=qm_config["host"],
            port=qm_config["port"],
            cluster_name=qm_config["cluster_name"],
            octave=octave_config
        )
        self.single_shot = False

        # Get values from the config
        hw_settings = qm_config["channels"]
        hw_rf_inputs = hw_settings["RF_in"]
        hw_rf_outputs = hw_settings["RF_out"]
        hw_analog_out = hw_settings["analog_out"]

        # Make channels
        self.rf_output_channels = {id: OctaveRF(id, 6e9, -20) for id in hw_rf_outputs}
        self.rf_input_channels = {id: OctaveRF(id, 6e9, 0) for id in hw_rf_inputs}
        self.analog_output_channels = {id: OPXAnalog(id, 0) for id in hw_analog_out}        
        
        # Get cryo connectivity
        cryo_config = config["cryostat"]

        # Get chip connectivity
        chip_config = config["chip"]
        
        # Make PL
        pl_chip_config = chip_config.pop("PL")
        self.pl_config = {
            "PL": ProbeLine(
                self.rf_output_channels[cryo_config[pl_chip_config["input"]]],
                self.rf_input_channels[cryo_config[pl_chip_config["output"]]],
                6e9
            )
        }
        # Make qubit config
        self.qubit_config = {
            id: TransmonQubit(
                drive=self.rf_output_channels[cryo_config[val["drive"]]],
                flux=self.analog_output_channels[cryo_config[fval]] if (fval:=val.get("flux")) else None
            ) for id, val in chip_config.items()
        }

        self.elements = []
        self.full_config = self.pl_config | self.qubit_config

        # Make config
        qm_config = generate_config(
            [],
            self.rf_output_channels,
            self.rf_input_channels,
            self.analog_output_channels,
            self.qubit_config
        )

        import json
        with open("qtl_qm_config.json", "w+") as f:
            json.dump(qm_config, f)

        self.qm = self.qm_manager.open_qm(qm_config)
        def exit_handler():
            print("Cleaning up, closing QM")
            self.qm.close()
        atexit.register(exit_handler)

    def print_tree(self):
        for element in self.elements:
            print(f"{element}:\n{self.full_config[element].get_tree(indent=1)}")
        print(f"PL:\n{self.pl_config["PL"].get_tree(indent=1)}")

    def reload_config(self, elements, new_settings):
        # TODO: Only supports depth 2 dicts
        for elem, settings in new_settings.items():
            subtree = self.full_config[elem]
            for k, v in settings.items():
                if type(v) is dict:
                    for kk, vv in v.items():
                        subtree[k][kk] = vv
                else:
                    subtree[k] = v

        self.elements = elements

        qm_config=generate_config(
            elements,
            self.rf_output_channels,
            self.rf_input_channels,
            self.analog_output_channels,
            self.qubit_config
        )

        import json
        with open("qtl_qm_config.json", "w+") as f:
            json.dump(qm_config, f)

        self.qm.close()
        self.qm = self.qm_manager.open_qm(qm_config)


    def execute(self, element, program, Navg, live_plot=False):
        if self.single_shot:
            job = self.qm.execute(program)
            res_handles = job.result_handles
            res_handles.wait_for_all_values()
            I = res_handles.get("I").fetch_all()["value"]
            Q = res_handles.get("Q").fetch_all()["value"]

            self.single_shot = False

            return u.demod2volts(I + 1.j * Q, self.full_config[element].readout_len)

        job = self.qm.execute(program)
        print(job.execution_report())
        results = fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")
        while results.is_processing():
            I, Q, iteration = results.fetch_all()
            S = u.demod2volts(I + 1.j * Q, self.full_config[element].readout_len)
            progress_counter(iteration, Navg, start_time=results.get_start_time())

        return S


class ExperimentResult:
    disc_0 = 0
    disc_1 = 0

    def __init__(self, data, experiment, existing_id=None):
        self.data = data
        self.experiment = experiment
        self.id = existing_id

    def analyze(self, **kwargs):
        return self.experiment.analyze_data(self, **kwargs)

    def save(self):
        self.id = self.db.save_data(self.experiment.experiment_name, self.data, overwrite_id=self.id)
        print(f"Saved with ID {self.id}")

    def get_title(self):
        return f"{self.id}_{self.experiment.experiment_name}_{self.data.attrs["element"]}"

    def mag_phase_plot(self, y_axis=None):
        fig, axs = plt.subplots(nrows=2)#, constrained_layout=True)
        fig.suptitle(self.get_title())
        plt.tight_layout()

        np.abs(self.data["iq"]).plot(ax=axs[0], y=y_axis)
        if len(axs[0].collections) == 0:
            axs[0].set_ylabel(r"$Magnitude, \ |S|$ (V)")
        else:
            axs[0].collections[-1].colorbar.set_label(r"$Magnitude, \ |S|$ (V)")
        axs[0].set_xlabel("")

        xr.ufuncs.angle(self.data["iq"]).plot(ax=axs[1], y=y_axis)
        if len(axs[1].collections) == 0:
            axs[1].set_ylabel(r"$Phase \ S$ (rad)")
        else:
            axs[1].collections[-1].colorbar.set_label(r"$Phase \ S$ (rad)")

        return axs

    def iq_plot(self):
        fig, axs = plt.subplots(constrained_layout=True)
        fig.suptitle(self.get_title())

        axs.scatter(
            self.data["iq"].real,
            self.data["iq"].imag
        )
        axs.set_xlabel(r"$I$ (V)")
        axs.set_ylabel(r"$Q$ (V)")

    def add_e_state(self):
        self.data["e_state"] = ((self.data["iq"] - self.disc_0) * self.disc_1).real


class QTLQMExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    station = None

    def run(self, element, sweeps=None, Navg=1024, autosave=True, **kwargs):
        program = self.get_program(element, Navg, sweeps, **kwargs)
        results = self.station.execute(element, program, Navg)

        sweep_labels = [sl[0] for sl in self.sweep_labels()]
        ds = xr.Dataset(
            data_vars={"iq": (sweep_labels, results)},
            coords={sweep_label: values for sweep_label, values in zip(sweep_labels, sweeps)},
            attrs={"element": element}
        )

        for label, unit in self.sweep_labels():
            ds[label].attrs["units"] = unit

        exp_res = ExperimentResult(ds, self)

        if autosave:
            exp_res.save()

        return exp_res
    
    def load(self, id, data):
        return ExperimentResult(data, self, id)
    

def start_station(config, db_path, db_name):
    with open(config) as f:
        config = yaml.safe_load(f)
    station = QTLQMSimpleStation(config)
    db = FileSystemDB(db_name, db_path)
    ExperimentResult.db = db
    QTLQMExperiment.station = station

    return station
