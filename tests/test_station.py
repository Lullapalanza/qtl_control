from qtl_control.qtl_station.station import StationSettingsChanger

def test_config_load(station_w_filedb):
    station_w_filedb.load_full_config(["Q7"], "test")
    config = station_w_filedb.station.config
    assert station_w_filedb.config["Q7"].frequency == 5.8e9
    assert station_w_filedb.config["Q7"].drive.LO_frequency == 6e9

    station_w_filedb.config["Q7"].frequency = 5.9e9
    station_w_filedb.change_config(["Q7"])
    assert station_w_filedb.config["Q7"].frequency == 5.9e9

def test_change_context(station_w_filedb):
    station_w_filedb.load_full_config(["Q7"], "test")
    assert station_w_filedb.config["Q7"].frequency == 5.8e9
    with station_w_filedb.change_settings():
        station_w_filedb.config["Q7"].frequency = 5.9e9
    assert station_w_filedb.config["Q7"].frequency == 5.9e9


def test_qm_config(station_w_filedb):
    with station_w_filedb.change_settings():
        station_w_filedb.config["Q7"].X180_amplitude = 0.999
    station_w_filedb.change_config(["Q7", "Q4"])
    assert station_w_filedb.config["Q7"].X180_amplitude == 0.999
