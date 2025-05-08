import os
import json
import shutil
import re
import tkinter as tk
from tkinter import filedialog
import csv
import shlex
import platform

current_db = None
current_db_file = None
_id_counter = {}

def handle_nosql_query(query):
    # Simple placeholder for actual NoSQL handling logic
    return f"[NoSQL] You entered: {query}"

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
        if len(tokens) < 4 or tokens[2].lower() != "from":
            return "Syntax error. Usage: SELECT ALL|field1,field2 FROM table_name [WHERE field='value'] [ORDER BY field ASC|DESC] [GROUP BY field];"

        fields_token = tokens[1].lower()
        table_name = tokens[3]
        condition_clause = None
        order_field = None
        order_direction = "asc"
        group_field = None

        # Initialize fields
        fields = [] if fields_token == "all" else [f.strip() for f in fields_token.split(",")]

        # Handle WHERE clause
        if "where" in tokens:
            where_index = tokens.index("where")
            condition_clause = " ".join(tokens[where_index + 1:])
            if "order" in tokens:
                condition_clause = " ".join(tokens[where_index + 1:tokens.index("order")])
            elif "group" in tokens:
                condition_clause = " ".join(tokens[where_index + 1:tokens.index("group")])

        # Handle ORDER BY
        if "order" in tokens and "by" in tokens:
            order_index = tokens.index("order")
            order_field = tokens[order_index + 2]
            if len(tokens) > order_index + 3 and tokens[order_index + 3].lower() in ["asc", "desc"]:
                order_direction = tokens[order_index + 3].lower()

        # Handle GROUP BY
        if "group" in tokens and "by" in tokens:
            group_index = tokens.index("group")
            group_field = tokens[group_index + 2]

        # Perform operations
        if table_name in current_db:
            result = current_db[table_name]

            # WHERE filter
            if condition_clause:
                if "=" in condition_clause:
                    condition_field, condition_value = condition_clause.split("=")
                    condition_field = condition_field.strip()
                    condition_value = condition_value.strip().strip("'\"")
                    result = [r for r in result if r.get(condition_field) == condition_value]
                else:
                    return "Only '=' conditions are supported."

            # GROUP BY
            if group_field:
                grouped = {}
                for record in result:
                    key = record.get(group_field)
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(record)
                result = [{"group": k, "records": v} for k, v in grouped.items()]

            # ORDER BY
            if order_field:
                result = sorted(result, key=lambda x: x.get(order_field, ""), reverse=(order_direction == "desc"))

            # Field filtering
            if fields_token != "all":
                result = [{field: r.get(field) for field in fields} for r in result]

            return json.dumps(result, indent=4) if result else "No records matched."
        else:
            return f"Table '{table_name}' does not exist."



    elif action.lower() == "update":
        try:
            # Use shlex to split the command, preserving quoted values
            tokens = shlex.split(command.replace("=", " = "))
            lowered_tokens = [t.lower() for t in tokens]

            if len(tokens) < 8 or "set" not in lowered_tokens or "where" not in lowered_tokens:
                return "Syntax error. Usage: UPDATE table_name SET field=value WHERE condition;"

            table_name = tokens[1]
            set_index = lowered_tokens.index("set")
            where_index = lowered_tokens.index("where")

            # Validate SET clause
            if tokens[set_index + 2] != "=":
                return "Syntax error in SET clause."
            set_field = tokens[set_index + 1]
            set_value = tokens[set_index + 3].strip("'").strip('"')

            # Validate WHERE clause
            if tokens[where_index + 2] != "=":
                return "Syntax error in WHERE clause."
            condition_field = tokens[where_index + 1]
            condition_value = tokens[where_index + 3].strip("'").strip('"')

            if table_name not in current_db:
                return f"Table '{table_name}' not found."

            modified_count = 0

            # Detect and convert types for WHERE value
            for record in current_db[table_name]:
                if condition_field in record:
                    if isinstance(record[condition_field], int):
                        try:
                            condition_value = int(condition_value)
                        except ValueError:
                            return "Type mismatch in WHERE clause."
                    elif isinstance(record[condition_field], float):
                        try:
                            condition_value = float(condition_value)
                        except ValueError:
                            return "Type mismatch in WHERE clause."
                    break

            # Detect and convert types for SET value
            for record in current_db[table_name]:
                if set_field in record:
                    if isinstance(record[set_field], int):
                        try:
                            set_value = int(set_value)
                        except ValueError:
                            return "Type mismatch in SET clause."
                    elif isinstance(record[set_field], float):
                        try:
                            set_value = float(set_value)
                        except ValueError:
                            return "Type mismatch in SET clause."
                    break

            # Perform the update
            for record in current_db[table_name]:
                if record.get(condition_field) == condition_value:
                    record[set_field] = set_value
                    modified_count += 1

            save_db()  # Save changes to the JSON file
            return f"{modified_count} record(s) updated in '{table_name}'."

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
            if "from" not in tokens or "where" not in tokens:
                return "Syntax error. Usage: DELETE [field] FROM table_name WHERE condition;"

            # Determine if field to delete is specified
            field_to_delete = tokens[1].lower() if len(tokens) > 1 else None
            table_name = tokens[3]
            where_index = tokens.index("where")
            condition_clause = " ".join(tokens[where_index + 1:])

            # Handle condition parsing
            condition_field, condition_value = condition_clause.split("=")
            condition_field = condition_field.strip()
            condition_value = condition_value.strip().strip("'")

            if table_name in current_db:
                deleted_count = 0
                for record in current_db[table_name]:
                    if record.get(condition_field) == condition_value:
                        if field_to_delete:
                            # Set the specified field to null
                            record[field_to_delete] = None
                        else:
                            # If no specific field is provided, delete the record entirely
                            current_db[table_name].remove(record)
                        deleted_count += 1

                # Save the changes to the file
                save_db()

                # Return response based on whether a field was deleted or the record
                return f"{deleted_count} record(s) updated in '{table_name}' with field '{field_to_delete}' set to null." if field_to_delete else f"{deleted_count} record(s) deleted from '{table_name}'."
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
        command = input("xdb> ")
        if command.lower() == "exit":
            break
        response = process_command(command)
        print(response)

if __name__ == "__main__":
    cli()
    