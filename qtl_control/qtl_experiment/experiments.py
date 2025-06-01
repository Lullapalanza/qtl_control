import matplotlib
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

# from qm.qua import *
# from qualang_tools.loops import from_array

from qtl_control.backend.qubit_controllers import PulsePlaylist, PlaylistOp

class VNATrace:
    experiment_name = "VNATrace"

    def run(self, vna_name, parameter=None, sweep_points=None):
        if parameter is None:
            data = self.default_station.run_module_method(
                "RandSModule",
                "get_frequency_trace",
                vna_name
            )

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


class QTLPulsedExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    default_db = None
    default_station = None

    def run(self, element, Navg=1024, sweep_values=None, autosave=True, **kwargs):
        sweeps = self.get_sweeps(element, sweep_values)
        pulse_playlist = self.get_playlist(element, Navg, sweeps)
        experiment_results = self.default_station.run_module_method(
            "PulsedQubits",
            "execute_playlist",
            pulse_playlist
        )

        ds = xr.DataSet(
            data_vars={
                "iq": (sweeps.keys(), experiment_results)
            },
            coords=sweeps
        )

        saved_id = self.default_db.save_data(
            self.experiment_name,
            ds
        )

        return saved_id, ds


class ReadoutResonatorSpectroscopy(QTLPulsedExperiment):
    experiment_name = "QMReadoutSpec"

    def get_sweeps(self, element, sweep_values=None):
        if sweep_values:
            return {"readout_frequency": sweep_values[0]}
        else:
            return {"readout_frequency": np.arange(5e9, 5.1e9, 1e6)}

    def get_playlist(self, element, Navg, sweeps):
        playlist = PulsePlaylist([element, ], Navg, data_dims=sweeps)
        for frequency in sweeps["readout_frequency"]:
            playlist.add(element, PlaylistOp.change_readout_frequency, frequency)
            playlist.add(element, PlaylistOp.readout)

        return playlist

        # N_avg = 1024 * 2
        # depletion_time = 2 * u.us
        # df = frequency_range - resonator_LO
        # with program() as resonator_spec:
        #     n = declare(int)  # QUA variable for the averaging loop
        #     f = declare(int)  # QUA variable for the readout frequency
        #     I = declare(fixed)  # QUA variable for the measured 'I' quadrature
        #     Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
        #     I_st = declare_stream()  # Stream for the 'I' quadrature
        #     Q_st = declare_stream()  # Stream for the 'Q' quadrature
        #     n_st = declare_stream()  # Stream for the averaging iteration 'n'

        #     with for_(n, 0, n < N_avg, n + 1):  # QUA for_ loop for averaging
        #         with for_(*from_array(f, df)):  # QUA for_ loop for sweeping the frequency
        #             # Update the frequency of the digital oscillator linked to the resonator element
        #             update_frequency("resonator", f)
        #             # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
        #             measure(
        #                 "readout",
        #                 "resonator",
        #                 None,
        #                 dual_demod.full("cos", "sin", I),
        #                 dual_demod.full("minus_sin", "cos", Q),
        #             )
        #             # Wait for the resonator to deplete
        #             wait(depletion_time * u.ns, "resonator")
        #             # Save the 'I' & 'Q' quadratures to their respective streams
        #             save(I, I_st)
        #             save(Q, Q_st)
        #         # Save the averaging iteration to get the progress bar
        #         save(n, n_st)

        #     with stream_processing():
        #         # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
        #         I_st.buffer(len(frequency_range)).average().save("I")
        #         Q_st.buffer(len(frequency_range)).average().save("Q")
        #         n_st.save("iteration")


