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
        <title>TaxiPay</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0B3C5D" />
        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 22%, #EAF5FC 22%, #F7FBFF 100%);
                min-height: 100vh;
                color: #16324a;
            }

            .app {
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: stretch;
            }

            .mobile-shell {
                width: 100%;
                max-width: 430px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }

            .top {
                padding: 28px 20px 22px;
                color: white;
            }

            .brand-row {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 2rem;
                font-weight: 800;
                letter-spacing: -0.5px;
            }

            .brand-icon {
                font-size: 1.9rem;
            }

            .hero-card {
                margin-top: 18px;
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.18);
                backdrop-filter: blur(6px);
                border-radius: 20px;
                padding: 18px 16px;
            }

            .hero-card h1 {
                margin: 0 0 8px;
                font-size: 1.65rem;
                line-height: 1.15;
                font-weight: 800;
            }

            .hero-card p {
                margin: 0;
                color: rgba(255,255,255,0.92);
                line-height: 1.45;
                font-size: 0.97rem;
            }

            .content {
                flex: 1;
                padding: 0 16px 24px;
                margin-top: -6px;
            }

            .panel {
                background: rgba(255,255,255,0.98);
                border-radius: 28px 28px 0 0;
                min-height: calc(100vh - 220px);
                padding: 22px 16px 28px;
                box-shadow: 0 -6px 24px rgba(11,60,93,0.08);
                position: relative;
                overflow: hidden;
            }

            .panel::after {
                content: "";
                position: absolute;
                right: -60px;
                bottom: -50px;
                width: 220px;
                height: 220px;
                background: radial-gradient(circle, rgba(26,159,219,0.16) 0%, rgba(26,159,219,0) 70%);
                pointer-events: none;
            }

            .section-title {
                margin: 0;
                font-size: 1.3rem;
                color: #0B3C5D;
                font-weight: 800;
            }

            .section-subtitle {
                margin: 8px 0 20px;
                color: #60798b;
                font-size: 0.95rem;
                line-height: 1.45;
            }

            .role-list {
                display: grid;
                gap: 14px;
                position: relative;
                z-index: 1;
            }

            .role-card {
                display: flex;
                align-items: center;
                justify-content: space-between;
                text-decoration: none;
                background: white;
                border: 1px solid #E3EEF6;
                border-radius: 22px;
                padding: 16px 15px;
                box-shadow: 0 8px 22px rgba(17, 68, 102, 0.08);
                transition: transform 0.18s ease, box-shadow 0.18s ease;
            }

            .role-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 12px 28px rgba(17, 68, 102, 0.14);
            }

            .role-left {
                display: flex;
                align-items: center;
                gap: 14px;
            }

            .icon-box {
                width: 54px;
                height: 54px;
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.45rem;
                font-weight: bold;
                flex-shrink: 0;
            }

            .rider .icon-box {
                background: rgba(26,159,219,0.14);
                color: #1A9FDB;
            }

            .driver .icon-box {
                background: rgba(11,60,93,0.12);
                color: #0B3C5D;
            }

            .admin .icon-box {
                background: rgba(90,121,139,0.12);
                color: #5A798B;
            }

            .role-text h3 {
                margin: 0;
                font-size: 1.07rem;
                color: #0B3C5D;
            }

            .role-text p {
                margin: 5px 0 0;
                font-size: 0.9rem;
                color: #6A8191;
            }

            .arrow {
                color: #98AFC0;
                font-size: 1.5rem;
                font-weight: bold;
            }

            .quick-grid {
                margin-top: 18px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                position: relative;
                z-index: 1;
            }

            .quick-link {
                text-decoration: none;
                background: #F2F8FC;
                border: 1px solid #DCEAF4;
                color: #0B3C5D;
                border-radius: 16px;
                padding: 14px 12px;
                text-align: center;
                font-weight: 700;
                font-size: 0.94rem;
            }

            .status-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 18px;
                position: relative;
                z-index: 1;
            }

            .chip {
                background: #EAF5FC;
                color: #0B3C5D;
                border: 1px solid #D4E8F4;
                padding: 8px 12px;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 700;
            }

            .footer-note {
                margin-top: 18px;
                text-align: center;
                color: #7D94A3;
                font-size: 0.86rem;
                position: relative;
                z-index: 1;
            }

            @media (max-width: 520px) {
                .top {
                    padding: 24px 16px 20px;
                }

                .content {
                    padding: 0 10px 18px;
                }

                .panel {
                    padding: 20px 14px 24px;
                    border-radius: 24px 24px 0 0;
                }

                .brand-row {
                    font-size: 1.8rem;
                }

                .hero-card h1 {
                    font-size: 1.45rem;
                }

                .quick-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="app">
            <div class="mobile-shell">
                <div class="top">
                    <div class="brand-row">
                        <span class="brand-icon">🚖</span>
                        <span>TaxiPay</span>
                    </div>

                    <div class="hero-card">
                        <h1>Smart taxi payments for riders and drivers</h1>
                        <p>
                            Pay quickly, track seats in real time, and manage
                            trips with a cleaner, safer, and more trusted system.
                        </p>
                    </div>
                </div>

                <div class="content">
                    <div class="panel">
                        <h2 class="section-title">Get started</h2>
                        <p class="section-subtitle">
                            Choose how you want to use TaxiPay today.
                        </p>

                        <div class="role-list">
                            <a class="role-card rider" href="/master/tx100-master">
                                <div class="role-left">
                                    <div class="icon-box">👤</div>
                                    <div class="role-text">
                                        <h3>I’m a Rider</h3>
                                        <p>Select your seat and pay for your ride</p>
                                    </div>
                                </div>
                                <div class="arrow">›</div>
                            </a>

                            <a class="role-card driver" href="/driver">
                                <div class="role-left">
                                    <div class="icon-box">🛞</div>
                                    <div class="role-text">
                                        <h3>I’m a Driver</h3>
                                        <p>Track seats, payments, and trip progress</p>
                                    </div>
                                </div>
                                <div class="arrow">›</div>
                            </a>

                            <a class="role-card admin" href="/admin">
                                <div class="role-left">
                                    <div class="icon-box">⚙️</div>
                                    <div class="role-text">
                                        <h3>Admin</h3>
                                        <p>View system activity, trips, and reports</p>
                                    </div>
                                </div>
                                <div class="arrow">›</div>
                            </a>
                        </div>

                        <div class="quick-grid">
                            <a class="quick-link" href="/rider/tx100-seat-1">Demo Seat 1</a>
                            <a class="quick-link" href="/docs">API Docs</a>
                        </div>

                        <div class="status-chip-row">
                            <span class="chip">Toyota Quantum demo</span>
                            <span class="chip">15 passenger seats</span>
                            <span class="chip">1 master QR</span>
                        </div>

                        <div class="footer-note">
                            Blue theme · mobile-first · real-time dashboard
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/live")
def health_live():
    return {"status": "live"}

@app.get("/health/ready")
def health_ready():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}
    finally:
        db.close()

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
