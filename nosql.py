import os
import json
import shutil
import re
import tkinter as tk
from tkinter import filedialog
import csv

current_db = None
current_db_file = None
_id_counter = {}

def load_db(db_name):
    global current_db, current_db_file
    db_path = f"{db_name}.json"  # No folder, just file
    
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            try:
                current_db = json.load(f)
            except json.JSONDecodeError:
                current_db = {}
    else:
        current_db = {}

    current_db_file = db_path
    update_id_counter() # Update the ID counter after loading the DB


def update_id_counter():
    """Update the _id_counter for each table in the current database."""
    global _id_counter
    
    if current_db is not None:
        for table_name, records in current_db.items():
            _id_counter[table_name] = max((record.get("id", 0) for record in records), default=0)

def save_db():
    """Save the database to the current database's JSON file."""
    if current_db_file:
        with open(current_db_file, "w") as f:
            json.dump(current_db, f, indent=4)
            
import os
import platform

def get_downloads_directory():
    if platform.system() == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    else:
        return os.path.join(os.path.expanduser("~"), "Downloads")


def process_command(command):
    global current_db, current_db_file
    
    tokens = command.strip().split()

    # Remove the semicolon if present at the end of the command
    if tokens[-1].endswith(";"):
        tokens[-1] = tokens[-1][:-1]

    if not tokens:
        return "Invalid command."

    action = tokens[0].lower()
    
    if action == "show" and len(tokens) == 2 and tokens[1].lower() == "databases":
        # List all JSON database files in the current directory
        databases = [f for f in os.listdir() if f.endswith(".json")]
        return "Databases: " + ", ".join(databases) if databases else "No databases found."
    
    elif action == "create" and len(tokens) == 3 and tokens[1].lower() == "database":
        db_name = tokens[2]
        db_path = f"{db_name}.json"
        
        if os.path.exists(db_path):
            return f"Database '{db_name}' already exists."
        
        # Create an empty JSON file
        with open(db_path, "w") as f:
            json.dump({}, f)
        
        return f"Database '{db_name}' created successfully."
        
    elif action == "exit" and len(tokens) == 2:
        db_name = tokens[1]

        if current_db is None:
            return "No database is currently in use."

        db_path = f"{db_name}.json"  # Direct JSON file name
        if not os.path.exists(db_path):
            return f"Database '{db_name}' does not exist."

        if current_db_file == db_path:
            save_db()  # Save changes before exiting
            current_db_file = None
            current_db = None
            return f"Exited from database '{db_name}'. You can now use another database."
        else:
            return f"Database '{db_name}' is not currently in use."
        
    elif action == "use" and len(tokens) == 2:
        db_name = tokens[1]
        db_path = f"{db_name}.json"  # Direct JSON file name

        if not os.path.exists(db_path):
            return f"Database '{db_name}' does not exist."
        else:
            load_db(db_name)
            return f"Using database '{db_name}'."

    elif action == "remove" and len(tokens) == 2:
        db_name = tokens[1]
        db_path = f"{db_name}.json"  # Direct JSON file name

        if not os.path.exists(db_path):
            return f"Database '{db_name}' does not exist."

        os.remove(db_path)  # Delete the JSON file
        if current_db_file == db_path:
            current_db_file = None
            current_db = None

        return f"Database '{db_name}' deleted successfully."



    elif action == "make" and len(tokens) >= 2:
        if current_db is None:
            return "No database selected. Use 'USE database_name' to select a database."

        table_name = tokens[1]
        if table_name in current_db:
            return f"Table '{table_name}' already exists."
        current_db[table_name] = []
        _id_counter[table_name] = 0  # Initialize ID counter for the table
        save_db()
        return f"Table '{table_name}' created successfully."



    elif action == "include":
        if len(tokens) < 3:
            return "Syntax error. Usage: INCLUDE table_name [{key: value, ...}, {key: value, ...}];"
        
        table_name = tokens[1]
        data_block = command.split("[", 1)[-1].split("]", 1)[0]  # Extract data inside [ ... ]

        try:
            if not data_block.strip():
                return "Empty data provided."

            # Convert unquoted keys and values to valid JSON format
            def fix_json_format(data):
                # Add quotes around keys and string values
                data = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', data)  # Keys
                data = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([},])', r':"\1"\2', data)  # String values
                return data

            fixed_data = fix_json_format(data_block)
            raw_records = f"[{fixed_data}]"
            parsed_records = []

            # Parse and check for duplicate keys in each individual object
            for obj in json.loads(raw_records, object_pairs_hook=lambda pairs: pairs):
                seen_keys = set()
                obj_dict = {}
                for key, value in obj:
                    if key in seen_keys:
                        return f"Error: Duplicate key '{key}' found within a JSON object."
                    seen_keys.add(key)
                    obj_dict[key] = value
                parsed_records.append(obj_dict)

            if not isinstance(parsed_records, list):
                return "Invalid format. Expected an array of JSON objects."

            if table_name in current_db:
                inserted_ids = []

                for record in parsed_records:
                    if isinstance(record, dict):  
                        # Auto-increment ID
                        _id_counter[table_name] += 1
                        record["id"] = _id_counter[table_name]

                        current_db[table_name].append(record)
                        inserted_ids.append(record["id"])
                    else:
                        return "Invalid data format. Each entry should be a JSON object."

                save_db()
                return f"{len(inserted_ids)} records included into '{table_name}' with IDs {inserted_ids}."
            else:
                return f"Table '{table_name}' does not exist."
        except json.JSONDecodeError as e:
            return f"Invalid JSON format: {e}"


    elif action == "select":
        if len(tokens) < 2:
            return "Syntax error. Usage: SELECT table_name [field_name] WHERE condition [ORDER BY field_name ASC/DESC] [GROUP BY field_name];"

        table_name = tokens[1]
        fields = []
        condition_clause = None
        order_field = None
        order_direction = "asc"
        group_field = None
        where_index = len(tokens)
        
        # Check for WHERE condition
        if "where" in tokens:
            where_index = tokens.index("where")
            condition_clause = " ".join(tokens[where_index + 1:])
            fields = tokens[2:where_index] if len(tokens) > 2 and tokens[2] != "where" else []
        else:
            fields = tokens[2:] if len(tokens) > 2 else []

        # Handle ORDER BY clause
        if "order" in tokens and "by" in tokens:
            order_index = tokens.index("order")
            order_field = tokens[order_index + 2]
            if len(tokens) > order_index + 3 and tokens[order_index + 3].lower() in ["asc", "desc"]:
                order_direction = tokens[order_index + 3].lower()

        # Handle GROUP BY clause
        if "group" in tokens and "by" in tokens:
            group_index = tokens.index("group")
            group_field = tokens[group_index + 2]

        fields = [field.strip() for field in " ".join(fields).split(",") if field.strip()]

        if table_name in current_db:
            result = current_db[table_name]

            # Apply WHERE condition if exists
            if condition_clause:
                condition_field, condition_value = condition_clause.split("=")
                condition_field = condition_field.strip()
                condition_value = condition_value.strip().strip("'")
                result = [record for record in result if record.get(condition_field) == condition_value]

            # Apply GROUP BY if exists
            if group_field:
                grouped = {}
                for record in result:
                    group_key = record.get(group_field)
                    if group_key is not None:
                        if group_key not in grouped:
                            grouped[group_key] = []
                        grouped[group_key].append(record)
                result = [{"group": group_key, "records": records} for group_key, records in grouped.items()]

            # Apply ORDER BY if exists
            if order_field:
                result = sorted(result, key=lambda x: x.get(order_field, ""), reverse=(order_direction == "desc"))

            if fields:
                result = [{field: record.get(field) for field in fields} for record in result]

            return json.dumps(result, indent=4) if result else "No records matched the condition."
        else:
            return f"Table '{table_name}' does not exist."
    

    elif action == "update":
        try:
            if "set" not in tokens or "where" not in tokens:
                return "Syntax error. Usage: UPDATE table_name SET field=value WHERE condition;"

            table_name = tokens[1]
            set_index = tokens.index("set")
            where_index = tokens.index("where")

            set_clause = " ".join(tokens[set_index + 1:where_index])
            condition_clause = " ".join(tokens[where_index + 1:])

            if "=" not in set_clause or "=" not in condition_clause:
                return "Syntax error in SET or WHERE clause."

            set_field, set_value = set_clause.split("=")
            set_field = set_field.strip()
            set_value = set_value.strip().strip("'")

            condition_field, condition_value = condition_clause.split("=")
            condition_field = condition_field.strip()
            condition_value = condition_value.strip().strip("'")

            if table_name in current_db:
                modified_count = 0

                # Detect column type from existing data
                detected_type = None
                for record in current_db[table_name]:
                    if condition_field in record and record[condition_field] is not None:
                        if isinstance(record[condition_field], int):
                            detected_type = int
                        elif isinstance(record[condition_field], float):
                            detected_type = float
                        break

                # Convert condition value if type is detected
                if detected_type:
                    try:
                        condition_value = detected_type(condition_value)
                    except ValueError:
                        return "Type mismatch in WHERE condition."

                # Detect set value type from existing data
                detected_type = None
                for record in current_db[table_name]:
                    if set_field in record and record[set_field] is not None:
                        if isinstance(record[set_field], int):
                            detected_type = int
                        elif isinstance(record[set_field], float):
                            detected_type = float
                        break

                # Convert set value if type is detected
                if detected_type:
                    try:
                        set_value = detected_type(set_value)
                    except ValueError:
                        return "Type mismatch in SET clause."

                # Apply update
                for record in current_db[table_name]:
                    if record.get(condition_field) == condition_value:
                        record[set_field] = set_value
                        modified_count += 1

                return f"{modified_count} record(s) updated in '{table_name}'."
            else:
                return f"Table '{table_name}' not found."

        except Exception as e:
            return f"Error processing update command: {e}"




    elif action == "exclude":
            if len(tokens) < 2:
                return "Syntax error. Usage: EXCLUDE table_name; OR EXCLUDE FROM table_name WHERE condition;"

            # Case 1: Exclude the entire table (Delete table itself)
            if len(tokens) == 2:
                table_name = tokens[1]

                # Ensure table exists
                if table_name not in current_db:
                    return f"Table '{table_name}' does not exist."

                # Delete the entire table
                del current_db[table_name]
                save_db()
                return f"Table '{table_name}' has been excluded."

            # Case 2: Exclude records from a table (Must include 'FROM')
            if tokens[1].lower() == "from":
                if len(tokens) < 3:
                    return "Syntax error. Usage: EXCLUDE FROM table_name; OR EXCLUDE FROM table_name WHERE condition;"

                table_name = tokens[2]

                # Ensure table exists
                if table_name not in current_db:
                    return f"Table '{table_name}' does not exist."

                # Case 2a: Exclude all records from the table (No WHERE Clause)
                if len(tokens) == 3:
                    current_db[table_name] = []  # Clear all records but keep the table
                    save_db()
                    return f"All records excluded from '{table_name}'."

                # Case 2b: Exclude specific records using WHERE condition
                if len(tokens) > 3 and tokens[3].lower() == "where":
                    if len(tokens) < 6 or "=" not in " ".join(tokens[4:]):
                        return "Syntax error in WHERE clause. Expected format: EXCLUDE FROM table_name WHERE field = value;"

                    # Extract condition clause
                    condition_clause = " ".join(tokens[4:])
                    condition_field, condition_value = condition_clause.split("=")
                    condition_field = condition_field.strip()
                    condition_value = condition_value.strip().strip("'")

                    # Convert condition value type if necessary
                    for record in current_db[table_name]:
                        if condition_field in record:
                            if isinstance(record[condition_field], int):
                                condition_value = int(condition_value)
                            elif isinstance(record[condition_field], float):
                                condition_value = float(condition_value)
                            break  # Stop checking after the first record

                    # Remove matching records
                    original_count = len(current_db[table_name])
                    current_db[table_name] = [record for record in current_db[table_name] if record.get(condition_field) != condition_value]

                    # Save and return response
                    if len(current_db[table_name]) < original_count:
                        save_db()
                        return f"Excluded {original_count - len(current_db[table_name])} record(s) from '{table_name}'."
                    else:
                        return "No matching records found."

            return "Syntax error. Use: EXCLUDE table_name; OR EXCLUDE FROM table_name WHERE condition;"


    elif action == "delete":
        try:
            if len(tokens) < 4 or tokens[2] != "from" or "where" not in tokens:
                return "Syntax error. Usage: DELETE [field_name] FROM table_name WHERE condition;"

            table_name = tokens[3]
            where_index = tokens.index("where")
            condition_clause = " ".join(tokens[where_index + 1:])

            if "=" not in condition_clause:
                return "Syntax error in WHERE clause."

            condition_field, condition_value = condition_clause.split("=")
            condition_field = condition_field.strip()
            condition_value = condition_value.strip().strip("'")

            if table_name in current_db:
                modified_count = 0

                # Type conversion for numerical fields
                for record in current_db[table_name]:
                    if condition_field in record:
                        if isinstance(record[condition_field], int):
                            condition_value = int(condition_value)
                        elif isinstance(record[condition_field], float):
                            condition_value = float(condition_value)
                        break

                if len(tokens) > 4:
                    field_name = tokens[1]

                    for record in current_db[table_name]:
                        if record.get(condition_field) == condition_value:
                            if field_name in record:
                                record[field_name] = None  # Instead of deleting, set it to None
                                modified_count += 1
                            else:
                                return f"Field '{field_name}' not found in the record."
                else:
                    current_db[table_name] = [
                        r if r.get(condition_field) != condition_value else {**r, "deleted": True}
                        for r in current_db[table_name]
                    ]
                    modified_count += 1

                return f"Deleted {modified_count} record(s)."
            else:
                return f"Table '{table_name}' not found."

        except Exception as e:
            return f"Error processing delete command: {e}"



 # Stop after removing the first matching record
                    
    elif action == "count":
        if len(tokens) < 2:
            return "Syntax error. Usage: COUNT table_name;"

        table_name = tokens[1]

        if table_name in current_db:
            record_count = len(current_db[table_name])
            return f"Table '{table_name}' contains {record_count} record(s)."
        else:
            return f"Table '{table_name}' does not exist."
        
    elif action == "show" and len(tokens) == 2 and tokens[1].lower() == "tables":
    # Show all table names
        if current_db:
            table_names = list(current_db.keys())
            return f"Tables: {', '.join(table_names)}"
        else:
            return "No tables found."
            







def cli():
    print("SimpleDB CLI. Type 'exit' to quit.")
    while True:
        command = input("db> ")
        if command.lower() == "exit":
            break
        response = process_command(command)
        print(response)

if __name__ == "__main__":
    cli()
    