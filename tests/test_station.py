def test_config_load(station):
    station.reload_config(["Q7"])
    assert station.config["Q7"].frequency == 5.8e9
    assert station.config["Q7"].drive.LO_frequency == 6e9

    station.config["Q7"].frequency = 5.9e9
    station.reload_config(["Q7"])
    assert station.config["Q7"].frequency == 5.9e9