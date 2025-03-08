import os
import json
import re
import csv
import platform

current_db = None
current_db_file = None

def load_db(db_name):
    """Load the database file into memory."""
    global current_db, current_db_file
    db_path = f"{db_name}.json"
    
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            try:
                current_db = json.load(f)
            except json.JSONDecodeError:
                current_db = {}
    else:
        current_db = {}

    current_db_file = db_path

def save_db():
    """Save the database to the JSON file."""
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
    if not tokens:
        return "Invalid command."

    action = tokens[0].lower()
    
    # CREATE DATABASE
    if action == "create" and len(tokens) == 3 and tokens[1].lower() == "database":
        db_name = tokens[2]
        db_path = f"{db_name}.json"
        
        if os.path.exists(db_path):
            return f"Database '{db_name}' already exists."
        
        with open(db_path, "w") as f:
            json.dump({}, f)
        
        return f"Database '{db_name}' created successfully."
    
    
    elif action == "show" and len(tokens) == 2 and tokens[1].lower() == "tables":
    # Show all table names
        if current_db:
            table_names = list(current_db.keys())
            return f"Tables: {', '.join(table_names)}"
        else:
            return "No tables found."
        
    elif action == "use" and len(tokens) == 2:
        db_name = tokens[1]
        db_path = f"{db_name}.json"

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

    # MAKE TABLE
    elif action == "make":
        if current_db is None:
            return "No database selected. Use 'USE database_name' first."
        
        match = re.match(r"make (\w+)\s*\((.+)\);?", command, re.IGNORECASE)
        if not match:
            return "Syntax error. Use: MAKE table_name (column1 TYPE, column2 TYPE, ...);"

        table_name, columns_part = match.groups()
        columns = [col.strip() for col in columns_part.split(",")]

        column_names = []
        column_types = {}

        for col in columns:
            parts = col.split()
            if len(parts) != 2:
                return f"Invalid column definition: '{col}'. Use 'column_name TYPE'."
            column_name, column_type = parts
            column_names.append(column_name)
            column_types[column_name] = column_type.upper()

        if table_name in current_db:
            return f"Table '{table_name}' already exists."
        
        current_db[table_name] = {"columns": column_names, "types": column_types, "data": []}
        save_db()
        return f"Table '{table_name}' created with columns {column_names}."

    # INCLUDE DATA
    elif action == "include":
        match = re.match(r"include (\w+)\s*\(([^)]+)\);?", command, re.IGNORECASE)
        if not match:
            return "Syntax error. Use: INCLUDE table_name (value1, value2, ...);"

        table_name, values_part = match.groups()

        if table_name not in current_db:
            return f"Table '{table_name}' does not exist."

        table_columns = current_db[table_name]["columns"]
        column_types = current_db[table_name]["types"]

        values = [val.strip() for val in values_part.split(",")]

        if len(values) != len(table_columns):
            return f"Column mismatch. Expected {len(table_columns)} values but got {len(values)}."

        # Convert values based on column types
        converted_values = []
        for i, column in enumerate(table_columns):
            column_type = column_types[column]

            try:
                if column_type == "INT":
                    converted_values.append(int(values[i]))
                elif column_type == "FLOAT":
                    converted_values.append(float(values[i]))
                elif column_type == "TEXT":
                    converted_values.append(values[i].strip("'\""))  # Remove quotes if present
                else:
                    return f"Unsupported data type '{column_type}' for column '{column}'."
            except ValueError:
                return f"Type mismatch for column '{column}'. Expected {column_type}."

        # Insert into table
        current_db[table_name]["data"].append(converted_values)
        save_db()
        
        return f"1 record inserted into '{table_name}'."


    # SELECT DATA
    elif action == "select":
        if len(tokens) >= 2:
            table_name = tokens[1]

            if table_name not in current_db:
                return f"Table '{table_name}' does not exist."

            table_columns = current_db[table_name]["columns"]
            table_data = current_db[table_name]["data"]

            # Check if WHERE condition is used
            if "where" in tokens:
                where_index = tokens.index("where")
                if where_index + 2 >= len(tokens):
                    return "Syntax error. Use: SELECT table_name WHERE column_name = value"
                
                column_name = tokens[where_index + 1]
                condition_value = tokens[where_index + 3]

                if column_name not in table_columns:
                    return f"Column '{column_name}' does not exist in table '{table_name}'."

                column_index = table_columns.index(column_name)
                filtered_data = []

                # Filter rows based on WHERE condition
                for row in table_data:
                    if str(row[column_index]) == condition_value:
                        filtered_data.append(row)

                # Display filtered results
                output = " | ".join(table_columns) + "\n" + "-" * 50 + "\n"
                for row in filtered_data:
                    output += " | ".join(str(item) for item in row) + "\n"

                return output if filtered_data else f"No records found for the condition."

            # If no WHERE condition, select all
            output = " | ".join(table_columns) + "\n" + "-" * 50 + "\n"
            for row in table_data:
                output += " | ".join(str(item) for item in row) + "\n"

            return output if table_data else f"Table '{table_name}' is empty."
        
    elif action == "update":
        if "set" not in tokens or "where" not in tokens:
            return "Syntax error. Usage: UPDATE table_name SET field_name = new_value WHERE condition;"

        table_name = tokens[1]
        set_index = tokens.index("set")
        where_index = tokens.index("where")

        # Extract the SET clause and WHERE clause
        set_clause = " ".join(tokens[set_index + 1:where_index])
        where_clause = " ".join(tokens[where_index + 1:])

        if "=" not in set_clause or "=" not in where_clause:
            return "Syntax error in SET or WHERE clause."

        # Split the SET clause into field_name and new_value
        field_name, new_value = set_clause.split("=")
        field_name = field_name.strip()
        new_value = new_value.strip().strip('"')

        # Split the WHERE clause into condition_field and condition_value
        condition_field, condition_value = where_clause.split("=")
        condition_field = condition_field.strip()
        condition_value = condition_value.strip().strip('"')

        if table_name in current_db:
            table_info = current_db[table_name]
            columns = table_info["columns"]
            data = table_info["data"]

            if field_name not in columns or condition_field not in columns:
                return "Invalid column name."

            field_index = columns.index(field_name)
            condition_index = columns.index(condition_field)

            modified_count = 0

            # Loop through each row and update if condition matches
            for row in data:
                if str(row[condition_index]) == condition_value:
                    # Convert the new value to the correct type
                    if table_info["types"][field_name] == "INT":
                        new_value = int(new_value)
                    elif table_info["types"][field_name] == "FLOAT":
                        new_value = float(new_value)
                    
                    # Update the field value
                    row[field_index] = new_value
                    modified_count += 1

            if modified_count > 0:
                save_db()
                return f"{modified_count} record(s) updated in '{table_name}'."
            else:
                return "No records matched the condition."
        else:
            return f"Table '{table_name}' does not exist."
        
    elif action == "delete":
        try:
            # Check if it's for a field or entire row
            if "from" not in tokens or "where" not in tokens:
                return "Syntax error. Usage: DELETE [field_name] FROM table_name WHERE condition;"

            from_index = tokens.index("from")
            where_index = tokens.index("where")

            # Determine if field_name is specified or not
            if from_index == 1:  # No field_name, e.g., DELETE FROM users WHERE ...
                field_name = None
                table_name = tokens[2]
            else:  # Field_name is specified, e.g., DELETE name FROM users WHERE ...
                field_name = tokens[1]
                table_name = tokens[3]

            condition_clause = " ".join(tokens[where_index + 1:])

            if "=" not in condition_clause:
                return "Syntax error in WHERE clause."

            condition_field, condition_value = condition_clause.split("=")
            condition_field = condition_field.strip()
            condition_value = condition_value.strip().strip('"')

            if table_name in current_db:
                table_columns = current_db[table_name]["columns"]
                table_data = current_db[table_name]["data"]
                modified_count = 0

                # Get the index of the condition field
                if condition_field not in table_columns:
                    return f"Field '{condition_field}' not found in table '{table_name}'."

                condition_index = table_columns.index(condition_field)

                # Get the type of the condition field
                field_type = current_db[table_name]["types"][condition_field]
                if field_type == "INT":
                    condition_value = int(condition_value)

                # Case 1: Delete a specific field in matching rows
                if field_name:
                    # Check if the field name is valid
                    if field_name not in table_columns:
                        return f"Field '{field_name}' not found in table '{table_name}'."

                    field_index = table_columns.index(field_name)

                    # Delete the specific field in rows that match the condition
                    for row in table_data:
                        if row[condition_index] == condition_value:
                            row[field_index] = None  # Set the field to None
                            modified_count += 1

                # Case 2: Delete entire rows matching the condition
                else:
                    initial_len = len(table_data)
                    table_data[:] = [row for row in table_data if row[condition_index] != condition_value]
                    modified_count = initial_len - len(table_data)

                save_db()
                return f"Deleted {modified_count} record(s) from '{table_name}'."
            else:
                return f"Table '{table_name}' not found."

        except Exception as e:
            return f"Error processing delete command: {e}"
    
    elif action == "show" and len(tokens) == 2 and tokens[1].lower() == "databases":
        databases = []
        for f in os.listdir():
            if f.endswith(".json") and f != "storage.json":
                db_name = f.split(".json")[0]
                
                # Check the database type
                with open(f, "r") as file:
                    try:
                        db_content = json.load(file)
                        if f == "storage.json":
                            db_type = "NoSQL"
                        elif isinstance(db_content, dict):
                            if all(
                                isinstance(table, dict) and 
                                "columns" in table and 
                                "types" in table and 
                                "data" in table
                                for table in db_content.values()
                            ):
                                db_type = "SQL"
                            else:
                                db_type = "Unknown"
                        else:
                            db_type = "Unknown"
                        
                        databases.append(f"{db_name} ({db_type})")
                    except json.JSONDecodeError:
                        databases.append(f"{db_name} (Corrupted)")

        return "Databases: " + ", ".join(databases) if databases else "No databases found."
    
    
    elif action == "export":
        try:
            parts = command.split()
            if len(parts) != 6 or parts[2].lower() != "as" or parts[4].lower() != "in":
                return "❌ Invalid export command format. Use: EXPORT database_name AS file_name IN [CSV/JSON]"

            db_name, file_name, file_format = parts[1], parts[3], parts[5].upper()

            if file_format not in ["CSV", "JSON"]:
                return "❌ Error: Unsupported file format. Use CSV or JSON."

            downloads_folder = get_downloads_directory()
            file_path = os.path.join(downloads_folder, f"{file_name}.{file_format.lower()}")

            if file_format == "JSON":  
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(current_db, f, indent=4)
                return f"✅ Database '{db_name}' successfully exported as JSON! File saved at: {file_path}"

            elif file_format == "CSV":
                if not isinstance(current_db, dict) or not current_db:
                    return "❌ Error: Database is empty or has an invalid structure for CSV export."

                with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)

                    for table_name, table_info in current_db.items():
                        if not isinstance(table_info, dict) or "columns" not in table_info or "data" not in table_info:
                            continue  # Skip invalid tables

                        writer.writerow([f"Table: {table_name}"])  # Table name
                        writer.writerow(table_info["columns"])  # Column headers

                        for record in table_info["data"]:
                            writer.writerow(record)  # Write row data

                        writer.writerow([])  # Blank line for separation

                return f"✅ Database '{db_name}' successfully exported as CSV! File saved at: {file_path}"

        except Exception as e:
            return f"❌ Error exporting database: {e}"


if __name__ == "__main__":
    print("Welcome to the simple database. Type 'exit' to quit.")
    
    while True:
        command = input("db>").strip()
        if command.lower() == "exit":
            break
        print(process_command(command))
