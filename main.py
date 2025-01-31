from fastapi import FastAPI
from pydantic import BaseModel
from db import FlatDB

app = FastAPI()
db = FlatDB()

# Pydantic model for data validation
class Record(BaseModel):
    name: str
    age: int

@app.post("/insert/{table}")
def insert_record(table: str, record: Record):
    db.insert(table, record.dict())
    return {"message": f"Record inserted into {table}"}

@app.get("/select/{table}")
def get_records(table: str):
    records = db.get_all(table)
    return {"records": records}

@app.put("/update/{table}/{index}")
def update_record(table: str, index: int, record: Record):
    db.update(table, index, record.dict())
    return {"message": f"Record in {table} updated at index {index}"}

@app.delete("/delete/{table}/{index}")
def delete_record(table: str, index: int):
    db.delete(table, index)
    return {"message": f"Record deleted from {table} at index {index}"}
