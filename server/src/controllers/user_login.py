# user_login.py
import os
import datetime
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from auth import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()

admin_pass = os.getenv("ADMIN_PASS")
observer_pass = os.getenv("OBSERVER_PASS")

if not admin_pass or not observer_pass:
    logger.error("ADMIN_PASS and/or OBSERVER_PASS are not set in environment variables.")

# Predefined users for in-house use
users_db = {
    "admin": {
        "password": admin_pass,
        "role": "admin"
    },
    "observer": {
        "password": observer_pass,
        "role": "observer"
    }
}

@router.post("/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = users_db.get(form_data.username)
        if not user or user["password"] != form_data.password:
            logger.warning(f"Invalid login attempt for user: {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        access_token = create_access_token(
            data={"sub": form_data.username, "role": user["role"]},
            expires_delta=datetime.timedelta(hours=12)
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during login for user {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
