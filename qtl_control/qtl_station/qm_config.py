import numpy as np

from qualang_tools.config.waveform_tools import drag_gaussian_pulse_waveforms

from qtl_control.qtl_station.station import u


def generate_config(
    elements_to_run,
    rf_output_channels,
    rf_input_channels,
    analog_output_channels,
    element_conn
    ):

    # TODO: FIXME
    octave_label = "oct1"
    time_of_flight = 200

    OCTAVE_CONFIG = {
        octave_label: {
            "connectivity": "con1", # Default connectivity/magic,
            "RF_outputs": {
                int(id.strip("RF")): {
                    "LO_frequency": rf_ch.LO_frequency,
                    "gain": rf_ch.gain,
                    "output_mode": "always_on",
                    "LO_source": "internal"
                } for id, rf_ch in rf_output_channels.items()
            },
            "RF_inputs": {
                int(id.strip("RF_").strip("_in")): {
                    "LO_frequency": rf_ch.LO_frequency,
                    "LO_source": "internal"
                } for id, rf_ch in rf_input_channels.items()
            }
        }
    }

    CONTROLLER_CONFIG = {
        "con1": {
            "analog_outputs": {
                id: {"offset": config_out.dc_volt if (config_out:=analog_output_channels.get(f"AO{id}")) else 0} for id in range(1, 11)
            },
            "digital_outputs": {
                1: {},
            },
            "analog_inputs": {
                1: {"offset": 0.0, "gain_db": 20}, # 20},  # I from down-conversion
                2: {"offset": 0.0, "gain_db": 20}, # 20},  # Q from down-conversion
            },
        },
    }

    OPERATIONS = {
        "cw": "const_pulse",
        "saturation": "saturation_pulse",
        "pi": "pi_pulse",
        "pi_half": "pi_half_pulse",
        "gauss": "gauss_pulse"
    }

    OPERATIONS_PER_ELEMENT = {}

    for element in elements_to_run:
        OPERATIONS_PER_ELEMENT.update({element: {
            f"{element}_idle": f"{element}_idle_pulse",
            f"{element}_x90": f"{element}_x90_pulse",
            f"{element}_x180": f"{element}_x180_pulse",
            f"{element}_-x90": f"{element}_-x90_pulse",
            f"{element}_y90": f"{element}_y90_pulse",
            f"{element}_y180": f"{element}_y180_pulse",
            f"{element}_-y90": f"{element}_-y90_pulse",     
        }})

    # ADD DRIVES
    ELEMENTS_CONFIG = {
        f"drive_{qb_id}": {
            "RF_inputs": {"port": ("oct1", int(element_conn[qb_id].drive.channel_id.strip("RF")))},
            "intermediate_frequency": element_conn[qb_id].frequency - element_conn[qb_id].drive.LO_frequency,
            "operations": OPERATIONS | OPERATIONS_PER_ELEMENT[qb_id]
        } for qb_id in elements_to_run
    }
    # ADD READOUT
    ELEMENTS_CONFIG.update({
        f"resonator_{element}": {
            "RF_inputs": {"port": ("oct1", 1)},
            "RF_outputs": {"port": ("oct1", 1)},
            "intermediate_frequency": element_conn[element].readout_frequency - OCTAVE_CONFIG[octave_label]["RF_outputs"][1]["LO_frequency"],
            "operations": {
                "cw": "const_pulse",
                "readout": f"readout_pulse_{element}",
            },
            "time_of_flight": time_of_flight,
            "smearing": 0,
        } for element in elements_to_run
    })
    ELEMENTS_CONFIG.update({
        f"flux_{element}": {
            "singleInput": {"port": ("con1", int(element_conn[element].flux.channel_id.strip("AO")))}
        } for element in elements_to_run if element_conn[element].flux is not None
    })

    CONST_LEN = 100 # X180_duration
    CONST_FLUX_LEN = 100 # X180_duration
    SATURATION_LEN = 1000
    # SQ_PULSE_LEN = 100 # X180_duration

    CONST_AMP = 0.45
    SATURATION_AMP = 0.45
    PI_AMP = 0.45
    FLUX_AMP = 0.45

    def get_gauss_wfs(SQ_PULSE_LEN):
        GDRAG_SIGMA = SQ_PULSE_LEN / 4
        SQ_gaussian = 0.5 * np.exp(-np.linspace(-SQ_PULSE_LEN//2, SQ_PULSE_LEN//2, SQ_PULSE_LEN)**2/(2*GDRAG_SIGMA**2))
        SQ_gaus_der = -np.linspace(-SQ_PULSE_LEN//2, SQ_PULSE_LEN//2, SQ_PULSE_LEN)/(2*GDRAG_SIGMA) * SQ_gaussian

        return SQ_gaussian, SQ_gaus_der

    pulse_lens_wfs = {
        elem: (element_conn[elem].X180_duration, *get_gauss_wfs(element_conn[elem].X180_duration)) for elem in elements_to_run
    }
    SQ_gaussian = 0.5 * np.exp(-np.linspace(-100//2, 100//2, 100)**2/(2*25**2))
    SQ_gaus_der = -np.linspace(-100//2, 100//2, 100)/(2*25) * SQ_gaussian



    # X180_amplitude = 0.1473
    WAVEFORMS_CONFIG = {
        "const_wf": {"type": "constant", "sample": CONST_AMP},
        "saturation_drive_wf": {"type": "constant", "sample": SATURATION_AMP},
        "pi_wf": {"type": "constant", "sample": PI_AMP},
        "pi_half_wf": {"type": "constant", "sample": PI_AMP / 2},
        "const_flux_wf": {"type": "constant", "sample": FLUX_AMP},
        "zero_wf": {"type": "constant", "sample": 0.0},
        "gauss_I_wf": {"type": "arbitrary", "samples": SQ_gaussian.tolist()},
        "gauss_Q_wf": {"type": "arbitrary", "samples": SQ_gaus_der.tolist()},
    }

    for elem in elements_to_run:
        amp = element_conn[elem].X180_amplitude
        drag_amp = element_conn[elem].drag_coef
        SQ_gaussian = pulse_lens_wfs[elem][1]
        SQ_gaus_der = pulse_lens_wfs[elem][2]

        WAVEFORMS_CONFIG.update({
            f"{elem}_idle_wf": {"type": "arbitrary", "samples": np.zeros(pulse_lens_wfs[elem][0]).tolist()},
            f"{elem}_x180_I_wf": {"type": "arbitrary", "samples": (SQ_gaussian*amp).tolist()},
            f"{elem}_x180_Q_wf": {"type": "arbitrary", "samples": (SQ_gaus_der*amp*drag_amp).tolist()},
            f"{elem}_x90_I_wf": {"type": "arbitrary", "samples": (SQ_gaussian*amp/2).tolist()},
            f"{elem}_x90_Q_wf": {"type": "arbitrary", "samples": (SQ_gaus_der*amp*drag_amp/2).tolist()},
            f"{elem}_minus_x90_I_wf": {"type": "arbitrary", "samples": (-SQ_gaussian*amp/2).tolist()},
            f"{elem}_minus_x90_Q_wf": {"type": "arbitrary", "samples": (-SQ_gaus_der*amp*drag_amp/2).tolist()},

            f"{elem}_y180_I_wf": {"type": "arbitrary", "samples": (-SQ_gaus_der*amp*drag_amp).tolist()},
            f"{elem}_y180_Q_wf": {"type": "arbitrary", "samples": (SQ_gaussian*amp).tolist()},
            f"{elem}_y90_I_wf": {"type": "arbitrary", "samples": (-SQ_gaus_der*amp*drag_amp/2).tolist()},
            f"{elem}_y90_Q_wf": {"type": "arbitrary", "samples": (SQ_gaussian*amp/2).tolist()},
            f"{elem}_minus_y90_I_wf": {"type": "arbitrary", "samples": (SQ_gaus_der*amp*drag_amp/2).tolist()},
            f"{elem}_minus_y90_Q_wf": {"type": "arbitrary", "samples": (-SQ_gaussian*amp/2).tolist()},
        })

    WAVEFORMS_CONFIG.update({
        f"readout_wf_{id}": {"type": "constant", "sample": element_conn[id].readout_amplitude} for id in elements_to_run
    })

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
            "gauss_pulse":{
                "operation": "control",
                "length": 100,
                "waveforms": {
                    "I": "gauss_I_wf",
                    "Q": "gauss_Q_wf",
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
                "length": 100,
                "waveforms": {
                    "I": "pi_wf",
                    "Q": "pi_wf",
                },
            },
            "pi_half_pulse": {
                "operation": "control",
                "length": 100,
                "waveforms": {
                    "I": "pi_half_wf",
                    "Q": "zero_wf",
                },
            }
        },
        "integration_weights": {},
        "waveforms": WAVEFORMS_CONFIG,
        "digital_waveforms": {
            "ON": {"samples": [(1, 0)]},
        },
    }

    for element in elements_to_run:
        SQ_PULSE_LEN = pulse_lens_wfs[elem][0]
        config["pulses"].update({
            f"{element}_idle_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_idle_wf",
                    "Q": f"{element}_idle_wf",
                },
            },
            f"{element}_x90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_x90_I_wf",
                    "Q": f"{element}_x90_Q_wf",
                },
            },
            f"{element}_x180_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_x180_I_wf",
                    "Q": f"{element}_x180_Q_wf",
                },
            },
            f"{element}_-x90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_minus_x90_I_wf",
                    "Q": f"{element}_minus_x90_Q_wf",
                },
            },
            f"{element}_y90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_y90_I_wf",
                    "Q": f"{element}_y90_Q_wf",
                },
            },
            f"{element}_y180_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_y180_I_wf",
                    "Q": f"{element}_y180_Q_wf",
                },
            },
            f"{element}_-y90_pulse": {
                "operation": "control",
                "length": SQ_PULSE_LEN,
                "waveforms": {
                    "I": f"{element}_minus_y90_I_wf",
                    "Q": f"{element}_minus_y90_Q_wf",
                },
            },
        })

    for element in elements_to_run:
        config["pulses"].update({
            f"readout_pulse_{element}": {
                "operation": "measurement",
                "length": element_conn[element].readout_len,
                "waveforms": {
                    "I": f"readout_wf_{element}",
                    "Q": "zero_wf",
                },
                "integration_weights": {
                    "cos": f"cosine_weights_{element}",
                    "sin": f"sine_weights_{element}",
                    "minus_sin": f"minus_sine_weights_{element}",
                    # "rotated_cos": "rotated_cosine_weights",
                    # "rotated_sin": "rotated_sine_weights",
                    # "rotated_minus_sin": "rotated_minus_sine_weights",
                    # "opt_cos": "opt_cosine_weights",
                    # "opt_sin": "opt_sine_weights",
                    # "opt_minus_sin": "opt_minus_sine_weights",
                },
                "digital_marker": "ON",
            }
        })
        config["integration_weights"].update({
            f"cosine_weights_{element}": {
                "cosine": [(1.0, element_conn[element].readout_len)],
                "sine": [(0.0, element_conn[element].readout_len)],
            },
            f"sine_weights_{element}": {
                "cosine": [(0.0, element_conn[element].readout_len)],
                "sine": [(1.0, element_conn[element].readout_len)],
            },
            f"minus_sine_weights_{element}": {
                "cosine": [(0.0, element_conn[element].readout_len)],
                "sine": [(-1.0, element_conn[element].readout_len)],
            }     
        })

    return config
