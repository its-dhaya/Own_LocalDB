import os
import json

DB_FILE = "storage.json"

# Load existing database or create an empty one
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        try:
            database = json.load(f)
        except json.JSONDecodeError:
            database = {}
else:
    database = {}

# Initialize auto-increment ID tracking
_id_counter = {}

# Ensure existing tables have proper ID tracking
for table_name, records in database.items():
    if records:
        max_id = max(record.get("id", 0) for record in records)
    else:
        max_id = 0
    _id_counter[table_name] = max_id

def save_db():
    """Save the database to a JSON file."""
    with open(DB_FILE, "w") as f:
        json.dump(database, f, indent=4)

def process_command(command):
    tokens = command.strip().split()

    # Remove the semicolon if present at the end of the command
    if tokens[-1].endswith(";"):
        tokens[-1] = tokens[-1][:-1]

    if not tokens:
        return "Invalid command."

    action = tokens[0].lower()

    if action == "create":
        if len(tokens) < 2:
            return "Syntax error. Usage: CREATE table_name;"
        table_name = tokens[1]
        if table_name in database:
            return f"Table '{table_name}' already exists."
        database[table_name] = []
        _id_counter[table_name] = 0  # Initialize ID counter
        save_db()
        return f"Table '{table_name}' created successfully."

    elif action == "insert":
        if len(tokens) < 3:
            return "Syntax error. Usage: INSERT table_name {data};"
        table_name = tokens[1]
        data = command.split("{", 1)[-1].split("}", 1)[0]
        try:
            if not data:
                return "Empty data provided."
            data = data.strip()
            record = json.loads(f"{{{data}}}")

            if table_name in database:
                # Auto-increment ID
                _id_counter[table_name] += 1
                record["id"] = _id_counter[table_name]

                database[table_name].append(record)
                save_db()
                return f"Record inserted into '{table_name}' with ID {record['id']}."
            else:
                return f"Table '{table_name}' does not exist."
        except json.JSONDecodeError as e:
            return f"Invalid JSON format: {e}"

    elif action == "select":
        if len(tokens) < 2:
            return "Syntax error. Usage: SELECT table_name [field_name] WHERE condition;"

        table_name = tokens[1]
        fields = []
        condition_clause = None

        if "where" in tokens:
            where_index = tokens.index("where")
            condition_clause = " ".join(tokens[where_index + 1:])
            
            if "=" in condition_clause:
                condition_field, condition_value = condition_clause.split("=")
                condition_field = condition_field.strip()
                condition_value = condition_value.strip().strip("'")
            fields = tokens[2:where_index] if len(tokens) > 2 and tokens[2] != "where" else[]
        else:
            fields = tokens[2:] if len(tokens) > 2 else []
        fields = [field.strip(",") for field in fields]

        if table_name in database:
            if not fields:
                return json.dumps(database[table_name], indent=4)

            condition_field, condition_value = None, None
            if condition_clause:
                if "=" in condition_clause:
                    condition_field, condition_value = condition_clause.split("=")
                    condition_field = condition_field.strip()
                    condition_value = condition_value.strip().strip("'")

            result = []
            for record in database[table_name]:
                match = True
                if condition_field:
                    record_value = record.get(condition_field)
                    if record_value is not None:
                        if isinstance(record_value, int):
                            condition_value = int(condition_value)
                        elif isinstance(record_value,float):
                            condition_value = float(condition_value)
                        if record_value != condition_value:
                            match = False
                if match:
                    result_record = {field.strip(): record.get(field.strip()) for field in fields} if fields else record
                    result.append(result_record)

            return json.dumps(result, indent=4) if result else "No records matched the condition."
        else:
            return f"Table '{table_name}' does not exist."

    elif action == "update":
        if "set" not in tokens or "where" not in tokens:
            return "Syntax error. Usage: UPDATE table_name SET field_name = new_value WHERE condition;"

        table_name = tokens[1]
        set_index = tokens.index("set")
        where_index = tokens.index("where")

        set_clause = " ".join(tokens[set_index + 1:where_index])
        where_clause = " ".join(tokens[where_index + 1:])

        if "=" not in set_clause or "=" not in where_clause:
            return "Syntax error in SET or WHERE clause."

        field_name, new_value = set_clause.split("=")
        condition_field, condition_value = where_clause.split("=")

        field_name = field_name.strip()
        new_value = new_value.strip().strip("'")
        condition_field = condition_field.strip()
        condition_value = condition_value.strip().strip("'")

        if table_name in database:
            updated = False
            for record in database[table_name]:
                if str(record.get(condition_field)) == condition_value:
                    if isinstance(record.get(field_name), int):
                        new_value = int(new_value)
                    elif isinstance(record.get(field_name), float):
                        new_value = float(new_value)

                    record[field_name] = new_value
                    updated = True
            if updated:
                save_db()
                return f"Record(s) updated in '{table_name}'."
            else:
                return "No records matched the condition."
        else:
            return f"Table '{table_name}' does not exist."

    elif action == "delete":
        if "from" not in tokens or "where" not in tokens:
            return "Syntax error. Usage: DELETE FROM table_name WHERE condition;"

        table_name = tokens[2]
        where_index = tokens.index("where")
        condition_clause = " ".join(tokens[where_index + 1:])

        if "=" not in condition_clause:
            return "Syntax error in WHERE clause."

        condition_field, condition_value = condition_clause.split("=")
        condition_field = condition_field.strip()
        condition_value = condition_value.strip().strip("'")

        if table_name in database:
            original_count = len(database[table_name])
            database[table_name] = [record for record in database[table_name] if str(record.get(condition_field)) != condition_value]

            if len(database[table_name]) < original_count:
                save_db()
                return f"Record(s) deleted from '{table_name}'."
            else:
                return "No records matched the condition."
        else:
            return f"Table '{table_name}' does not exist."

    else:
        return "Unknown command. Try 'create', 'insert', 'select', 'update', or 'delete'."

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