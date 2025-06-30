import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
from qm.qua import *
from qualang_tools.loops import from_array
from qualang_tools.units import unit
u = unit(coerce_to_integer=True)

from qtl_control.qtl_simple_experiments.experiments.base import QTLQMExperiment


def notch_res(f, f0, a, alpha, phi, kext, kint):
    return a * np.exp(1.j * alpha) * (1 - (np.exp(1.j * phi)/np.cos(phi)) * kext / (2j * (f - f0) + (kext + kint)))

def notch_res_abs(f, f0, a, phi, kext, kint):
    return np.abs(notch_res(f, f0, a, 0, phi, kext, kint))

def format_res(labels, values):
    return f"Fit:\n" + "\n".join([f"{label}: {float(v):.3e}" for label, v in zip(labels, values)])

class ReadoutResonatorSpectroscopy(QTLQMExperiment):
    experiment_name = "QM-ReadoutResonatorSpectroscopy"

    def sweep_labels(self):
        return [("readout_frequency", "Hz"), ]

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
                    wait(wait_after//4, "resonator")
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
    
    def analyze_data(self, result, plot=True):
        res, _ = opt.curve_fit(
            notch_res_abs,
            result.data.coords["readout_frequency"],
            np.abs(result.data["iq"]),
            p0=[result.data.coords["readout_frequency"].mean(), np.abs(result.data["iq"]).max(), 0, 1e5, 1e5]
        )
        if plot:
            axs = result.mag_phase_plot()
            axs[0].plot(
                result.data.coords["readout_frequency"],
                notch_res_abs(result.data.coords["readout_frequency"], *res),
                label=format_res(["f0 (GHz)", "a (V)", "phi (rad)", "kext (Hz)", "kint (Hz)"], res)
            )
            axs[0].legend()

        return float(notch_res_abs(result.data.coords["readout_frequency"], *res).idxmin())


class ReadoutFluxSpectroscopy(QTLQMExperiment):
    experiment_name = "QM-ReadoutFluxSpectroscopy"

    def sweep_labels(self):
        return [("amplitude", "arb"), ("readout_frequency", "Hz")]

    def get_program(self, Navg, sweeps, wait_after=1000):
        amp_sweep = sweeps[0]
        if_sweep = sweeps[1] - self.station.settings["readout_LO"]
        with program() as resonator_spec:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the readout frequency
            a = declare(fixed)  # QUA variable for the measured 'I' quadrature
            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(a, amp_sweep)):  # QUA for_ loop for sweeping the frequency
                    set_dc_offset("flux_line", "single", a)
                    with for_(*from_array(f, if_sweep)):  # QUA for_ loop for sweeping the frequency
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
                        wait(wait_after//4, "resonator")
                        # Save the 'I' & 'Q' quadratures to their respective streams
                        save(I, I_st)
                        save(Q, Q_st)
                    # Save the averaging iteration to get the progress bar
                save(n, n_st)


            set_dc_offset("flux_line", "single", 0)

            with stream_processing():
                I_st.buffer(len(if_sweep)).buffer(len(amp_sweep)).average().save("I")
                Q_st.buffer(len(if_sweep)).buffer(len(amp_sweep)).average().save("Q")
                n_st.save("iteration")
        
        return resonator_spec
    
    def analyze_data(self, result, p0=None):
        data = result.data

        frequencies = []
        amplitudes = data.coords["amplitude"]
        for a in amplitudes:
            data_slice = np.abs(data["iq"].sel(amplitude=a))
            res, _ = opt.curve_fit(
                notch_res_abs,
                data_slice["readout_frequency"],
                data_slice,
                p0=[float(data_slice["readout_frequency"].mean()), 0.001, 0, 10e6, 10e6]
            )
            frequencies.append(res[0])

        def cosine_dep(v, period, offset, a, b):
            return a * np.cos(2 * np.pi * (v-offset)/period) + b

        p0 = p0 or [0.4, 0, 1e6, np.mean(frequencies)]
        res, _ = opt.curve_fit(
            cosine_dep,
            amplitudes,
            frequencies,
            bounds=(
                [0.0001, -1, 0, float(data_slice["readout_frequency"].min())],
                [1, 1, 1e9, float(data_slice["readout_frequency"].max())]
            ),
            p0=p0,
            ftol=1e-10, xtol=1e-10, gtol=1e-10
        )

        axs = result.mag_phase_plot(y_axis="readout_frequency")
        axs[0].scatter(amplitudes, frequencies)
        axs[0].plot(
            amplitudes,
            cosine_dep(amplitudes, *res),
            label=format_res(["period (V)", "offset (V)", "a", "b"], res)
        )

        axs[0].legend(bbox_to_anchor=(1.75, 0.8))

        return res

class PunchOut(QTLQMExperiment):
    experiment_name = "QM-PunchOut"

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
                        wait(wait_after//4, "resonator")
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


class DispersiveShift(QTLQMExperiment):
    experiment_name = "QM-DispersiveShift"

    def sweep_labels(self):
        return [("readout_frequency", "Hz"), ("state", "")]

    def get_program(self, Navg, sweeps, wait_after=10000):
        sweep = sweeps[0] - self.station.settings["readout_LO"]
        sweep_state = [0, 1]
        with program() as resonator_spec:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the readout frequency
            op = declare(int)
            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < Navg, n + 1):  # QUA for_ loop for averaging
                with for_(*from_array(f, sweep)):  # QUA for_ loop for sweeping the frequency
                    update_frequency("resonator", f)
                    with for_(*from_array(op, sweep_state)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                # Measure the state of the resonator
                        with if_(op==1):
                            play("x180", "qubit")
                            wait(400 * u.ns, "qubit")
                        align("qubit", "resonator")
                    # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                        measure(
                            "readout",
                            "resonator",
                            None,
                            dual_demod.full("cos", "sin", I),
                            dual_demod.full("minus_sin", "cos", Q),
                        )
                    # Wait for the resonator to deplete
                        wait(wait_after//4, "resonator")
                        # Save the 'I' & 'Q' quadratures to their respective streams
                        save(I, I_st)
                        save(Q, Q_st)
                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                I_st.buffer(len(sweep_state)).buffer(len(sweep)).average().save("I")
                Q_st.buffer(len(sweep_state)).buffer(len(sweep)).average().save("Q")
                n_st.save("iteration")
        
        return resonator_spec
    
    def analyze_data(self, result):
        fig, ax = plt.subplots(constrained_layout=True)
        fig.suptitle(f"{result.id}_{self.experiment_name}")

        res0, _ = opt.curve_fit(
            notch_res_abs,
            result.data.coords["readout_frequency"],
            np.abs(result.data["iq"].sel(state="ground")),
            p0=[result.data.coords["readout_frequency"].mean(), np.abs(result.data["iq"]).max(), 0, 1e5, 1e5]
        )
        ax.plot(
            result.data.coords["readout_frequency"],
            np.abs(result.data["iq"].sel(state="ground")), label="ground state"
        )
        ax.plot(
            result.data.coords["readout_frequency"],
            notch_res_abs(result.data.coords["readout_frequency"], *res0), label="ground state fit"
            # label="\n".join([f"{_:.4e}" for _ in res])
        )

        res1, _ = opt.curve_fit(
            notch_res_abs,
            result.data.coords["readout_frequency"],
            np.abs(result.data["iq"].sel(state="excited")),
            p0=[result.data.coords["readout_frequency"].mean(), np.abs(result.data["iq"]).max(), 0, 1e5, 1e5]
        )
        ax.plot(
            result.data.coords["readout_frequency"],
            np.abs(result.data["iq"].sel(state="excited")), label="excited"
        )
        ax.plot(
            result.data.coords["readout_frequency"],
            notch_res_abs(result.data.coords["readout_frequency"], *res1), label=f"excited state fit\nDispersive shift: {res1[0] - res0[0]:.3e}"
            # label="\n".join([f"{_:.4e}" for _ in res])
        )
        ax.legend()
        ax.set_ylabel(r"$Magnitude, \ |S|$ (V)")
        ax.set_xlabel("Readout_frequency")

        print(res1[0] - res0[0])