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

    def save_data(self, experiment_name, data, extra_axes):
        self.current_id += 1
        filename = f"{self.current_id}_{experiment_name}_{datetime.today().strftime(r'%Y_%m_%d')}.json"
        with open(self.db_path + "/id.txt", "w+") as f:
            f.write(str(self.current_id))
        
        with open(f"{self.db_path}/{filename}", "w") as f:
            f.write(json.dumps({
                "data": data,
                "extra_axes": extra_axes
            }, cls=ComplexJsonEncoder, indent=4))

        return self.current_id
