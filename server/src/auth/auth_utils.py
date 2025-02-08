# auth_utils.py
import os
import jwt
import datetime
import logging
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    logger.error("JWT_SECRET is not set in environment variables!")
ALGORITHM = "HS256"

# This tells FastAPI where to look for the token (in the Authorization header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.datetime.utcnow() + expires_delta
        else:
            expire = datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise HTTPException(status_code=500, detail="Failed to create access token")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.error(f"Token expired: {e}")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise HTTPException(status_code=500, detail="Token verification failed")

def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_token(token)

def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        logger.warning(f"Access denied for non-admin user: {user}")
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

def require_user(user: dict = Depends(get_current_user)):
    if user.get("role") != "observer" and user.get("role") != "admin":
        logger.warning(f"Access denied for non-user: {user}")
        raise HTTPException(status_code=403, detail="Admin or Observer privileges required")
    return user