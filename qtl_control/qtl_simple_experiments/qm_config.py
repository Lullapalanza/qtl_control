import numpy as np
from qualang_tools.config.waveform_tools import drag_gaussian_pulse_waveforms
from qualang_tools.units import unit

u = unit(coerce_to_integer=True)


def generate_config(settings): # readout_LO_frequency=ro_LO, readout_amp=0.01):
    readout_LO = settings["readout_LO"]
    readout_IF = settings["readout_IF"]
    readout_amp = settings["readout_amp"]
    readout_len = settings["readout_len"]

    qubit_LO = settings["qubit_LO"]
    qubit_IF = settings["qubit_IF"]

    time_of_flight = 200
    octave_label = "oct1"

    OCTAVE_CONFIG = {
        octave_label: {
            "connectivity": "con1", # Default connectivity/magic,
            "RF_outputs": {
                1: {
                    "LO_frequency": readout_LO,
                    "LO_source": "internal",
                    "gain": -20, # -20 to 20 in 0.5 steps
                    "output_mode": "always_on",
                },
                5: {
                    "LO_frequency": qubit_LO,
                    "LO_source": "internal",
                    "output_mode": "always_on",
                    "gain": -15,
                },
                # 2: {...},
                # 3: {...},
                # 4: {...},
                # 5: {...}
            },
            "RF_inputs": {
                1: {
                    "LO_frequency": readout_LO, #
                    "LO_source": "internal", #
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
                9: {"offset": 0.0},  # I qubit
                10: {"offset": 0.0},  # Q qubit
                # 5: {"offset": 0.0},  # flux line?
            },
            "digital_outputs": {
                1: {},
            },
            "analog_inputs": {
                1: {"offset": 0.0, "gain_db": 20},  # I from down-conversion
                2: {"offset": 0.0, "gain_db": 20},  # Q from down-conversion
            },
        },
    }

    ELEMENTS_CONFIG = {
        "qubit": {
            "RF_inputs": {"port": ("oct1", 5)},
            "intermediate_frequency": qubit_IF,
            "operations": {
                "cw": "const_pulse",
                "saturation": "saturation_pulse",
                "pi": "pi_pulse",
                "pi_half": "pi_half_pulse",
                "x90": "x90_pulse",
                "x180": "x180_pulse",
                "-x90": "-x90_pulse",
                "y90": "y90_pulse",
                "y180": "y180_pulse",
                "-y90": "-y90_pulse",
            },
        },
        "resonator": {
            "RF_inputs": {"port": ("oct1", 1)},
            "RF_outputs": {"port": ("oct1", 1)},
            "intermediate_frequency": readout_IF,
            "operations": {
                "cw": "const_pulse",
                "readout": "readout_pulse",
            },
            "time_of_flight": time_of_flight,
            "smearing": 0,
        },
        # "flux_line": {
        #     "singleInput": {
        #         "port": ("con1", 5),
        #     },
        #     "operations": {
        #         "const": "const_flux_pulse",
        #     },
        # },
    }

    CONST_LEN = 300
    CONST_FLUX_LEN = 300
    SATURATION_LEN = 1000
    SQ_PULSE_LEN = 300

    CONST_AMP = 0.4
    SATURATION_AMP = 0.4
    PI_AMP = 0.4
    FLUX_AMP = 0.001

    GDRAG_SIGMA = SQ_PULSE_LEN / 4
    GDRAG_COEFF = 0
    GDRAG_ALPHA = -200 * u.MHz
    GDRAG_STARK = 0
    SQ_gaussian, SQ_gaus_der = np.array(
        drag_gaussian_pulse_waveforms(PI_AMP, SQ_PULSE_LEN, GDRAG_SIGMA, GDRAG_COEFF, GDRAG_ALPHA, GDRAG_STARK)
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
        "readout_wf": {"type": "constant", "sample": readout_amp},
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
                    "Q": "pi_wf",
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
                "length": readout_len,
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
                "cosine": [(1.0, readout_len)],
                "sine": [(0.0, readout_len)],
            },
            "sine_weights": {
                "cosine": [(0.0, readout_len)],
                "sine": [(1.0, readout_len)],
            },
            "minus_sine_weights": {
                "cosine": [(0.0, readout_len)],
                "sine": [(-1.0, readout_len)],
            }
        },
    }

    return config
