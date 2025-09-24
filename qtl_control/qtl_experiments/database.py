import os
import fnmatch
import xarray as xr

import sqlite3
import json

from pathlib import Path
from datetime import datetime

from qtl_control.qtl_experiments.experiment import ExperimentResult
from qtl_control.qtl_experiments import experiments_dict as default_experiments


class ExperimentDatabase:
    """
    """
    def save_data(self, experiment_name, data) -> int:
        pass

    def load_result(self, id) -> ExperimentResult:
        pass


class FileSystemDB(ExperimentDatabase):
    """
    Make a database as a filesystem to store measurement data in
    """
    def __init__(self, db_name, path, experiment_dict=None):
        self.db_path = path + db_name
        self.current_id = -1
        self.experiment_dict = experiment_dict or default_experiments

        if os.path.exists(self.db_path):
            with open(self.db_path + "/id.txt", "r") as f:
                self.current_id = int(f.readline().strip("\n"))
            print(f"Opened DB with last id: {self.current_id}")

        else:
            os.makedirs(self.db_path)
            with open(self.db_path + "/id.txt", "w+") as f:
                f.write(str(self.current_id))
            print(f"Created new DB")

    def save_dataset(self, experiment_name, data) -> int:
        # Save xarray dataset as '.nc'
        
        self.current_id += 1
        save_as_id = self.current_id

        filename = f"{save_as_id}_{experiment_name}_{datetime.today().strftime(r'%Y-%m-%d-%H-%M-%S')}.nc"
        
        with open(self.db_path + "/id.txt", "w+") as f:
            f.write(str(self.current_id))
        
        data.to_netcdf(f"{self.db_path}/{filename}", auto_complex=True)

        return save_as_id

    def load_result(self, id) -> ExperimentResult:
        _id = None
        for file in os.listdir(f"{self.db_path}/"):
            if fnmatch.fnmatch(file, f"{id}_*"):
                print(f"Found {file}")
                _id, experiment_name, timestamp = file.split("_")
                break
        
        if _id is None:
            print("No file found")
            return
        
        experiment = self.experiment_dict.get(experiment_name)
        if experiment is None:
            print(f"{experiment_name} not registered")
            return
        
        return experiment().load(
            id=_id,
            data=xr.open_dataset(f"{self.db_path}/{file}", auto_complex=True),
        )
    
    def load_config_by_name(self, config_name, initial_settings_for_new_config):
        print("FileSystemDB has no config saves")
        return 0, {}

    def change_config(self, base_config_id, new_settings) -> int:
        print("FileSystemDB has no config saves")
        return 0

class RelationalDB(ExperimentDatabase):
    def __init__(self, db_name, path, experiment_dict=None):
        self.db_path = path + db_name
        self.sqlite_path = self.db_path + "/db.sqlite3"
        self.experiment_dict = experiment_dict or default_experiments

        # Make directory
        if os.path.exists(self.db_path):
            pass
        else:
            os.makedirs(self.db_path)

        # Make db file
        if not Path(self.sqlite_path).is_file():
            with sqlite3.connect(self.sqlite_path) as conn:
            ### Create default schema

                # station_configs is a table of full trees which can be modified
                conn.execute("""
                    CREATE TABLE station_configs (
                        PK INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        config_json BLOB NOT NULL
                    )
                """)

                conn.execute("""
                    CREATE TABLE station_config_changes (
                        PK INTEGER PRIMARY KEY,
                        key_value_json BLOB NOT NULL,
                        base_station_config INTEGER NOT NULL,
                        FOREIGN KEY(base_station_config) REFERENCES station_configs(PK)
                    )
                """)

                conn.execute("""
                    CREATE TABLE experiment_results (
                        PK INTEGER PRIMARY KEY,
                        id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        dataset_path TEXT NOT NULL,
                        config INTEGER,
                        FOREIGN KEY(config) REFERENCES station_config_changes(PK)
                    )
                """)

                self.current_id = -1
        
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                res = cur.execute("SELECT id FROM experiment_results ORDER BY id desc LIMIT 1")
                if (existing_id := res.fetchone()) is None:
                    self.current_id = -1
                else:
                    self.current_id = existing_id[0]


    def save_dataset(self, experiment_name, data) -> int:
        # Save xarray dataset as '.nc' and useful data
        
        self.current_id += 1
        save_as_id = self.current_id

        filename = f"{save_as_id}_{experiment_name}_{datetime.today().strftime(r'%Y-%m-%d-%H-%M-%S')}.nc"
        data.to_netcdf(f"{self.db_path}/{filename}", auto_complex=True)
        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO experiment_results (id, name, dataset_path) VALUES (?, ?, ?)",
                [self.current_id, experiment_name, f"{self.db_path}/{filename}"]
            )

        return save_as_id


    def load_result(self, id) -> ExperimentResult:
        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.cursor()
            result = cur.execute("SELECT dataset_path, name FROM experiment_results WHERE id = ? LIMIT 1", [id, ])
            path, experiment_name = result.fetchone()    
    
        experiment = self.experiment_dict.get(experiment_name)
        if experiment is None:
            print(f"{experiment_name} not registered")
            return
        
        return experiment().load(
            id=id,
            data=xr.open_dataset(path, auto_complex=True),
        )
    

    def load_config_by_name(self, config_name, initial_settings_for_new_config=None):
        initial_settings_for_new_config = initial_settings_for_new_config or {}

        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.cursor()
            result = cur.execute("SELECT PK, config_json FROM station_configs WHERE name = ? LIMIT 1", [config_name, ])
            existing_id_tree = result.fetchone()
            
        if (config_tree := existing_id_tree) is None:
            # No config exists
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                res = cur.execute(
                    "INSERT INTO station_configs (name, config_json) VALUES (?, ?) RETURNING PK",
                    [config_name, json.dumps(initial_settings_for_new_config)]
                )
                _id = res.fetchone()[0]
            return _id, initial_settings_for_new_config
        else:
            return config_tree[0], json.loads(config_tree[1])
            
    def change_config(self, base_config_id, new_settings) -> int:
        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.cursor()
            res = cur.execute(
                "INSERT INTO station_config_changes (key_value_json, base_station_config) VALUES (?, ?) RETURNING PK",
                [json.dumps(new_settings), base_config_id]
            )
            _id = res.fetchone()[0]

        return _id
    
    def save_config(self, new_config_name, config):
        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.cursor()
            result = cur.execute(
                "INSERT INTO station_configs (name, config_json) values (?, ?) RETURNING PK",
                [new_config_name, json.dumps(config)]
            )
            _id = result.fetchone()[0]
        return _id
    
    def load_changes_for_config_up_to(self, config_id, checkpoint_key):
        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.cursor()
            result = cur.execute(
                "SELECT key_value_json FROM station_config_changes WHERE base_station_config = ? AND PK < ?",
                [config_id, checkpoint_key]
            )
            all_changes = result.fetchall()
        
        new_settings = {}
        for change in all_changes:
            new_settings = new_settings | json.loads(change[0])
        return new_settings