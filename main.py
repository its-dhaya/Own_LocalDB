import requests

AUTH_SERVER = "http://127.0.0.1:8000"

def authenticate():
    """Login or register a user before allowing access to the database."""
    while True:
        print("\n1. Login\n2. Register\n3. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            response = requests.post(f"{AUTH_SERVER}/login", json={"username": username, "password": password})

            if response.status_code == 200:
                token = response.json()["token"]
                print(f"✅ Login successful! Token: {token}")  # Debugging: Print token
                return token  # Return JWT token
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")

        elif choice == "2":
            username = input("Choose a username: ").strip()
            password = input("Choose a password: ").strip()
            response = requests.post(f"{AUTH_SERVER}/register", json={"username": username, "password": password})

            if response.status_code == 201:
                print("✅ Registration successful! You can now log in.")
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")

        elif choice == "3":
            return None

        else:
            print("❌ Invalid option. Try again.")

def test_protected_route(token):
    """Test the protected route with the JWT token."""
    headers = {"Authorization": f"Bearer {token}"}
    print(f"🔍 Sending Token in Headers: {headers}")  # Debugging: Print the token being sent

    response = requests.get(f"{AUTH_SERVER}/protected", headers=headers)

    try:
        if response.status_code == 200:
            print("🔒 Protected Route Access:", response.json()["message"])
            return True
        else:
            print(f"❌ Failed to access protected route: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error parsing response: {e}, Raw response: {response.text}")
        return False

def main():
    token = authenticate()
    if not token:
        print("❌ Authentication required. Exiting.")
        return

    # Test if the token works for protected routes
    if not test_protected_route(token):
        print("❌ Token is invalid or expired. Please login again.")
        return

    print("\nChoose your database format:")
    print("1. SQL")
    print("2. NoSQL")
    
    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        print("You selected SQL database.")
        import sql
        process_command = sql.process_command
    elif choice == "2":
        print("You selected NoSQL database.")
        import nosql
        process_command = nosql.process_command
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
