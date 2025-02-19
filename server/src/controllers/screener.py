# screener.py
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services import screen_eligible_stocks_vcp, screen_eligible_stocks_ipo
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/vcpscreen")
async def screen_vcp(user: dict = Depends(get_current_user)):
    try:
        response = await asyncio.to_thread(screen_eligible_stocks_vcp)
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_vcp: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch VCP screener data")

@router.get("/iposcreen")
async def screen_ipo(user: dict = Depends(get_current_user)):
    try:
        response = await asyncio.to_thread(screen_eligible_stocks_ipo)
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_ipo: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch IPO screener data")
