import os
import json

from datetime import datetime
from json import JSONEncoder

class ComplexJsonEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, complex):
            return (o.real, o.imag)
        
        return super().default(o)

class FileSystemDB:
    """
    Make a database as a filesystem to store measurement data in
    """
    def __init__(self, db_name, path):
        self.db_path = path + db_name
        self.current_id = -1

        if os.path.exists(self.db_path):
            with open(self.db_path + "/id.txt", "r") as f:
                self.current_id = int(f.readline().strip("\n"))
            print(f"Opened DB with last id: {self.current_id}")

        else:
            os.makedirs(self.db_path)
            with open(self.db_path + "/id.txt", "w+") as f:
                f.write(str(self.current_id))
            print(f"Created new DB")

    def save_data(self, experiment_name, data, overwrite_id=None):
        # Save xarray dataset as '.nc'
        if overwrite_id is None:
            self.current_id += 1
            save_as_id = self.current_id
        else:
            save_as_id = overwrite_id

        filename = f"{save_as_id}_{experiment_name}_{datetime.today().strftime(r'%Y_%m_%d')}.nc"
        
        with open(self.db_path + "/id.txt", "w+") as f:
            f.write(str(self.current_id))
        
        data.to_netcdf(f"{self.db_path}/{filename}", auto_complex=True)

        return save_as_id
