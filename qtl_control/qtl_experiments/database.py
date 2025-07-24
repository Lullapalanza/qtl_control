import os
import fnmatch
import xarray as xr

from datetime import datetime

from qtl_control.qtl_experiments.experiment import ExperimentResult

class FileSystemDB:
    """
    Make a database as a filesystem to store measurement data in
    """
    def __init__(self, db_name, path, experiment_dict=None):
        self.db_path = path + db_name
        self.current_id = -1
        self.experiment_dict = experiment_dict

        if os.path.exists(self.db_path):
            with open(self.db_path + "/id.txt", "r") as f:
                self.current_id = int(f.readline().strip("\n"))
            print(f"Opened DB with last id: {self.current_id}")

        else:
            os.makedirs(self.db_path)
            with open(self.db_path + "/id.txt", "w+") as f:
                f.write(str(self.current_id))
            print(f"Created new DB")

    def save_data(self, experiment_name, data, overwrite_id=None) -> int:
        # Save xarray dataset as '.nc'
        if overwrite_id is None:
            self.current_id += 1
            save_as_id = self.current_id
        else:
            save_as_id = overwrite_id

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