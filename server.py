from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import bcrypt
from pydantic import BaseModel
import jwt  # ✅ Import pyjwt
from datetime import timedelta

# Initialize FastAPI
app = FastAPI()

# Database setup
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT Setup
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="user")  

Base.metadata.create_all(bind=engine) 

# Pydantic models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Register user
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

# Login user
@app.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    if db_user and bcrypt.checkpw(user.password.encode(), db_user.password.encode()):
        token_data = {"username": db_user.username, "role": db_user.role}
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        return {"token": token}
    
    raise HTTPException(status_code=401, detail="Invalid username or password")

# Secure route dependency
auth_scheme = HTTPBearer()

# Protected Route (Requires JWT Token)
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

# Run server with Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000)
