from qtl_control.qtl_experiments.database import FileSystemDB, RelationalDB
from qtl_control.qtl_experiments.experiment import ExperimentResult

def test_file_db(station_w_filedb):
    assert type(station_w_filedb.db) == FileSystemDB
    
    load_result = station_w_filedb.load_result(0)
    assert load_result


def test_relational_db(station_w_relational_db):
    assert type(station_w_relational_db.db) == RelationalDB

    load_result = station_w_relational_db.load_result(0)
    assert load_result

    load_result = station_w_relational_db.load_result(1)
    assert load_result


def test_relational_db_configs(station_w_relational_db):
    station_w_relational_db.load_full_config(["Q4"], "Q4_test_config") # Load full config, save to database
    assert station_w_relational_db.config["Q4"].frequency == 5.8e9

    config_change_key = station_w_relational_db.change_config(["Q4"], {"Q4": {"frequency": 6e9}})
    assert station_w_relational_db.config["Q4"].frequency == 6e9

    station_w_relational_db.change_config(["Q4"], {"Q4": {"frequency": 6.2e9}})
    assert station_w_relational_db.config["Q4"].frequency == 6.2e9
    
    station_w_relational_db.save_config("Q4_test_saved_config")
    assert station_w_relational_db.config["Q4"].frequency == 6.2e9

    station_w_relational_db.load_full_config(["Q4"], "Q4_test_config")
    assert station_w_relational_db.config["Q4"].frequency == 5.8e9

    station_w_relational_db.load_to_checkpoint(["Q4"], config_change_key)
    assert station_w_relational_db.config["Q4"].frequency == 6e9
