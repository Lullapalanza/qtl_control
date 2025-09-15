import json

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

from inspect import signature, _empty

from qtl_control.qtl_experiments.utils import ReadoutType

class ExperimentResult:
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

    def iq_plot(self, existing_axs=None):
        if existing_axs is None:
            fig, axs = plt.subplots(constrained_layout=True)
            fig.suptitle(self.get_title())
        else:
            axs = existing_axs

        axs.scatter(
            self.data["iq"].real,
            self.data["iq"].imag
        )
        axs.set_xlabel(r"$I$ (V)")
        axs.set_ylabel(r"$Q$ (V)")

        return axs


class QTLQMExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    station = None
    readout_type = ReadoutType.average # default

    def hidden_sweeps(self):
        return dict()

    def run(self, element, sweeps=None, Navg=1024, autosave=True, **kwargs):
        sweeps = sweeps or []
        for index, sweep in self.hidden_sweeps(Navg=Navg, **kwargs).items():
            sweeps.insert(index, sweep)
        
        if len(sweeps) != len(self.sweep_labels()):
            print("Warning: Missing some sweeps for run call")
            print("All sweeps:", self.sweep_labels())
            print("Hidden sweeps:", self.hidden_sweeps(Navg=Navg, **kwargs))
            return

        program = self.get_program(element, Navg, sweeps, **kwargs)
        results = self.station.execute(element, program, Navg, readout_type=self.readout_type)

        run_kwargs = {
            k: v.default for k, v in signature(self.get_program).parameters.items() if v.default is not _empty
        } | kwargs

        sweep_labels = [sl[0] for sl in self.sweep_labels()]
        ds = xr.Dataset(
            data_vars={"iq": (sweep_labels, results)},
            coords={sweep_label: values for sweep_label, values in zip(sweep_labels, sweeps)},
            attrs={"element": element, "run_kwargs": json.dumps(run_kwargs)}
        )

        for label, unit in self.sweep_labels():
            ds[label].attrs["units"] = unit

        exp_res = ExperimentResult(ds, self)

        if autosave:
            exp_res.save()

        return exp_res
    
    def load(self, id, data):
        return ExperimentResult(data, self, id)