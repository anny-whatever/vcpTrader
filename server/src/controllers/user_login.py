# user_login.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from auth import create_access_token
import datetime
import os

router = APIRouter()


admin_pass = os.getenv("ADMIN_PASS")
observer_pass = os.getenv("OBSERVER_PASS")

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
    user = users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(
        data={"sub": form_data.username, "role": user["role"]},
        expires_delta=datetime.timedelta(hours=12)
    )
    return {"access_token": access_token, "token_type": "bearer"}
