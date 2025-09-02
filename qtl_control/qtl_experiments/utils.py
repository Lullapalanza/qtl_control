import numpy as np

from enum import Enum

from qm.qua import *


class ReadoutType(Enum):
    average = 1
    single_shot = 2


def notch_res(f, f0, a, alpha, phi, kext, kint):
    return a * np.exp(1.j * alpha) * (1 - (np.exp(1.j * phi)/np.cos(phi)) * kext / (2j * (f - f0) + (kext + kint)))

def notch_res_abs(f, f0, a, phi, kext, kint):
    return np.abs(notch_res(f, f0, a, 0, phi, kext, kint))

def format_res(labels, values):
    return f"Fit:\n" + "\n".join([f"{label}: {float(v):.3e}" for label, v in zip(labels, values)])

def standard_readout(element, I, I_st, Q, Q_st, wait_after):
    measure(
        "readout",
        element,
        None,
        dual_demod.full("cos", "sin", I),
        dual_demod.full("minus_sin", "cos", Q),
    )
    # Wait for the resonator to deplete
    # Save the 'I' & 'Q' quadratures to their respective streams
    save(I, I_st)
    save(Q, Q_st)
    wait(wait_after//4, element)