from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
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
        <title>FareFlow</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0B3C5D" />
        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 24%, #EAF5FC 24%, #F7FBFF 100%);
                min-height: 100vh;
                color: #16324a;
            }

            .app {
                min-height: 100vh;
                display: flex;
                justify-content: center;
            }

            .shell {
                width: 100%;
                max-width: 430px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                padding: 18px 12px 24px;
            }

            .topbar {
                color: white;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 4px 4px 18px;
            }

            .brand {
                font-size: 1.5rem;
                font-weight: 800;
                letter-spacing: -0.02em;
            }

            .brand-sub {
                font-size: 0.86rem;
                opacity: 0.88;
                margin-top: 4px;
            }

            .hero {
                color: white;
                padding: 8px 4px 24px;
            }

            .hero h1 {
                margin: 0 0 10px;
                font-size: 2.2rem;
                line-height: 1.05;
                letter-spacing: -0.03em;
            }

            .hero p {
                margin: 0;
                color: rgba(255,255,255,0.9);
                font-size: 1rem;
                line-height: 1.5;
            }

            .panel {
                background: rgba(255,255,255,0.98);
                border-radius: 28px 28px 0 0;
                flex: 1;
                padding: 20px 16px 24px;
                box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
            }

            .cta-grid {
                display: grid;
                gap: 12px;
            }

            .btn {
                text-decoration: none;
                border-radius: 20px;
                padding: 18px 18px;
                font-weight: 800;
                font-size: 1rem;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }

            .btn-primary {
                background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
                color: white;
                box-shadow: 0 14px 24px rgba(26,159,219,0.24);
            }

            .btn-secondary {
                background: #F2F8FC;
                color: #0B3C5D;
                border: 1px solid #DCEAF4;
            }

            .trust {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-top: 18px;
            }

            .trust-card {
                background: white;
                border: 1px solid #E3EEF6;
                border-radius: 18px;
                padding: 14px 10px;
                text-align: center;
                box-shadow: 0 8px 18px rgba(11,60,93,0.04);
            }

            .trust-icon {
                font-size: 1.2rem;
                margin-bottom: 8px;
            }

            .trust-text {
                color: #5f7688;
                font-size: 0.82rem;
                font-weight: 700;
                line-height: 1.35;
            }

            .section-title {
                margin: 22px 0 12px;
                color: #0B3C5D;
                font-size: 1rem;
                font-weight: 800;
            }

            .link-list {
                display: grid;
                gap: 10px;
            }

            .link-card {
                text-decoration: none;
                background: white;
                border: 1px solid #E3EEF6;
                border-radius: 18px;
                padding: 15px 16px;
                box-shadow: 0 8px 18px rgba(11,60,93,0.04);
                color: inherit;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
            }

            .link-title {
                color: #0B3C5D;
                font-weight: 800;
                margin-bottom: 4px;
            }

            .link-sub {
                color: #6b8293;
                font-size: 0.88rem;
            }

            .arrow {
                color: #1A9FDB;
                font-size: 1.2rem;
                font-weight: 800;
            }

            @media (max-width: 420px) {
                .hero h1 {
                    font-size: 1.95rem;
                }

                .trust {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="app">
            <div class="shell">
                <div class="topbar">
                    <div>
                        <div class="brand">FareFlow</div>
                        <div class="brand-sub">Digital taxi payments</div>
                    </div>
                </div>

                <div class="hero">
                    <h1>Pay your taxi fare in seconds.</h1>
                    <p>Scan, choose your seat, pay securely, and get your receipt instantly.</p>
                </div>

                <div class="panel">
                    <div class="cta-grid">
                        <a class="btn btn-primary" href="/scan">📷 Scan to Pay</a>
                        <a class="btn btn-secondary" href="/master/tx100-master">🚕 Choose Seat</a>
                    </div>

                    <div class="trust">
                        <div class="trust-card">
                            <div class="trust-icon">🛡️</div>
                            <div class="trust-text">Secure payments</div>
                        </div>
                        <div class="trust-card">
                            <div class="trust-icon">⚡</div>
                            <div class="trust-text">Instant updates</div>
                        </div>
                        <div class="trust-card">
                            <div class="trust-icon">🧾</div>
                            <div class="trust-text">Digital receipts</div>
                        </div>
                    </div>

                    <div class="section-title">More</div>
                    <div class="link-list">
                        <a class="link-card" href="/payments/history">
                            <div>
                                <div class="link-title">Payment History</div>
                                <div class="link-sub">View recent payments and receipts</div>
                            </div>
                            <div class="arrow">→</div>
                        </a>

                        <a class="link-card" href="/driver">
                            <div>
                                <div class="link-title">Driver View</div>
                                <div class="link-sub">Live seat status dashboard</div>
                            </div>
                            <div class="arrow">→</div>
                        </a>

                        <a class="link-card" href="/admin">
                            <div>
                                <div class="link-title">Admin</div>
                                <div class="link-sub">Operations and payment overview</div>
                            </div>
                            <div class="arrow">→</div>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

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
