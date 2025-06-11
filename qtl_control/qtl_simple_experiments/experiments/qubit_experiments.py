import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
from qm.qua import *
from qualang_tools.loops import from_array

from qualang_tools.units import unit
u = unit(coerce_to_integer=True)
from qtl_control.qtl_simple_experiments.experiments.base import QTLQMExperiment

def format_res(labels, values):
    return f"Fit:\n" + "\n".join([f"{label}: {float(v):.3e}" for label, v in zip(labels, values)])


class QubitSpectroscopy(QTLQMExperiment):
    experiment_name = "QM-QubitSpectroscopy"

    def sweep_labels(self):
        return [("drive_frequency", "Hz"), ]

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


class FluxQubitSpectrsocopy(QTLQMExperiment):
    experiment_name = "QM-FluxQubitSpectroscopy"

    def sweep_labels(self):
        return [("amplitude", "arb"), ("drive_frequency", "Hz"), ]

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
    experiment_name = "QM-Rabi"

    def sweep_labels(self):
        return [("amplitude", "arb"), ]

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
    
    def analyze_data(self, result, rabi_amp=None):
        data = result.data
        def rabi(amplitudes, frequency, a0, b0, a1, b1):
            amplitudes_0 = amplitudes[0:len(amplitudes)//2]
            amplitudes_1 = amplitudes[len(amplitudes)//2:]
            return np.concatenate([
                a0 * np.cos(2 * np.pi * 0.5 * amplitudes_0/frequency) + b0,
                a1 * np.cos(2 * np.pi * 0.5 * amplitudes_1/frequency) + b1,
            ])
        
        def rabi_check(amp, frequency):
            return 0.5 - np.cos(2 * np.pi * 0.5 * amp/frequency) * 0.5

        p0 = [rabi_amp or 0.1, 1e-5, 2e-4, -1e-5, -5e-5]
        res, _ = opt.curve_fit(
            rabi,
            np.concatenate([np.array(data.coords["amplitude"]), np.array(data.coords["amplitude"])]),
            np.concatenate([np.array(data["iq"].real), np.array(data["iq"].imag)]),
            p0=p0,
            ftol=1e-12, xtol=1e-12, gtol=1e-12
        )


        rabi_f, a0, b0, a1, b1 = res
        g_state_readout = (b0 + a0) + (b1 + a1)*1.j
        e_state_readout = (b0 - a0) + (b1 - a1)*1.j

        e_state_readout = e_state_readout - g_state_readout

        data["e_state"] = (
            (data["iq"] - g_state_readout) * np.conjugate(e_state_readout)/np.abs(e_state_readout)**2
        ).real

        fig, ax = plt.subplots(constrained_layout=True)
        fig.suptitle(f"{result.id}_{self.experiment_name}")
        data["e_state"].plot.scatter(ax=ax, label="data")
        ax.plot(
            data.coords["amplitude"],
            rabi_check(data.coords["amplitude"], rabi_f),
            label=format_res(["Rabi amp (arb)"], [rabi_f])
        )
        ax.legend()

        return rabi_f, g_state_readout, np.conjugate(e_state_readout)/np.abs(e_state_readout)**2




class TimeRabi(QTLQMExperiment):
    experiment_name = "QM-TimeRabi"

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


class Ramsey2F(QTLQMExperiment):
    experiment_name = "QM-Ramsey2F"

    def sweep_labels(self):
        return [("detuning", "Hz"), ("time", "ns")]

    def get_program(self, Navg, sweeps, wait_after=50000):
        delay_sweep = sweeps[1]//4
        qubit_IF = self.station.settings["qubit_frequency"] - self.station.settings["qubit_LO"]
        detuning_sweep = qubit_IF + sweeps[0]
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
    
    def analyze_data(self, result):
        result.add_e_state()

        def exp_sine(time, detune, p0, tau, e0, e1):
            return e0 + e1 * np.sin(2 * np.pi * detune * time/1e9 + p0) * np.exp(-(time/1e9)/tau)

        fig, ax = plt.subplots(constrained_layout=True)
        fig.suptitle(f"{result.id}_{self.experiment_name}")

        detunes = []
        for detun in data.coords["detuning"]:
            _data = data["e_state"].sel(detuning=detun)
            _data.plot(ax=ax, x="time", label=f"Detuning (Hz): {float(detun)}")
            p0 = [np.abs(detun)*1.2, 0, 1e-6, 0.5, 0.5]
            res, _ = opt.curve_fit(
                exp_sine,
                _data["time"],
                _data,
                p0=p0,
                maxfev=5000
            )
            ax.plot(_data["time"], exp_sine(_data["time"], *res), label=format_res(
                ["Frequency (Hz)", "T2 (ns)"], [res[0], res[2]]
            ))
            detunes.append(res[0])

        ax.set_title("")
        ax.legend()

        if any([_det > sum(np.abs(data.coords["detuning"])) for _det in detunes]):
            return self.station.settings["qubit_frequency"] + sum([-np.abs(_det) * np.sign(data_detung) for _det, data_detung in zip(detunes, data.coords["detuning"])]) * 2
        else:
            return self.station.settings["qubit_frequency"] + sum([-np.abs(_det) * np.sign(data_detung) for _det, data_detung in zip(detunes, data.coords["detuning"])]) * 0.5
    
            

class T1(QTLQMExperiment):
    experiment_name = "QM-T1"

    def sweep_labels(self):
        return [("time", "ns"), ]

    def get_program(self, Navg, sweeps, wait_after=50000):
        delay_sweep = sweeps[0]//4
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

            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(t, delay_sweep)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                    # Play the qubit pulse with a variable amplitude (pre-factor to the pulse amplitude defined in the config)
                    
                    # play("x180" * amp(a), "qubit")
                    play("x180", "qubit")
                    # wait(t, "qubit")
                    wait(t, "qubit") # in units of 4 ns
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
                I_stream.buffer(len(delay_sweep)).average().save("I")
                Q_stream.buffer(len(delay_sweep)).average().save("Q")
                n_stream.save("iteration")
        # === END QM program ===
        return t1_program
    
    def analyze_data(self, result):
        result.add_e_state()
        data = result.data

        fig, ax = plt.subplots(constrained_layout=True)
        fig.suptitle(f"{result.id}_{self.experiment_name}")

        def t1(wait, tau, e0, e1):
            return np.exp(-(wait/1e9)/tau) * e1 + e0
        
        res, _ = opt.curve_fit(
            t1,
            data["time"],
            data["e_state"],
            p0=[10e-6, 0, 1]
        )
        

        data["e_state"].plot.scatter(ax=ax, x="time")
        ax.plot(data.coords["time"], t1(data.coords["time"], *res), label=format_res(
            ["T1 (ns)"], [res[0]]
        ))
        ax.legend()


    
class SingleShotReadout(QTLQMExperiment):
    experiment_name = "QM-SingleShotReadout"

    def sweep_labels(self):
        return [("iteration", ""), ("state", "")]
        
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
    
    def analyze_data(self, result):
        fig, ax = plt.subplots(constrained_layout=True)
        fig.suptitle(f"{result.id}_{self.experiment_name}")

        ax.scatter(
            result.data["iq"].sel(state="ground").real,
            result.data["iq"].sel(state="ground").imag,
            label="ground state"
        )
        ax.scatter(
            result.data["iq"].sel(state="excited").real,
            result.data["iq"].sel(state="excited").imag,
            label="excited state"
        )
        ax.scatter(
            result.data["iq"].sel(state="ground").real.mean(),
            result.data["iq"].sel(state="ground").imag.mean(),
            label="ground state average"
        )
        ax.scatter(
            result.data["iq"].sel(state="excited").real.mean(),
            result.data["iq"].sel(state="excited").imag.mean(),
            label="excited state average"
        )
        ax.legend()
        ax.set_xlabel("I")
        ax.set_ylabel("Q")