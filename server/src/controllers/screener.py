# screener.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services import screen_eligible_stocks_vcp, screen_eligible_stocks_ipo
from auth import get_current_user

router = APIRouter()

@router.get("/vcpscreen")
async def screen_vcp(user: dict = Depends(get_current_user)):
    try:
        response = screen_eligible_stocks_vcp()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/iposcreen")
async def screen_ipo(user: dict = Depends(get_current_user)):
    try:
        response = screen_eligible_stocks_ipo()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}
