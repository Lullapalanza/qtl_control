import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
from qm.qua import *
from qualang_tools.loops import from_array

from qualang_tools.units import unit
u = unit(coerce_to_integer=True)
from qtl_control.qtl_simple_experiments.experiments.base import QTLQMExperiment


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
                    wait(400 * u.ns, "qubit")
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
                    wait(wait_after//4, "resonator")
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

class QubitFluxSpec(QTLQMExperiment):
    experiment_name = "QMFluxSpec"

    def sweep_labels(self):
        return ["amplitude", "drive_frequency", ]

    def get_program(self, Navg, sweeps, sat_amp=0.05, wait_after=10000):
        saturation_len = 10 * u.us  # In ns
        amp_sweep = sweeps[0]
        dfs = sweeps[1] - self.station.settings["qubit_LO"]
        # === START QM program ===
        with program() as spec_program:
            n = declare(int)
            df = declare(int)
            a = declare(fixed)  # QUA variable for the measured 'I' quadrature
            I = declare(fixed)
            Q = declare(fixed)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()

            with for_(n, 0, n < Navg, n + 1):
                with for_(*from_array(a, amp_sweep)):  # QUA for_ loop for sweeping the frequency
                    set_dc_offset("flux_line", "single", a)
                    with for_(*from_array(df, dfs)):
                        # Update the frequency of the digital oscillator linked to the qubit element
                        update_frequency("qubit", df)
                        # Play the saturation pulse to put the qubit in a mixed state - Can adjust the amplitude on the fly [-2; 2)
                        play("saturation" * amp(sat_amp), "qubit", duration=saturation_len * u.ns)
                        # Align the two elements to measure after playing the qubit pulse.
                        # One can also measure the resonator while driving the qubit by commenting the 'align'
                        wait(400 * u.ns, "qubit")
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
                        wait(wait_after//4, "resonator")
                        # Save the 'I' & 'Q' quadratures to their respective streams
                        save(I, I_stream)
                        save(Q, Q_stream)
                    # Save the averaging iteration to get the progress bar
                save(n, n_stream)

            with stream_processing():
                # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
                I_stream.buffer(len(dfs)).buffer(len(amp_sweep)).average().save("I")
                Q_stream.buffer(len(dfs)).buffer(len(amp_sweep)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===
        return spec_program


class Rabi(QTLQMExperiment):
    experiment_name = "QMRabi"

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
                    play("gauss" * amp(a), "qubit", duration=pulse_duration * u.ns)
                    
                    # Align the two elements to measure after playing the qubit pulse.
                    wait(400 * u.ns, "qubit")
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
                    wait(wait_after//4, "resonator")
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

class TimeRabi(QTLQMExperiment):
    experiment_name = "QMTimeRabi"

    def sweep_labels(self):
        return ["duration", ]

    def get_program(self, Navg, sweeps, pulse_amplitude=0.1, wait_after=50000):
        duration_sweep = sweeps[0]
        # === START QM program ===
        with program() as rabi_time:
            n = declare(int)
            a = declare(fixed)
            t = declare(int)
            I = declare(fixed)
            Q = declare(fixed)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()


            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(t, duration_sweep)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                    # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    
                    # play("x180" * amp(a), "qubit")
                    play("gauss" * amp(pulse_amplitude), "qubit", duration=t)
                    # wait(t, "qubit")
                    
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
                    wait(wait_after//4, "resonator")
                    # Save the 'I' & 'Q' quadratures to their respective streams
                    save(I, I_stream)
                    save(Q, Q_stream)
                # Save the averaging iteration to get the progress bar
                save(n, n_stream)

            with stream_processing():
                # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
                I_stream.buffer(len(duration_sweep)).average().save("I")
                Q_stream.buffer(len(duration_sweep)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===

        return rabi_time

class RamseyF(QTLQMExperiment):
    experiment_name = "QMRamseyF"

    def sweep_labels(self):
        return ["detuning", "delay"]
        # return ["delay", "detuning"]

    def get_program(self, Navg, sweeps, wait_after=50000):
        delay_sweep = sweeps[1]
        qubit_IF = self.station.settings["qubit_frequency"] - self.station.settings["qubit_LO"]
        detuning_sweep = qubit_IF - sweeps[0]
        # === START QM program ===
        with program() as ramsey_prog:
            n = declare(int)  # QUA variable for the averaging loop
            tau = declare(int)  # QUA variable for the idle time
            f = declare(int)  # QUA variable for the idle time

            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            # Shift the qubit drive frequency to observe Ramsey oscillations

            with for_(n, 0, n < Navg, n + 1):
                with for_(*from_array(f, detuning_sweep)):
                    update_frequency("qubit", f) 
                    with for_(*from_array(tau, delay_sweep)):
                        # 1st x90 gate
                        play("x90", "qubit")
                        # Wait a varying idle time
                        wait(tau, "qubit")
                        # 2nd x90 gate
                        play("x90", "qubit")
                        # Align the two elements to measure after playing the qubit pulse.
                        wait(400 * u.ns, "qubit")
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
                        wait(wait_after * u.ns, "resonator")
                        # Save the 'I' & 'Q' quadratures to their respective streams
                        save(I, I_st)
                        save(Q, Q_st)
                    # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
                I_st.buffer(len(delay_sweep)).buffer(len(detuning_sweep)).average().save("I")
                Q_st.buffer(len(delay_sweep)).buffer(len(detuning_sweep)).average().save("Q")
                n_st.save("iteration")
            
        return ramsey_prog

class T1(QTLQMExperiment):
    experiment_name = "QMT1"

    def sweep_labels(self):
        return ["delay", ]

    def get_program(self, Navg, sweeps, wait_after=50000):
        delay_sweep = sweeps[0] / 4
        # === START QM program ===
        with program() as t1_program:
            n = declare(int)
            a = declare(fixed)
            t = declare(int)
            I = declare(fixed)
            Q = declare(fixed)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()

            update_frequency("qubit", qubit_IF)


            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(t, delay_sweep)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                    # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    
                    # play("x180" * amp(a), "qubit")
                    play("x180", "qubit")
                    # wait(t, "qubit")
                    wait(t, "qubit") # in units of 4 ns
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
                    wait(wait_after//4, "resonator")
                    # Save the 'I' & 'Q' quadratures to their respective streams
                    save(I, I_stream)
                    save(Q, Q_stream)
                # Save the averaging iteration to get the progress bar
                save(n, n_stream)

            with stream_processing():
                # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
                I_stream.buffer(len(waits)).average().save("I")
                Q_stream.buffer(len(waits)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===
        return t1_program
    
class SingleShotReadout(QTLQMExperiment):
    experiment_name = "QMSSH"

    def sweep_labels(self):
        return ["iteration", "state"]
        
    def get_program(self, Navg, sweeps, wait_after=100000):
        self.station.single_shot = True
        sweep = [0, 1]
        with program() as IQ_blobs:
            n = declare(int)
            op = declare(int)
            I = declare(fixed)
            Q = declare(fixed)
            I_st = declare_stream()
            Q_st = declare_stream()

            with for_(n, 0, n < Navg, n + 1):
                with for_(*from_array(op, sweep)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                # Measure the state of the resonator
                    with if_(op==1):
                        play("x180", "qubit")
                        wait(400 * u.ns, "qubit")
                    align("qubit", "resonator")
                    measure(
                        "readout",
                        "resonator",
                        None,
                        dual_demod.full("cos", "sin", I),
                        dual_demod.full("minus_sin", "cos", Q),
                    )
                # Wait for the qubit to decay to the ground state in the case of measurement induced transitions
                    wait(wait_after//4, "resonator")
                    align("resonator", "qubit")
                # Save the 'I' & 'Q' quadratures to their respective streams for the ground state
                    save(I, I_st)
                    save(Q, Q_st)

            with stream_processing():
                # Save all streamed points for plotting the IQ blobs
                I_st.buffer(len(sweep)).save_all("I")
                Q_st.buffer(len(sweep)).save_all("Q")
        
        return IQ_blobs