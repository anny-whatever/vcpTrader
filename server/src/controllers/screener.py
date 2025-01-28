from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services import screen_eligible_stocks_vcp, screen_eligible_stocks_ipo

router = APIRouter()

@router.get("/vcpscreen")
async def screen_stocks():
    try:
        response = screen_eligible_stocks_vcp()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/iposcreen")
async def screen_stocks_ipo():
    try:
        response = screen_eligible_stocks_ipo()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}