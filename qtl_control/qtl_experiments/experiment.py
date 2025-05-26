import matplotlib
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

from qm.qua import *
from qualang_tools.loops import from_array

from qtl_control.qtl_qm.utils import qubit_LO, u

class QTLExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    default_db = None
    default_station = None

    def run(self, autosave=True):
        pass

class VNATrace(QTLExperiment):
    experiment_name = "VNATrace"

    def run(self, vna_name, parameter=None, sweep_points=None):
        if parameter is None:
            data = self.default_station.run_module_method(
                "RandSModule",
                "get_frequency_trace",
                vna_name
            )
            # Format data to xarray?

            frequency_data = data[0]
            Sparam_data = data[1]

            ds = xr.Dataset(
                data_vars=dict(
                    Sparam=(["frequency", ], Sparam_data)
                ),
                coords=dict(
                    frequency=frequency_data
                ),
            )

        else:
            data = self.default_station.external_sweeps(
                [dict({parameter: sp}) for sp in sweep_points],
                "RandSModule",
                "get_frequency_trace",
                vna_name
            )

            # Assume frequency axis is the same for all
            frequency_data = data[0][0]
            ds = xr.Dataset(
                data_vars=dict(
                    Sparam=([parameter, "frequency"], [data[i][1] for i in range(len(sweep_points))])
                ),
                coords={
                    parameter: sweep_points,
                    "frequency": frequency_data,
                }
            )

        saved_id = self.default_db.save_data(
            self.experiment_name,
            ds
        )

        return saved_id, ds
    
    def plot(self, data):
        mag_data = np.abs(data["Sparam"])
        phase_data = xr.ufuncs.angle(data["Sparam"])

        fig, axs = plt.subplots(2)
        mag_data.plot(ax=axs[0])
        phase_data.plot(ax=axs[1])


class RabiChevron(QTLExperiment):
    experiment_name = "RabiChevron"
    """
    Run Rabi Chevron for a qubit, ranges are internal sweeps for the device

    Currently just for qm
    """

    def run(self, qubit, frequency_range, duration_range):
        N_avg = 1024
        thermalization_time = 100e-6
        # === START QM program ===
        with program() as rabi_chevron:
            n = declare(int)
            f = declare(int)
            t = declare(int)
            I = declare(fixed)
            Q = declare(fixed)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()

            with for_(n, 0, n < N_avg, n+1):
                with for_(*from_array(t, duration_range)):
                    with for_(*from_array(f, frequency_range)):
                        update_frequency(qubit, f - qubit_LO)

                        play("x180", qubit, duration=t)
                        align(qubit, "resonator")

                        measure(
                            "readout",
                            "resonator",
                            None,
                            dual_demod.full("rotated_cos", "rotated_sin", I),
                            dual_demod.full("rotated_minus_sin", "rotated_cos", Q),
                        )
                        # Wait for the qubit to decay to the ground state
                        wait(thermalization_time * u.ns, "resonator")
                        # Save the 'I' & 'Q' quadratures to their respective streams
                        save(I, I_stream)
                        save(Q, Q_stream)
                # Save the averaging iteration to get the progress bar
                save(n, n_stream)

            with stream_processing():
                # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
                I_stream.buffer(len(frequency_range)).buffer(len(duration_range)).average().save("I")
                Q_stream.buffer(len(frequency_range)).buffer(len(duration_range)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===

        # === SEND PROGRAM ===
        qubit_playlist = rabi_chevron
        results = self.default_station.run_module_method(
            "PulsedQubits",
            "execute_pulse_playlist",
            rabi_chevron
        )

        # === DATA TO XARRAY AND SAVE
        ds = xr.Dataset(
            data_vars=dict(
                Sparam=(["drive_frequency", "duration"], results)
            ),
            coords={
                "drive_frequency": frequency_range,
                "duration": duration_range,
            }
        )
    
        saved_id = self.default_db.save_data(
            self.experiment_name,
            ds
        )

        return saved_id, ds
  


class SingleQubitRB(QTLExperiment):
    experiment_name = "SingleQubitRB"

    def run(self, controller_name, nr_of_iterations):
        full_data = None
        for i in nr_of_iterations:
            new_hash = ...
            new_sqrb_sequence = ...

            # station.run(...)

        self.default_db.save_data(
            self.experiment_name,
            full_data,
            [("hash", [i for i in nr_of_iterations])]
        )