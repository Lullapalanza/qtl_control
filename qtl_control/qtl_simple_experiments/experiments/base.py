import matplotlib
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

from qm.qua import *
from qualang_tools.loops import from_array
from qm import QuantumMachinesManager
from qm.octave import QmOctaveConfig
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.units import unit
u = unit(coerce_to_integer=True)

from qtl_control.qtl_simple_experiments.qm_config import generate_config

import sys
import atexit
import signal
def kill_handler(*args):
    sys.exit(0)

signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)


class QTLQMSimpleStation:
    def __init__(self, host, port, cluster_name):
        octave_config = QmOctaveConfig()
        octave_config.set_calibration_db("")
        self.qm_manager = QuantumMachinesManager(
            host=host, port=port, cluster_name=cluster_name, octave=octave_config
        )
        self.single_shot = False

        self.settings = {
            "readout_LO": 7e9,
            "readout_frequency": 6.9e9,
            "readout_amp": 0.01,
            "readout_len": 2000,

            "qubit_LO": 7e9,
            "qubit_frequency": 6.9e9,

            "X180_duration": 300,
            "X180_amplitude": 0.1,

            "dc_volt": 0,
        }

        self.qm = self.qm_manager.open_qm(generate_config(self.settings))

        def exit_handler():
            print("Cleaning up, closing QM")
            self.qm.close()
        atexit.register(exit_handler)


    def change_settings(self, new_settings):
        self.settings.update(new_settings)
        self.qm.close()
        self.qm = self.qm_manager.open_qm(generate_config(self.settings))


    def execute(self, program, Navg):
        if self.single_shot:
            job = self.qm.execute(program)
            res_handles = job.result_handles
            res_handles.wait_for_all_values()
            I = res_handles.get("I").fetch_all()["value"]
            Q = res_handles.get("Q").fetch_all()["value"]

            self.single_shot = False

            return u.demod2volts(I + 1.j * Q, self.settings["readout_len"])

        job = self.qm.execute(program)
        print(job.execution_report())
        results = fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")
        while results.is_processing():
            I, Q, iteration = results.fetch_all()
            S = u.demod2volts(I + 1.j * Q, self.settings["readout_len"])
            progress_counter(iteration, Navg, start_time=results.get_start_time())

        return S


class ExperimentResult:
    db = None
    def __init__(self, data, experiment):
        self.data = data
        self.experiment = experiment
        self.id = None # In the future to reanalyze data

    def analyze(self):
        return self.experiment.analyze_data(self.data)

    def save(self):
        self.id = self.db.save_data(self.experiment.experiment_name, self.data, overwrite_id=self.id)
        print(f"Saved with ID {self.id}")

    def mag_phase_plot(self):
        fig, axs = plt.subplots(nrows=2, constrained_layout=True)
        np.abs(self.data["iq"]).plot(ax=axs[0])
        xr.ufuncs.phase(self.data["iq"]).plot(ax=axs[1])
        fig.suptitle(f"{self.id}_{self.experiment.experiment_name}")
        return fig

    def iq_plot(self):
        fig, axs = plt.subplots(constrained_layout=True)
        axs.scatter(
            self.data["iq"].re,
            self.data["iq"].imag
        )
        return fig

class QTLQMExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    station = None

    def run(self, sweeps=None, Navg=1024, autosave=True, **kwargs):
        program = self.get_program(Navg, sweeps, **kwargs)
        results = self.station.execute(program, Navg)

        ds = xr.Dataset(
            data_vars={"iq": (self.sweep_labels(), results)},
            coords={label: values for label, values in zip(self.sweep_labels(), sweeps)}
        )

        exp_res = ExperimentResult(ds, self)

        if autosave:
            exp_res.save()

        return exp_res