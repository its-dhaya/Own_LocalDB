import json
import os

DB_FILE = "storage.json"

class FlatDB:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, "w") as f:
                json.dump({}, f)

    def read_data(self):
        with open(DB_FILE, "r") as f:
            return json.load(f)

    def write_data(self, data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def insert(self, table: str, record: dict):
        data = self.read_data()
        if table not in data:
            data[table] = []
        data[table].append(record)
        self.write_data(data)

    def get_all(self, table: str):
        data = self.read_data()
        return data.get(table, [])

    def update(self, table: str, index: int, new_data: dict):
        data = self.read_data()
        if table in data and 0 <= index < len(data[table]):
            data[table][index] = new_data
            self.write_data(data)

    def delete(self, table: str, index: int):
        data = self.read_data()
        if table in data and 0 <= index < len(data[table]):
            data[table].pop(index)
            self.write_data(data)
