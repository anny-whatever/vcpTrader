from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services import screen_eligible_stocks

router = APIRouter()

@router.get("/vcpscreen")
async def screen_stocks():
    try:
        response = screen_eligible_stocks()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}