class QubitSpec(QTLPulsedExperiment):
    experiment_name = "QMspec"

    def get_playlist(self):
        pass

    def get_sweeps(elements, sweep_values=None):
        if sweep_values:
            return {"drive_frequency": sweep_values[0]}
        else:
            return {"drive_frequency": np.arange(4e9, 4.1e9, 1e6)}

    def get_playlist(self, elements, Navg, sweeps):
        playlist = PulsePlaylist(elements)
        for frequency in sweeps:
            for element in elements:
                playlist.add() # Change drive frequency?
                playlist.add() # Saturation Pulse
                playlist.add() # Add readout here?


    # def run(self, qubit, frequency_range, piamp=0.4):
    #     N_avg = 2024
    #     thermalization_time = 100 * u.us
    #     wait_between_ro = 100 * u.ns
    #     saturation_len = 10 * u.us  # In ns

    #     dfs = frequency_range - qubit_LO
    #     # === START QM program ===
    #     with program() as rabi_chevron:
    #         n = declare(int)
    #         df = declare(int)
    #         I = declare(fixed)
    #         Q = declare(fixed)

    #         I_stream = declare_stream()
    #         Q_stream = declare_stream()
    #         n_stream = declare_stream()

    #         with for_(n, 0, n < N_avg, n + 1):
    #             with for_(*from_array(df, dfs)):
    #                 # Update the frequency of the digital oscillator linked to the qubit element
    #                 update_frequency("qubit", df)
    #                 # Play the saturation pulse to put the qubit in a mixed state - Can adjust the amplitude on the fly [-2; 2)
    #                 play("saturation" * amp(piamp), "qubit", duration=saturation_len * u.ns)
    #                 # Align the two elements to measure after playing the qubit pulse.
    #                 # One can also measure the resonator while driving the qubit by commenting the 'align'
    #                 align("qubit", "resonator")
    #                 wait(wait_between_ro * u.ns, "resonator") # Wait for delays?

    #                 # Measure the state of the resonator
    #                 measure(
    #                     "readout",
    #                     "resonator",
    #                     None,
    #                     dual_demod.full("cos", "sin", I),
    #                     dual_demod.full("minus_sin", "cos", Q),
    #                 )
    #                 # Wait for the qubit to decay to the ground state
    #                 wait(thermalization_time * u.ns, "resonator")
    #                 # Save the 'I' & 'Q' quadratures to their respective streams
    #                 save(I, I_stream)
    #                 save(Q, Q_stream)
    #             # Save the averaging iteration to get the progress bar
    #             save(n, n_stream)

    #         with stream_processing():
    #             # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
    #             I_stream.buffer(len(frequency_range)).average().save("I")
    #             Q_stream.buffer(len(frequency_range)).average().save("Q")
    #             n_stream.save("iteration")
    #     # === END QM program ===

class Rabi(QTLPulsedExperiment):
    experiment_name = "QMRabi"

    def get_playlist(self):
        pass

    def get_sweeps(elements, sweep_values=None):
        if sweep_values:
            return {"drive_frequency": sweep_values[0]}
        else:
            return {"drive_frequency": np.arange(4e9, 4.1e9, 1e6)}

    def get_playlist(self, elements, Navg, sweeps):
        playlist = PulsePlaylist(elements)
        for amp in sweeps:
            for element in elements:
                playlist.add() # Pi pulse with different ampltidues
                playlist.add() # Add readout here?


    # def run(self, qubit, amp_range, pi_ns_duration):
    #     N_avg = 2024
    #     thermalization_time = 300 * u.us
    #     wait_between_ro = 300 * u.ns
    #     pi_duration = pi_ns_duration * u.ns
    #     # === START QM program ===
    #     with program() as rabi_chevron:
    #         n = declare(int)
    #         a = declare(fixed)
    #         I = declare(fixed)
    #         Q = declare(fixed)

    #         I_stream = declare_stream()
    #         Q_stream = declare_stream()
    #         n_stream = declare_stream()

    #         update_frequency("qubit", qubit_IF)


    #         with for_(n, 0, n < N_avg, n + 1):  # QUA for_ loop for averaging
    #             with for_(*from_array(a, amp_range)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
    #                 # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    
    #                 # play("x180" * amp(a), "qubit")
    #                 play("x180" * amp(a), "qubit", duration=pi_duration * u.ns)
                    
    #                 # Align the two elements to measure after playing the qubit pulse.
    #                 align("qubit", "resonator")
    #                 # Measure the state of the resonator
    #                 # The integration weights have changed to maximize the SNR after having calibrated the IQ blobs.
    #                 wait(wait_between_ro * u.ns, "resonator") # Wait for delays?
    #                 measure(
    #                     "readout",
    #                     "resonator",
    #                     None,
    #                     dual_demod.full("cos", "sin", I),
    #                     dual_demod.full("minus_sin", "cos", Q),
    #                 )
    #                 # Wait for the qubit to decay to the ground state
    #                 wait(thermalization_time * u.ns, "resonator")
    #                 # Save the 'I' & 'Q' quadratures to their respective streams
    #                 save(I, I_stream)
    #                 save(Q, Q_stream)
    #             # Save the averaging iteration to get the progress bar
    #             save(n, n_stream)

    #         with stream_processing():
    #             # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
    #             I_stream.buffer(len(amp_range)).average().save("I")
    #             Q_stream.buffer(len(amp_range)).average().save("Q")
    #             n_stream.save("iteration")
    #     # === END QM program ===

