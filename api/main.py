from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

# Secret key and algorithm for JWT
SECRET_KEY = "your_secret_key"  # Use a secure random key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Allow all origins for CORS (adjust as necessary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database (for demonstration purposes)
fake_users_db = {
    "john": {
        "username": "john",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": pwd_context.hash("password"),
    }
}

# Pydantic models for user and token
class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str
    
# Utility functions for authentication
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Login endpoint
@app.post("/login", response_model=Token)
async def login(request: LoginRequest):
    user = get_user(fake_users_db, request.username)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"username": user.username, "email": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}



@app.post("/users/get_current_user", response_model=User)
async def get_current_user(request: Token):
    token = request.access_token
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        if username is None:
            raise credentials_exception
        user = get_user(fake_users_db, username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception



# Load the JSON data from the file
with open("data.json") as f:
    data = json.load(f)

@app.get("/data", response_class=JSONResponse)
async def get_data():
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
