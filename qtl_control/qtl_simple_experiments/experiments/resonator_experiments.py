import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
from qm.qua import *
from qualang_tools.loops import from_array

from qtl_control.qtl_simple_experiments.experiments.base import QTLQMExperiment


def notch_res(f, f0, a, alpha, phi, kext, kint):
    return a * np.exp(1.j * alpha) * (1 - (np.exp(1.j * phi)/np.cos(phi)) * kext / (2j * (f - f0) + (kext + kint)))

def notch_res_abs(f, f0, a, alpha, phi, kext, kint):
    return np.abs(notch_res(f0, a, alpha, phi, kext, kint))

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
    
    def analyze_data(self, data):
        res, _ = opt.curve_fit(notch_res_abs, data["readout_frequency"], np.abs(data["iq"]))
        plt.plot(res["readout_frequency"], np.abs(data["iq"]))
        plt.plot(res["readout_frequency"], notch_res_abs(res["readout_frequency"], *res))
        plt.show()


class ReadoutFluxSpectroscopy(QTLQMExperiment):
    experiment_name = "QMReadoutFluxSpectroscopy"

    def sweep_labels(self):
        return ["amplitude", "readout_frequency"]

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
    
    def analyze_data(self, data):
        frequencies = []
        amplitudes = data.coords["amplitude"]
        for a in amplitudes:
            data_slice = np.abs(data["iq"].sel(amplitude=a))
            res, _ = opt.curve_fit(notch_res_abs, data_slice["readout_frequency"], data_slice)
            frequencies.append(res[0])

        def cosine_dep(v, period, offset, a, b):
            return a * np.cos(2 * np.pi * v/period + offset) + b

        res, _ = opt.curve_fit(cosine_dep, amplitudes, frequencies, bounds=(
            [0.001, -np.pi, 0, 2e9],
            [100, np.pi, 1e9, 10e9]
        ))
        plt.scatter(amplitudes, frequencies)
        plt.plot(amplitudes, cosine_dep(amplitudes, *res))
        plt.show()

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
