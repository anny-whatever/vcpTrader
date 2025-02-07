import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers import auth_router, historical_data_router, ws_endpoint, order_router, screener_router, data_router, user_login_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(ws_endpoint, prefix="/socket")  # WebSocket endpoint at /socket/ws
app.include_router(historical_data_router, prefix="/api/historicaldata")
app.include_router(order_router, prefix="/api/order")
app.include_router(screener_router, prefix="/api/screener")
app.include_router(data_router, prefix="/api/data")
app.include_router(user_login_router, prefix="/api/login")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
