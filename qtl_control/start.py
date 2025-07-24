import yaml

from qtl_control.qtl_station import QTLStation
from qtl_control.qtl_experiments import QTLQMExperiment, ExperimentResult
from qtl_control.qtl_experiments.database import FileSystemDB

from qtl_control.qtl_experiments import experiments_dict

def start_station(config, db_path, db_name):
    with open(config) as f:
        config = yaml.safe_load(f)
    station = QTLStation(config)
    db = FileSystemDB(db_name, db_path, experiment_dict=experiments_dict)
    ExperimentResult.db = db
    QTLQMExperiment.station = station

    return station
