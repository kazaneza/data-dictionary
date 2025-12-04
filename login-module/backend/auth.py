from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from config import ADMIN_USERS, MANAGER_USERS, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
from pydantic import BaseModel

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    token: str
    role: str

def get_user_role(username: str) -> str:
    """Determine user role based on username"""
    if username in ADMIN_USERS:
        return "admin"
    elif username in MANAGER_USERS:
        return "manager"
    return "user"

def create_access_token(username: str, role: str) -> str:
    """Create JWT token"""
    token_data = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    }
    return jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"username": username, "role": role}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

