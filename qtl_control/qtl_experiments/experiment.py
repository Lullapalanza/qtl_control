import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

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

    def iq_plot(self):
        fig, axs = plt.subplots(constrained_layout=True)
        fig.suptitle(self.get_title())

        axs.scatter(
            self.data["iq"].real,
            self.data["iq"].imag
        )
        axs.set_xlabel(r"$I$ (V)")
        axs.set_ylabel(r"$Q$ (V)")


class QTLQMExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    station = None
    readout_type = ReadoutType.average # default

    def run(self, element, sweeps=None, Navg=1024, autosave=True, **kwargs):
        program = self.get_program(element, Navg, sweeps, **kwargs)
        results = self.station.execute(element, program, Navg, readout_type=self.readout_type)

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