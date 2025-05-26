"""
For octave config https://docs.quantum-machines.co/1.2.1/docs/Guides/octave/
"""
import numpy as np
from qualang_tools.config.waveform_tools import drag_gaussian_pulse_waveforms
from qualang_tools.units import unit

u = unit(coerce_to_integer=True)
READOUT_LEN = 1000
qubit_LO = 4.3e9


def get_config(octave_label):
    resonator_LO = 6e9
    resonator_IF = -200e6
    qubit_IF = -150e6
    time_of_flight = 0

    OCTAVE_CONFIG = {
        octave_label: {
            "connectivity": "con1", # Default connectivity/magic,
            "RF_outputs": {
                1: {
                    "LO_frequency": resonator_LO,
                    "LO_source": "internal",
                    "gain": 0, # -20 to 20 in 0.5 steps
                    "output_mode": "always_on",
                    "input_attenuators": "OFF"
                },
                # 2: {...},
                # 3: {...},
                # 4: {...},
                # 5: {...}
            },
            "RF_inputs": {
                1: {
                    "RF_source": "RF_in",
                    "LO_frequency": resonator_LO, #
                    "LO_source": "internal", #
                    "IF_mode_I": "direct",  #
                    "IF_mode_Q": "direct"            
                },
                # 2: {...}
            }
        }
    }

    CONTROLLER_CONFIG = {
        "con1": {
            "analog_outputs": {
                1: {"offset": 0.0},  # I resonator
                2: {"offset": 0.0},  # Q resonators
                3: {"offset": 0.0},  # I qubit
                4: {"offset": 0.0},  # Q qubit
                5: {"offset": 0.0},  # flux line?
            },
            "digital_outputs": {
                1: {},
            },
            "analog_inputs": {
                1: {"offset": 0.0, "gain_db": 0},  # I from down-conversion
                2: {"offset": 0.0, "gain_db": 0},  # Q from down-conversion
            },
        },
    }

    ELEMENTS_CONFIG = {
        "qubit": {
            "mixInputs": {
                "I": ("con1", 3),
                "Q": ("con1", 4),
                "lo_frequency": qubit_LO,
                "mixer": "mixer_qubit",
            },
            "intermediate_frequency": qubit_IF,
            "operations": {
                "cw": "const_pulse",
                "saturation": "saturation_pulse",
                "pi": "pi_pulse",
                "pi_half": "pi_half_pulse",
                "x180": "x180_pulse",
                "x90": "x90_pulse",
                "-x90": "-x90_pulse",
                "y90": "y90_pulse",
                "y180": "y180_pulse",
                "-y90": "-y90_pulse",
            },
        },
        "resonator": {
            "mixInputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                "lo_frequency": resonator_LO,
                "mixer": "mixer_resonator",
            },
            "intermediate_frequency": resonator_IF,
            "operations": {
                "cw": "const_pulse",
                "readout": "readout_pulse",
            },
            "outputs": {
                "out1": ("con1", 1),
                "out2": ("con1", 2),
            },
            "time_of_flight": time_of_flight,
            "smearing": 0,
        },
        "flux_line": {
            "singleInput": {
                "port": ("con1", 5),
            },
            "operations": {
                "const": "const_flux_pulse",
            },
        },
    }

    READOUT_AMP = 0.01

    CONST_LEN = 100
    CONST_FLUX_LEN = 100
    SATURATION_LEN = 100
    SQ_PULSE_LEN = 100

    CONST_AMP = 0.1
    SATURATION_AMP = 0.1
    PI_AMP = 0.5
    FLUX_AMP = 0.001

    GDRAG_SIGMA = SQ_PULSE_LEN / 5
    GDRAG_COEFF = 0
    GDRAG_ALPHA = -200 * u.MHz
    GDRAG_STARK = 0
    SQ_gaussian, SQ_gaus_der = np.array(
        drag_gaussian_pulse_waveforms(1, SQ_PULSE_LEN, GDRAG_SIGMA, GDRAG_COEFF, GDRAG_ALPHA, GDRAG_STARK)
    )

    


    WAVEFORMS_CONFIG = {
        "const_wf": {"type": "constant", "sample": CONST_AMP},
        "saturation_drive_wf": {"type": "constant", "sample": SATURATION_AMP},
        "pi_wf": {"type": "constant", "sample": PI_AMP},
        "pi_half_wf": {"type": "constant", "sample": PI_AMP / 2},
        "const_flux_wf": {"type": "constant", "sample": FLUX_AMP},
        "zero_wf": {"type": "constant", "sample": 0.0},
        "x180_I_wf": {"type": "arbitrary", "samples": SQ_gaussian.tolist()},
        "x180_Q_wf": {"type": "arbitrary", "samples": SQ_gaus_der.tolist()},
        "x90_I_wf": {"type": "arbitrary", "samples": (SQ_gaussian/2).tolist()},
        "x90_Q_wf": {"type": "arbitrary", "samples": (SQ_gaus_der/2).tolist()},
        "minus_x90_I_wf": {"type": "arbitrary", "samples": (-SQ_gaussian/2).tolist()},
        "minus_x90_Q_wf": {"type": "arbitrary", "samples": (-SQ_gaus_der/2).tolist()},

        "y180_I_wf": {"type": "arbitrary", "samples": (-SQ_gaus_der).tolist()},
        "y180_Q_wf": {"type": "arbitrary", "samples": (SQ_gaussian).tolist()},
        "y90_I_wf": {"type": "arbitrary", "samples": (-SQ_gaus_der/2).tolist()},
        "y90_Q_wf": {"type": "arbitrary", "samples": (SQ_gaussian/2).tolist()},
        "minus_y90_I_wf": {"type": "arbitrary", "samples": (SQ_gaus_der/2).tolist()},
        "minus_y90_Q_wf": {"type": "arbitrary", "samples": (-SQ_gaussian/2).tolist()},
        "readout_wf": {"type": "constant", "sample": READOUT_AMP},
    }

    config = {
        "version": 1,
        "octaves": OCTAVE_CONFIG,
        "controllers": CONTROLLER_CONFIG,
        "elements": ELEMENTS_CONFIG,
        "pulses": {
            "const_single_pulse": {
                "operation": "control",
                "length": CONST_LEN,
                "waveforms": {
                    "single": "const_wf",
                },
            },
            "const_pulse": {
                "operation": "control",
                "length": CONST_LEN,
                "waveforms": {
                    "I": "const_wf",
                    "Q": "zero_wf",
                },
            },
            "const_flux_pulse": {
                "operation": "control",
                "length": CONST_FLUX_LEN,
                "waveforms": {
                    "single": "const_flux_wf",
                },
            },
            "saturation_pulse": {
                "operation": "control",
                "length": SATURATION_LEN,
                "waveforms": {"I": "saturation_drive_wf", "Q": "zero_wf"},
            },
            "pi_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "pi_wf",
                    "Q": "zero_wf",
                },
            },
            "pi_half_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "pi_half_wf",
                    "Q": "zero_wf",
                },
            },
            "x90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "x90_I_wf",
                    "Q": "x90_Q_wf",
                },
            },
            "x180_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "x180_I_wf",
                    "Q": "x180_Q_wf",
                },
            },
            "-x90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "minus_x90_I_wf",
                    "Q": "minus_x90_Q_wf",
                },
            },
            "y90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "y90_I_wf",
                    "Q": "y90_Q_wf",
                },
            },
            "y180_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "y180_I_wf",
                    "Q": "y180_Q_wf",
                },
            },
            "-y90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": "minus_y90_I_wf",
                    "Q": "minus_y90_Q_wf",
                },
            },
            "readout_pulse": {
                "operation": "measurement",
                "length": READOUT_LEN,
                "waveforms": {
                    "I": "readout_wf",
                    "Q": "zero_wf",
                },
                "integration_weights": {
                    "cos": "cosine_weights",
                    "sin": "sine_weights",
                    "minus_sin": "minus_sine_weights",
                    "rotated_cos": "rotated_cosine_weights",
                    "rotated_sin": "rotated_sine_weights",
                    "rotated_minus_sin": "rotated_minus_sine_weights",
                    "opt_cos": "opt_cosine_weights",
                    "opt_sin": "opt_sine_weights",
                    "opt_minus_sin": "opt_minus_sine_weights",
                },
                "digital_marker": "ON",
            },
        },
        "waveforms": WAVEFORMS_CONFIG,
        "digital_waveforms": {
            "ON": {"samples": [(1, 0)]},
        },
        "integration_weights": {
            "cosine_weights": {
                "cosine": [(1.0, READOUT_LEN)],
                "sine": [(0.0, READOUT_LEN)],
            },
            "sine_weights": {
                "cosine": [(0.0, READOUT_LEN)],
                "sine": [(1.0, READOUT_LEN)],
            },
            "minus_sine_weights": {
                "cosine": [(0.0, READOUT_LEN)],
                "sine": [(-1.0, READOUT_LEN)],
            }
        },
        "mixers": {
            "mixer_qubit": [
                {
                    "intermediate_frequency": qubit_IF,
                    "lo_frequency": qubit_LO,
                    # "correction": IQ_imbalance(mixer_qubit_g, mixer_qubit_phi),
                }
            ],
            "mixer_resonator": [
                {
                    "intermediate_frequency": resonator_IF,
                    "lo_frequency": resonator_LO,
                    # "correction": IQ_imbalance(mixer_resonator_g, mixer_resonator_phi),
                }
            ],
        },
    }

    return config