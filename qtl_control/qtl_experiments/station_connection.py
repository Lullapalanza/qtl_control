"""
Make a station connection that connects to a database, keeps track of experiments and handles database connection
"""
import yaml

from qtl_control.qtl_station import QTLStation
from qtl_control.qtl_experiments import experiments_dict
from qtl_control.qtl_experiments.database import FileSystemDB, RelationalDB


class StationConnection:
    def __init__(self, station_config_path, db_path, db_name, db_type="filesystem"):
        assert db_type in ["filesystem", "relational"]

        with open(station_config_path) as f:
            self.station = QTLStation(yaml.safe_load(f))
        self.config = self.station.config

        if db_type == "filesystem":
            self.db = FileSystemDB(db_name, db_path, experiment_dict=experiments_dict)
        elif db_type == "relational":
            self.db = RelationalDB(db_name, db_path, experiment_dict=experiments_dict)

    def print_tree(self):
        self.station.print_tree()

    def load_full_config(self, elements, config_name):
        """
        Load full config with a new config either from database or make a new config
        """
        current_config = {k: v.get_as_dict() for k, v in self.config.items()}
        self.current_config_id, new_settings = self.db.load_config_by_name(config_name, initial_settings_for_new_config=current_config)
        self.station.reload_config(elements, new_settings)

    def change_config(self, elements, new_settings=None):
        self.station.reload_config(elements, new_settings)
        self.config_change_key = self.db.change_config(self.current_config_id, new_settings)
        return self.config_change_key
    
    def save_config(self, new_config_name):
        current_config = {k: v.get_as_dict() for k, v in self.config.items()}
        self.current_config_id = self.db.save_config(new_config_name, current_config)

    def load_to_checkpoint(self, elements, checkpoint_key):
        new_settings = self.db.load_changes_for_config_up_to(self.current_config_id, checkpoint_key)
        self.station.reload_config(elements, new_settings)

    def change_settings(self):
        return self.station.change_settings()

    def load_result(self, result_id):
        return self.db.load_result(result_id)