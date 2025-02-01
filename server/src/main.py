import psycopg2
import psycopg2.extras
import time
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import get_db_connection, close_db_connection
from controllers import auth_router
from controllers import historical_data_router
from controllers import ws_endpoint
from controllers import order_router
from controllers import screener_router
from controllers import data_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to the specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(ws_endpoint, prefix="/ws")
app.include_router(historical_data_router, prefix="/api/historicaldata")
app.include_router(order_router, prefix="/api/order")
app.include_router(screener_router, prefix="/api/screener")
app.include_router(data_router, prefix="/api/data")

if __name__ == "__main__":
    
    # Start the FastAPI app with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)