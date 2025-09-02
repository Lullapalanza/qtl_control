from qtl_control.qtl_station.station import change_station

def test_config_load(station):
    station.reload_config(["Q7"])
    assert station.config["Q7"].frequency == 5.8e9
    assert station.config["Q7"].drive.LO_frequency == 6e9

    station.config["Q7"].frequency = 5.9e9
    station.reload_config(["Q7"])
    assert station.config["Q7"].frequency == 5.9e9

def test_change_context(station):
    station.reload_config(["Q7"])
    assert station.config["Q7"].frequency == 5.8e9
    with change_station(station):
        station.config["Q7"].frequency = 5.9e9
    assert station.config["Q7"].frequency == 5.9e9


def test_qm_config(station):
    with change_station(station):
        station.config["Q7"].X180_amplitude = 0.999
    station.reload_config(["Q7", "Q4"])
    assert station.config["Q7"].X180_amplitude == 0.999