# class TimeRabi(QTLExperiment):
#     experiment_name = "QMTimeRabi"
#     def run(self, qubit, durations, _amp):
#         N_avg = 2024
#         thermalization_time = 300 * u.us
#         wait_between_ro = 300 * u.ns
#         # === START QM program ===
#         with program() as rabi_chevron:
#             n = declare(int)
#             a = declare(fixed)
#             t = declare(int)
#             I = declare(fixed)
#             Q = declare(fixed)

#             I_stream = declare_stream()
#             Q_stream = declare_stream()
#             n_stream = declare_stream()

#             update_frequency("qubit", qubit_IF)


#             with for_(n, 0, n < N_avg, n + 1):  # QUA for_ loop for averaging
#                 with for_(*from_array(t, durations)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
#                     # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    
#                     # play("x180" * amp(a), "qubit")
#                     play("pi" * amp(_amp), "qubit", duration=t)
#                     # wait(t, "qubit")
                    
#                     # Align the two elements to measure after playing the qubit pulse.
#                     align("qubit", "resonator")
#                     # Measure the state of the resonator
#                     # The integration weights have changed to maximize the SNR after having calibrated the IQ blobs.
#                     wait(wait_between_ro * u.ns, "resonator") # Wait for delays?
#                     measure(
#                         "readout",
#                         "resonator",
#                         None,
#                         dual_demod.full("cos", "sin", I),
#                         dual_demod.full("minus_sin", "cos", Q),
#                     )
#                     # Wait for the qubit to decay to the ground state
#                     wait(thermalization_time * u.ns, "resonator")
#                     # Save the 'I' & 'Q' quadratures to their respective streams
#                     save(I, I_stream)
#                     save(Q, Q_stream)
#                 # Save the averaging iteration to get the progress bar
#                 save(n, n_stream)

#             with stream_processing():
#                 # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
#                 I_stream.buffer(len(durations)).average().save("I")
#                 Q_stream.buffer(len(durations)).average().save("Q")
#                 n_stream.save("iteration")
#         # === END QM program ===

#         # === SEND PROGRAM ===
#         results = self.default_station.run_module_method(
#             "PulsedQubits",
#             "execute_program",
#             qubit,
#             rabi_chevron
#         )

#         # === DATA TO XARRAY AND SAVE
#         ds = xr.Dataset(
#             data_vars={
#                 "iq": (["duration"], results)
#             },
#             coords={
#                 "duration": durations,
#             }
#         )
    
#         saved_id = self.default_db.save_data(
#             self.experiment_name,
#             ds
#         )

#         return saved_id, ds

# class RabiChevron(QTLExperiment):
#     experiment_name = "RabiChevron"
#     """
#     Run Rabi Chevron for a qubit, ranges are internal sweeps for the device

#     Currently just for qm
#     """

#     def run(self, qubit, frequency_range, duration_range):
#         N_avg = 2024
#         thermalization_time = 100 * u.us
#         wait_between_ro = 100 * u.ns
#         # === START QM program ===
#         with program() as rabi_chevron:
#             n = declare(int)
#             f = declare(int)
#             t = declare(int)
#             I = declare(fixed)
#             Q = declare(fixed)

#             I_stream = declare_stream()
#             Q_stream = declare_stream()
#             n_stream = declare_stream()

            
#             df = frequency_range - qubit_LO

#             with for_(n, 0, n < N_avg, n+1):
#                 with for_(*from_array(t, duration_range)):
#                     with for_(*from_array(f, df)):
#                         update_frequency(qubit, f)

#                         play("x180", qubit, duration=t)
#                         align(qubit, "resonator")
#                         # wait(300, "resonator") # Wait for delays?
#                         measure(
#                             "readout",
#                             "resonator",
#                             None,
#                             dual_demod.full("cos", "sin", I),
#                             dual_demod.full("minus_sin", "cos", Q),
#                         )
#                         # Wait for the qubit to decay to the ground state
#                         wait(thermalization_time * u.ns, "resonator")
#                         # Save the 'I' & 'Q' quadratures to their respective streams
#                         save(I, I_stream)
#                         save(Q, Q_stream)
#                 # Save the averaging iteration to get the progress bar
#                 save(n, n_stream)

