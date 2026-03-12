from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.db import SessionLocal, engine
from app.models import Base
from app.routers import taxis, trips, payments, seats, pages, debug, receipts, admin, payfast
from app.seed import seed_demo_data
from app.ws import manager

app = FastAPI(title="Taxi Pay API")

app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

db = SessionLocal()
seed_demo_data(db)
db.close()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TaxiPay</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#000000" />
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background: #f7f7f7;
                color: #111;
            }
            .card {
                background: white;
                padding: 24px;
                border-radius: 16px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            }
            h1 {
                margin-top: 0;
            }
            p {
                color: #444;
            }
            .qr-box {
                margin: 24px 0;
                text-align: center;
            }
            .qr-box img {
                width: 240px;
                max-width: 100%;
                border-radius: 12px;
                border: 1px solid #ddd;
                background: white;
                padding: 10px;
            }
            .btns {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 12px;
                margin-top: 24px;
            }
            a.btn {
                display: block;
                text-align: center;
                padding: 14px;
                text-decoration: none;
                background: black;
                color: white;
                border-radius: 10px;
                font-weight: bold;
            }
            .muted {
                font-size: 14px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>TaxiPay</h1>
            <p>QR taxi payment system for riders and drivers.</p>
            <p class="muted">Scan the QR below or use the demo buttons.</p>

            <div class="qr-box">
                <img src="/static/qrs/tx100-seat-1.png" alt="TaxiPay QR Code" />
                <p class="muted">Demo QR for Seat 1</p>
            </div>

            <div class="btns">
                <a class="btn" href="/rider/tx100-seat-1">Open Rider Seat 1</a>
                <a class="btn" href="/rider/tx100-seat-2">Open Rider Seat 2</a>
                <a class="btn" href="/driver">Open Driver Dashboard</a>
                <a class="btn" href="/admin">Open Admin Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """


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
app.include_router(payfast.router)

