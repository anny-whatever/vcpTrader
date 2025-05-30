import logging.config
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# Configure logging to output to both console and file.
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "server.log",  # Change the filename or path as needed
            "formatter": "standard",
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

# Import routers after configuring logging to ensure they inherit the configuration.
from controllers import (
    auth_router, 
    historical_data_router, 
    ws_endpoint, 
    order_router, 
    screener_router, 
    data_router, 
    user_login_router,
    alerts_router,
    watchlist_router
)
from controllers.risk_scores import router as risk_scores_router

app = FastAPI()

# Add health check endpoint
@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"}, status_code=200)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://devstatz.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
    ],# Or ["*"] for all origins (less secure)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable GZip compression for responses (minimum size in bytes)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(auth_router, prefix="/api")
app.include_router(ws_endpoint, prefix="/socket")  # WebSocket endpoint at /socket/ws
app.include_router(historical_data_router, prefix="/api/historicaldata")
app.include_router(order_router, prefix="/api/order")
app.include_router(screener_router, prefix="/api/screener")
app.include_router(data_router, prefix="/api/data")
app.include_router(user_login_router, prefix="/api/login")
app.include_router(alerts_router, prefix="/api/alerts")
app.include_router(watchlist_router, prefix="/api/watchlist")
app.include_router(risk_scores_router, prefix="/api/risk_scores")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
