"""
For octave config https://docs.quantum-machines.co/1.2.1/docs/Guides/octave/
"""
def get_config(octave_label):
    resonator_LO = 6e9
    config = {
        "version": 1,
        "octaves": {
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
                    2: {...},
                    3: {...},
                    4: {...},
                    5: {...}
                },
                "RF_inputs": {
                    1: {
                        "RF_source": "RF_in",
                        "LO_frequency": resonator_LO, #
                        "LO_source": "internal", #
                        "IF_mode_I": "direct",  #
                        "IF_mode_Q": "direct"            
                    },
                    2: {...}
                }
            } 
        },
        "controllers": {
            "con1": {
                "analog_outputs": {
                    1: {"offset": 0.0},  # I qubit
                    2: {"offset": 0.0},  # Q qubit
                    3: {"offset": 0.0},  # I resonator
                    4: {"offset": 0.0},  # Q resonator
                    5: {"offset": max_frequency_point},  # flux line
                },
                "digital_outputs": {
                    1: {},
                },
                "analog_inputs": {
                    1: {"offset": 0.0, "gain_db": 0},  # I from down-conversion
                    2: {"offset": 0.0, "gain_db": 0},  # Q from down-conversion
                },
            },
        },
        "elements": {
            "qubit": {
                "mixInputs": {
                    "I": ("con1", 1),
                    "Q": ("con1", 2),
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
                    "I": ("con1", 3),
                    "Q": ("con1", 4),
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
            "flux_line_sticky": {
                "singleInput": {
                    "port": ("con1", 5),
                },
                "sticky": {"analog": True, "duration": 20},
                "operations": {
                    "const": "const_flux_pulse",
                },
            },
        },
        "pulses": {
            "const_single_pulse": {
                "operation": "control",
                "length": const_len,
                "waveforms": {
                    "single": "const_wf",
                },
            },
            "const_flux_pulse": {
                "operation": "control",
                "length": const_flux_len,
                "waveforms": {
                    "single": "const_flux_wf",
                },
            },
            "const_pulse": {
                "operation": "control",
                "length": const_len,
                "waveforms": {
                    "I": "const_wf",
                    "Q": "zero_wf",
                },
            },
            "saturation_pulse": {
                "operation": "control",
                "length": saturation_len,
                "waveforms": {"I": "saturation_drive_wf", "Q": "zero_wf"},
            },
            "pi_pulse": {
                "operation": "control",
                "length": square_pi_len,
                "waveforms": {
                    "I": "pi_wf",
                    "Q": "zero_wf",
                },
            },
            "pi_half_pulse": {
                "operation": "control",
                "length": square_pi_len,
                "waveforms": {
                    "I": "pi_half_wf",
                    "Q": "zero_wf",
                },
            },
            "x90_pulse": {
                "operation": "control",
                "length": x90_len,
                "waveforms": {
                    "I": "x90_I_wf",
                    "Q": "x90_Q_wf",
                },
            },
            "x180_pulse": {
                "operation": "control",
                "length": x180_len,
                "waveforms": {
                    "I": "x180_I_wf",
                    "Q": "x180_Q_wf",
                },
            },
            "-x90_pulse": {
                "operation": "control",
                "length": minus_x90_len,
                "waveforms": {
                    "I": "minus_x90_I_wf",
                    "Q": "minus_x90_Q_wf",
                },
            },
            "y90_pulse": {
                "operation": "control",
                "length": y90_len,
                "waveforms": {
                    "I": "y90_I_wf",
                    "Q": "y90_Q_wf",
                },
            },
            "y180_pulse": {
                "operation": "control",
                "length": y180_len,
                "waveforms": {
                    "I": "y180_I_wf",
                    "Q": "y180_Q_wf",
                },
            },
            "-y90_pulse": {
                "operation": "control",
                "length": minus_y90_len,
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
        "waveforms": {
            "const_wf": {"type": "constant", "sample": const_amp},
            "saturation_drive_wf": {"type": "constant", "sample": saturation_amp},
            "pi_wf": {"type": "constant", "sample": square_pi_amp},
            "pi_half_wf": {"type": "constant", "sample": square_pi_amp / 2},
            "const_flux_wf": {"type": "constant", "sample": const_flux_amp},
            "zero_wf": {"type": "constant", "sample": 0.0},
            "x90_I_wf": {"type": "arbitrary", "samples": x90_I_wf.tolist()},
            "x90_Q_wf": {"type": "arbitrary", "samples": x90_Q_wf.tolist()},
            "x180_I_wf": {"type": "arbitrary", "samples": x180_I_wf.tolist()},
            "x180_Q_wf": {"type": "arbitrary", "samples": x180_Q_wf.tolist()},
            "minus_x90_I_wf": {"type": "arbitrary", "samples": minus_x90_I_wf.tolist()},
            "minus_x90_Q_wf": {"type": "arbitrary", "samples": minus_x90_Q_wf.tolist()},
            "y90_Q_wf": {"type": "arbitrary", "samples": y90_Q_wf.tolist()},
            "y90_I_wf": {"type": "arbitrary", "samples": y90_I_wf.tolist()},
            "y180_Q_wf": {"type": "arbitrary", "samples": y180_Q_wf.tolist()},
            "y180_I_wf": {"type": "arbitrary", "samples": y180_I_wf.tolist()},
            "minus_y90_Q_wf": {"type": "arbitrary", "samples": minus_y90_Q_wf.tolist()},
            "minus_y90_I_wf": {"type": "arbitrary", "samples": minus_y90_I_wf.tolist()},
            "readout_wf": {"type": "constant", "sample": readout_amp},
        },
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
            },
            "opt_cosine_weights": {
                "cosine": opt_weights_real,
                "sine": opt_weights_minus_imag,
            },
            "opt_sine_weights": {
                "cosine": opt_weights_imag,
                "sine": opt_weights_real,
            },
            "opt_minus_sine_weights": {
                "cosine": opt_weights_minus_imag,
                "sine": opt_weights_minus_real,
            },
            "rotated_cosine_weights": {
                "cosine": [(np.cos(rotation_angle), readout_len)],
                "sine": [(np.sin(rotation_angle), readout_len)],
            },
            "rotated_sine_weights": {
                "cosine": [(-np.sin(rotation_angle), readout_len)],
                "sine": [(np.cos(rotation_angle), readout_len)],
            },
            "rotated_minus_sine_weights": {
                "cosine": [(np.sin(rotation_angle), readout_len)],
                "sine": [(-np.cos(rotation_angle), readout_len)],
            },
        },
        "mixers": {
            "mixer_qubit": [
                {
                    "intermediate_frequency": qubit_IF,
                    "lo_frequency": qubit_LO,
                    "correction": IQ_imbalance(mixer_qubit_g, mixer_qubit_phi),
                }
            ],
            "mixer_resonator": [
                {
                    "intermediate_frequency": resonator_IF,
                    "lo_frequency": resonator_LO,
                    "correction": IQ_imbalance(mixer_resonator_g, mixer_resonator_phi),
                }
            ],
        },
    }


    return config