import threading
import time
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import bcrypt
from pydantic import BaseModel
import jwt
from datetime import timedelta
import requests
import uvicorn

# ---------------------- FastAPI Setup ----------------------
app = FastAPI()
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="user")

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register", status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    new_user = User(username=user.username, password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully!"}

@app.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user and bcrypt.checkpw(user.password.encode(), db_user.password.encode()):
        token_data = {"username": db_user.username, "role": db_user.role}
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid username or password")

auth_scheme = HTTPBearer()

@app.get("/protected")
def protected(authorization: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = authorization.credentials
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"message": f"Welcome {decoded_token['username']}, your role is {decoded_token['role']}!"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------------- Console Auth and Flow ----------------------

AUTH_SERVER = "http://127.0.0.1:8000"

def authenticate():
    while True:
        print("\n1. Login\n2. Register\n3. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            response = requests.post(f"{AUTH_SERVER}/login", json={"username": username, "password": password})
            if response.status_code == 200:
                token = response.json()["token"]
                print(f"Login successful!")
                return token
            else:
                print(f"Login failed: {response.status_code} - {response.text}")
        elif choice == "2":
            username = input("Choose a username: ").strip()
            password = input("Choose a password: ").strip()
            response = requests.post(f"{AUTH_SERVER}/register", json={"username": username, "password": password})
            if response.status_code == 201:
                print("Registration successful! You can now log in.")
            else:
                print(f"Registration failed: {response.status_code} - {response.text}")
        elif choice == "3":
            return None
        else:
            print("Invalid option. Try again.")

def test_protected_route(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{AUTH_SERVER}/protected", headers=headers)
    if response.status_code == 200:
        print("Protected Route Access:", response.json()["message"])
        return True
    else:
        print(f"Failed to access protected route: {response.status_code} - {response.text}")
        return False

# ---------------------- Main Program Logic ----------------------

def run_console_program():
    token = authenticate()
    if not token:
        print("Authentication required. Exiting.")
        return

    if not test_protected_route(token):
        print("Token is invalid or expired. Please login again.")
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

def start_server():
    uvicorn.run("xdb:app", host="127.0.0.1", port=8000, log_level="error", access_log=False)
    
if __name__ == "__main__":
    # Start the FastAPI server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait a moment for server to start
    time.sleep(1)
    print("Server connected successfully\n")

    # Start the console logic
    run_console_program()