#             with stream_processing():
#                 # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
#                 I_stream.buffer(len(frequency_range)).buffer(len(duration_range)).average().save("I")
#                 Q_stream.buffer(len(frequency_range)).buffer(len(duration_range)).average().save("Q")
#                 n_stream.save("iteration")
#         # === END QM program ===

#         # === SEND PROGRAM ===
#         results = self.default_station.run_module_method(
#             "PulsedQubits",
#             "execute_program",
#             qubit,
#             rabi_chevron
#         )

#         # === DATA TO XARRAY AND SAVE
#         ds = xr.Dataset(
#             data_vars={
#                 "iq": (["duration", "drive_frequency"], results)
#             },
#             coords={
#                 "drive_frequency": frequency_range,
#                 "duration": duration_range,
#             }
#         )
    
#         saved_id = self.default_db.save_data(
#             self.experiment_name,
#             ds
#         )

#         return saved_id, ds
  


# class T1(QTLExperiment):
#     experiment_name = "QMT1"
#     def run(self, qubit, waits, _amp, duration_ns):
#         N_avg = 2024
#         thermalization_time = 300 * u.us
#         wait_between_ro = 300 * u.ns
#         duration_ns = duration_ns * u.ns
#         # === START QM program ===
#         with program() as rabi_chevron:
#             n = declare(int)
#             a = declare(fixed)
#             t = declare(int)
#             I = declare(fixed)
#             Q = declare(fixed)

#             I_stream = declare_stream()
#             Q_stream = declare_stream()
#             n_stream = declare_stream()

#             update_frequency("qubit", qubit_IF)


#             with for_(n, 0, n < N_avg, n + 1):  # QUA for_ loop for averaging
#                 with for_(*from_array(t, waits)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
#                     # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    
#                     # play("x180" * amp(a), "qubit")
#                     play("x180" * amp(_amp), "qubit", duration=duration_ns * u.ns)
#                     # wait(t, "qubit")
#                     wait(t, "qubit")
#                     # Align the two elements to measure after playing the qubit pulse.
#                     align("qubit", "resonator")
#                     # Measure the state of the resonator
#                     # The integration weights have changed to maximize the SNR after having calibrated the IQ blobs.
#                     wait(wait_between_ro * u.ns, "resonator") # Wait for delays?
#                     measure(
#                         "readout",
#                         "resonator",
#                         None,
#                         dual_demod.full("cos", "sin", I),
#                         dual_demod.full("minus_sin", "cos", Q),
#                     )
#                     # Wait for the qubit to decay to the ground state
#                     wait(thermalization_time * u.ns, "resonator")
#                     # Save the 'I' & 'Q' quadratures to their respective streams
#                     save(I, I_stream)
#                     save(Q, Q_stream)
#                 # Save the averaging iteration to get the progress bar
#                 save(n, n_stream)

#             with stream_processing():
#                 # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
#                 I_stream.buffer(len(waits)).average().save("I")
#                 Q_stream.buffer(len(waits)).average().save("Q")
#                 n_stream.save("iteration")
#         # === END QM program ===

#         # === SEND PROGRAM ===
#         results = self.default_station.run_module_method(
#             "PulsedQubits",
#             "execute_program",
#             qubit,
#             rabi_chevron
#         )

#         # === DATA TO XARRAY AND SAVE
#         ds = xr.Dataset(
#             data_vars={
#                 "iq": (["wait_time"], results)
#             },
#             coords={
#                 "wait_time": waits,
#             }
#         )
    
#         saved_id = self.default_db.save_data(
#             self.experiment_name,
#             ds
#         )

#         return saved_id, ds


# class SingleQubitRB(QTLExperiment):
#     experiment_name = "SingleQubitRB"

#     def run(self, controller_name, nr_of_iterations):
#         full_data = None
#         for i in nr_of_iterations:
#             new_hash = ...
#             new_sqrb_sequence = ...

#             # station.run(...)

#         self.default_db.save_data(
#             self.experiment_name,
#             full_data,
#             [("hash", [i for i in nr_of_iterations])]
#         )