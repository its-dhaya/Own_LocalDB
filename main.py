import sql
import nosql

def main():
    print("Choose your database format:")
    print("1. SQL")
    print("2. NoSQL")
    
    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        print("You selected SQL database.")
        process_command = sql.process_command  # Use SQL processor
    elif choice == "2":
        print("You selected NoSQL database.")
        process_command = nosql.process_command  # Use NoSQL processor
    else:
        print("Invalid choice. Exiting.")
        return

    print("Type 'exit' to quit.")
    while True:
        command = input("db> ").strip()
        if command.lower() == "exit":
            break
        print(process_command(command))

if __name__ == "__main__":
    main()
