from services import get_positions, get_flags
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/flags")
async def historical_data():
    try:
        response = get_flags()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/positions")
async def historical_data():
    try:
        response = get_positions()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

