import logging.config
import logging
import atexit
import asyncio
from contextlib import asynccontextmanager

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
            "filename": "server.log",
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
logger = logging.getLogger(__name__)

# Import async database manager
from db.async_connection import async_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - startup and shutdown"""
    # Startup
    logger.info("Starting VCP Trader API server...")
    
    try:
        # Initialize async database pools
        await async_db.initialize_pools()
        logger.info("Async database pools initialized")
        
        # Add performance monitoring
        logger.info("Performance monitoring enabled")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down VCP Trader API server...")
        
        # Close async database pools
        await async_db.close_pools()
        logger.info("Async database pools closed")
        
        # Cleanup thread pools
        cleanup_resources()

# Import routers after configuring logging
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
from controllers.risk_scores import router as risk_scores_router, risk_calculation_executor
from controllers.performance_monitor import router as performance_router

# Create FastAPI app with lifespan management
app = FastAPI(
    title="VCP Trader API",
    description="Optimized VCP Trading Platform API",
    version="2.0.0",
    lifespan=lifespan
)

# Add health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check with system status"""
    try:
        # Test database connectivity
        result = await async_db.execute_query("SELECT 1 as test", fetch='one')
        db_status = "healthy" if result and result.get('test') == 1 else "unhealthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return JSONResponse(content={
        "status": "healthy",
        "database": db_status,
        "timestamp": str(asyncio.get_event_loop().time()),
        "version": "2.0.0"
    }, status_code=200)

# Graceful shutdown for thread pool
def cleanup_resources():
    """Clean up resources on shutdown"""
    try:
        risk_calculation_executor.shutdown(wait=True, timeout=30)
        logger.info("Thread pool executor shut down gracefully")
    except Exception as e:
        logger.error(f"Error during thread pool shutdown: {e}")

# Register cleanup function
atexit.register(cleanup_resources)

# CORS configuration - more restrictive for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tradekeep.in",
        "https://www.tradekeep.in",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Enable GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers with proper prefixes
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(ws_endpoint, prefix="/socket", tags=["WebSocket"])
app.include_router(historical_data_router, prefix="/api/historicaldata", tags=["Historical Data"])
app.include_router(order_router, prefix="/api/order", tags=["Order Management"])
app.include_router(screener_router, prefix="/api/screener", tags=["Stock Screening"])
app.include_router(data_router, prefix="/api/data", tags=["Data Fetching"])
app.include_router(user_login_router, prefix="/api/login", tags=["User Login"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(watchlist_router, prefix="/api/watchlist", tags=["Watchlist"])
app.include_router(risk_scores_router, prefix="/api/risk_scores", tags=["Risk Scores"])
app.include_router(performance_router, prefix="/api/performance", tags=["Performance Monitoring"])

# Custom exception handlers
@app.exception_handler(500)
async def internal_server_error(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

@app.exception_handler(asyncio.TimeoutError)
async def timeout_error(request, exc):
    logger.warning(f"Request timeout: {exc}")
    return JSONResponse(
        status_code=504,
        content={"detail": "Request timeout - please try again"}
    )

if __name__ == "__main__":
    # Production-ready uvicorn configuration
    uvicorn.run(
        "main_optimized:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        workers=1,  # Single worker with async handling
        loop="uvloop",  # Use uvloop for better performance
        http="httptools",  # Use httptools for better HTTP parsing
        access_log=True,
        log_config=LOGGING_CONFIG
    ) 