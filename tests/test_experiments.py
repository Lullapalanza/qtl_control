import numpy as np
from qtl_control.qtl_experiments.resonator_experiments import *
from qtl_control.qtl_experiments.qubit_experiments import *
from qtl_control.qtl_station.station import MockResHandles


def test_readout_spectroscopy(station):
    rrs = ReadoutResonatorSpectroscopy()
    
    MockResHandles.mock_data = [
        np.ones(100), np.ones(100), 1024
    ]
    res = rrs.run("Q7", [np.arange(5e9, 5.1e9, 1e6)])
    print(res.data)
    res.analyze()


def test_rabi(station):
    rabi = Rabi()

    MockResHandles.mock_data = [
        np.ones(10), np.ones(10), 1024
    ]
    res = rabi.run("Q7", [np.arange(0, 1, 0.1)])
    analysis_result = res.analyze()
    assert analysis_result["Q7"]["X180_duration"] == 100

    res = rabi.run("Q7", [np.arange(0, 1, 0.1)], pulse_duration=200)
    analysis_result = res.analyze()
    assert analysis_result["Q7"]["X180_duration"]== 200