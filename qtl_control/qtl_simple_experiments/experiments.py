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

        self.settings = {
            "readout_LO": 7e9,
            "readout_frequency": 6.9e9,
            "readout_amp": 0.01,
            "readout_len": 2000,

            "qubit_LO": 7e9,
            "qubit_frequency": 6.9e9,

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
        job = self.qm.execute(program)
        results = fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")
        while results.is_processing():
            I, Q, iteration = results.fetch_all()
            S = u.demod2volts(I + 1.j * Q, self.settings["readout_len"])
            progress_counter(iteration, Navg, start_time=results.get_start_time())

        return S


class QTLQMExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    db = None
    station = None

    def run(self, sweeps=None, Navg=1024, autosave=True, **kwargs):
        program = self.get_program(Navg, sweeps, **kwargs)
        results = self.station.execute(program, Navg)

        ds = xr.Dataset(
            data_vars={"iq": (self.sweep_labels(), results)},
            coords={label: values for label, values in zip(self.sweep_labels(), sweeps)}
        )

        if autosave:
            saved_id = self.db.save_data(self.experiment_name, ds)
            return saved_id, ds

        else:
            return None, ds


class ReadoutResonatorSpectroscopy(QTLQMExperiment):
    experiment_name = "QMReadoutSpec"

    def sweep_labels(self):
        return ["readout_frequency", ]

    def get_program(self, Navg, sweeps, wait_after=1000):
        sweep = sweeps[0] - self.station.settings["readout_LO"]
        with program() as resonator_spec:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the readout frequency
            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(f, sweep)):  # QUA for_ loop for sweeping the frequency
                    update_frequency("resonator", f)
                    # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                    measure(
                        "readout",
                        "resonator",
                        None,
                        dual_demod.full("cos", "sin", I),
                        dual_demod.full("minus_sin", "cos", Q),
                    )
                    # Wait for the resonator to deplete
                    wait(wait_after, "resonator")
                    # Save the 'I' & 'Q' quadratures to their respective streams
                    save(I, I_st)
                    save(Q, Q_st)
                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                I_st.buffer(len(sweep)).average().save("I")
                Q_st.buffer(len(sweep)).average().save("Q")
                n_st.save("iteration")
        
        return resonator_spec


class PunchOut(QTLQMExperiment):
    experiment_name = "QMPunchOut"

    def sweep_labels(self):
        return ["readout_frequency", "amplitude"]

    def get_program(self, Navg, sweeps, wait_after=1000):
        freq_sweep = sweeps[0] - self.station.settings["readout_LO"]
        amplitude_sweep = sweeps[1]
        with program() as resonator_spec:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the readout frequency
            a = declare(fixed)  # QUA variable for the readout amplitude pre-factor
            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(f, freq_sweep)):  # QUA for_ loop for sweeping the frequency
                    update_frequency("resonator", f)
                    with for_each_(a, amplitude_sweep):
                    # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                        measure(
                            "readout" * amp(a),
                            "resonator",
                            None,
                            dual_demod.full("cos", "sin", I),
                            dual_demod.full("minus_sin", "cos", Q),
                        )
                        # Wait for the resonator to deplete
                        wait(wait_after, "resonator")
                        # Save the 'I' & 'Q' quadratures to their respective streams
                        save(I, I_st)
                        save(Q, Q_st)
                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                I_st.buffer(len(amplitude_sweep)).buffer(len(freq_sweep)).average().save("I")
                Q_st.buffer(len(amplitude_sweep)).buffer(len(freq_sweep)).average().save("Q")
                n_st.save("iteration")
        
        return resonator_spec


class QubitSpec(QTLQMExperiment):
    experiment_name = "QMspec"

    def sweep_labels(self):
        return ["drive_frequency", ]

    def get_program(self, Navg, sweeps, sat_amp=0.05, wait_after=10000):
        saturation_len = 10 * u.us  # In ns
        dfs = sweeps[0] - self.station.settings["qubit_LO"]
        # === START QM program ===
        with program() as spec_program:
            n = declare(int)
            df = declare(int)
            I = declare(fixed)
            Q = declare(fixed)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()

            with for_(n, 0, n < Navg, n + 1):
                with for_(*from_array(df, dfs)):
                    # Update the frequency of the digital oscillator linked to the qubit element
                    update_frequency("qubit", df)
                    # Play the saturation pulse to put the qubit in a mixed state - Can adjust the amplitude on the fly [-2; 2)
                    play("saturation" * amp(sat_amp), "qubit", duration=saturation_len * u.ns)
                    # Align the two elements to measure after playing the qubit pulse.
                    # One can also measure the resonator while driving the qubit by commenting the 'align'
                    align("qubit", "resonator")

                    # Measure the state of the resonator
                    measure(
                        "readout",
                        "resonator",
                        None,
                        dual_demod.full("cos", "sin", I),
                        dual_demod.full("minus_sin", "cos", Q),
                    )
                    # Wait for the qubit to decay to the ground state
                    wait(wait_after, "resonator")
                    # Save the 'I' & 'Q' quadratures to their respective streams
                    save(I, I_stream)
                    save(Q, Q_stream)
                # Save the averaging iteration to get the progress bar
                save(n, n_stream)

            with stream_processing():
                # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
                I_stream.buffer(len(dfs)).average().save("I")
                Q_stream.buffer(len(dfs)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===
        return spec_program

class Rabi(QTLQMExperiment):
    experiment_name = "QMsQMRabi"

    def sweep_labels(self):
        return ["ampltidue", ]

    def get_program(self, Navg, sweeps, pulse_duration=100, wait_after=50000):
        amp_range = sweeps[0]
        # === START QM program ===
        with program() as rabi:
            n = declare(int)
            a = declare(fixed)
            I = declare(fixed)
            Q = declare(fixed)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()

            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(a, amp_range)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                    # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    
                    # play("x180" * amp(a), "qubit")
                    play("x180" * amp(a), "qubit", duration=pulse_duration)
                    
                    # Align the two elements to measure after playing the qubit pulse.
                    align("qubit", "resonator")
                    # Measure the state of the resonator
                    # The integration weights have changed to maximize the SNR after having calibrated the IQ blobs.
                    measure(
                        "readout",
                        "resonator",
                        None,
                        dual_demod.full("cos", "sin", I),
                        dual_demod.full("minus_sin", "cos", Q),
                    )
                    # Wait for the qubit to decay to the ground state
                    wait(wait_after, "resonator")
                    # Save the 'I' & 'Q' quadratures to their respective streams
                    save(I, I_stream)
                    save(Q, Q_stream)
                # Save the averaging iteration to get the progress bar
                save(n, n_stream)

            with stream_processing():
                # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
                I_stream.buffer(len(amp_range)).average().save("I")
                Q_stream.buffer(len(amp_range)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===

        return rabi

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