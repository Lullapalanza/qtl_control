import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt

from qm.qua import *
from qualang_tools.loops import from_array

from qtl_control.qtl_station.station import u
from qtl_control.qtl_experiments import QTLQMExperiment
from qtl_control.qtl_experiments.utils import *

class ReadoutResonatorSpectroscopy(QTLQMExperiment):
    experiment_name = "QM-ReadoutResonatorSpectroscopy"

    def sweep_labels(self):
        return [("readout_frequency", "Hz"), ]

    def get_program(self, element, Navg, sweeps, wait_after=1000):
        sweep = sweeps[0] - self.station.config["PL"].LO_frequency
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
                    update_frequency(f"resonator_{element}", f)
                    # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                    standard_readout(f"resonator_{element}", I, I_st, Q, Q_st, wait_after)
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

        element = result.data.attrs["element"]
        f0 = float(notch_res_abs(result.data.coords["readout_frequency"], *res).idxmin())

        return {element: {
            "readout_frequency": f0
        }}
    


class ReadoutFluxSpectroscopy(QTLQMExperiment):
    experiment_name = "QM-ReadoutFluxSpectroscopy"

    def sweep_labels(self):
        return [("amplitude", "arb"), ("readout_frequency", "Hz")]

    def get_program(self, element, Navg, sweeps, wait_after=1000):
        amp_sweep = sweeps[0]
        if_sweep = sweeps[1] - self.station.config["PL"].LO_frequency
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
                    set_dc_offset(f"flux_{element}", "single", a)
                    with for_(*from_array(f, if_sweep)):  # QUA for_ loop for sweeping the frequency
                        update_frequency(f"resonator_{element}", f)
                        # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                        standard_readout(f"resonator_{element}", I, I_st, Q, Q_st, wait_after)

                    # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                I_st.buffer(len(if_sweep)).buffer(len(amp_sweep)).average().save("I")
                Q_st.buffer(len(if_sweep)).buffer(len(amp_sweep)).average().save("Q")
                n_st.save("iteration")
        
        return resonator_spec
    
    def analyze_data(self, result, p0=None):
        data = result.data

        fits = []
        amplitudes = data.coords["amplitude"]
        for a in amplitudes:
            data_slice = np.abs(data["iq"].sel(amplitude=a))
            res, _ = opt.curve_fit(
                notch_res_abs,
                data_slice["readout_frequency"],
                data_slice,
                p0=[float(data_slice["readout_frequency"].mean()), 0.001, 0, 10e6, 10e6]
            )
            fits.append(res)

        frequencies = [_[0] for _ in fits]

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

        element = data.attrs["element"]

        return {element: {
            "flux": {"dc_volt": res[1]}},
        }


class PunchOut(QTLQMExperiment):
    experiment_name = "QM-PunchOut"

    def sweep_labels(self):
        return ["readout_frequency", "amplitude"]

    def get_program(self, element, Navg, sweeps, wait_after=1000):
        freq_sweep = sweeps[0] - self.station.config["PL"].LO_frequency
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
                    update_frequency(f"resonator_{element}", f)
                    with for_each_(a, amplitude_sweep):
                    # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                        measure(
                            "readout" * amp(a),
                            f"resonator_{element}",
                            None,
                            dual_demod.full("cos", "sin", I),
                            dual_demod.full("minus_sin", "cos", Q),
                        )
                        # Wait for the resonator to deplete
                        wait(wait_after//4, f"resonator_{element}")
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

    def get_program(self, element, Navg, sweeps, wait_after=10000):
        sweep = sweeps[0] - self.station.config["PL"].LO_frequency
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
                    update_frequency(f"resonator_{element}", f)
                    with for_(*from_array(op, sweep_state)):  # QUA for_ loop for sweeping the pulse amplitude pre-factor
                # Measure the state of the resonator
                        with if_(op==1):
                            play(f"{element}_x180", f"drive_{element}")
                            wait(400 * u.ns, f"drive_{element}")
                        align(f"drive_{element}", f"resonator_{element}")
                    # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                        standard_readout(f"resonator_{element}", I, I_st, Q, Q_st, wait_after)
                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                I_st.buffer(len(sweep_state)).buffer(len(sweep)).average().save("I")
                Q_st.buffer(len(sweep_state)).buffer(len(sweep)).average().save("Q")
                n_st.save("iteration")
        
        return resonator_spec
    
    def analyze_data(self, result):
        fig, ax = plt.subplots(constrained_layout=True)
        fig.suptitle(result.get_title())

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