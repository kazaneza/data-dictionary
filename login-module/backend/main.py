from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import uvicorn
import jwt
from auth import LoginRequest, Token, get_user_role, create_access_token
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Login API", description="Standalone login authentication service")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Auth endpoint
@app.post("/auth/login", response_model=Token)
async def login(request: LoginRequest):
    try:
        # In a real application, you would verify the password against a secure store
        # For this example, we're using a simple check
        if not request.password:  # Basic validation
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        # Get user role
        role = get_user_role(request.username)
        
        # Create JWT token
        token = create_access_token(request.username, role)
        
        logger.info(f"User {request.username} logged in with role {role}")
        return {"token": token, "role": role}
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

