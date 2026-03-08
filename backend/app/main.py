from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.db import engine
from app.models import Base
from app.routers import taxis, trips, payments, seats, pages, debug, receipts, admin
from app.ws import manager

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Taxi Pay API")


@app.get("/")
def home():
    return {
        "message": "Taxi Pay API is running",
        "rider_example": "/rider/tx100-seat-1",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/{trip_id}")
async def websocket_endpoint(websocket: WebSocket, trip_id: str):
    await manager.connect(trip_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(trip_id, websocket)


app.include_router(taxis.router)
app.include_router(trips.router)
app.include_router(payments.router)
app.include_router(seats.router)
app.include_router(pages.router)
app.include_router(debug.router)
app.include_router(receipts.router)
app.include_router(admin.router)
