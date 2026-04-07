from dotenv import load_dotenv
load_dotenv()
import os
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from app.db import SessionLocal, engine
from app.models import Base
from app.routers import taxis, trips, payments, seats, pages, debug, receipts, admin, payfast, auth
from app.seed import seed_demo_data
from app.ws import manager

app = FastAPI(title="Taxi Pay API")

# ── CORS lockdown ──────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Input sanitisation middleware ──────────────────────────────
DANGEROUS = re.compile(
    r"(<script|javascript:|vbscript:|onload\s*=|onerror\s*=|"
    r"union\s+select|drop\s+table|insert\s+into|delete\s+from|"
    r"<iframe|<object|eval\s*\(|\.\.\/|etc\/passwd)",
    re.IGNORECASE
)

class SanitiseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check query params
        for val in request.query_params.values():
            if DANGEROUS.search(val):
                return JSONResponse({"detail": "Invalid request"}, status_code=400)
        # Check body for POST/PUT
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if body and DANGEROUS.search(body.decode("utf-8", errors="ignore")):
                    return JSONResponse({"detail": "Invalid request"}, status_code=400)
            except Exception:
                pass
        return await call_next(request)

app.add_middleware(SanitiseMiddleware)

# ── Security headers middleware ────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

db = SessionLocal()
seed_demo_data(db)
db.close()

@app.get("/manifest.json")
def manifest_json():
    from fastapi.responses import FileResponse
    return FileResponse("static/manifest.json", media_type="application/manifest+json")
@app.get("/", response_class=HTMLResponse)

def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="manifest" href="/static/manifest.json" />
    <link rel="apple-touch-icon" href="/static/icon-192.png" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="FareFlow" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
            display: flex;
            justify-content: center;
        }
        .shell {
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        .bg-glow {
            position: absolute;
            top: -80px;
            left: 50%;
            transform: translateX(-50%);
            width: 340px;
            height: 340px;
            background: radial-gradient(circle, rgba(26,159,219,0.35) 0%, transparent 70%);
            pointer-events: none;
        }
        .topbar {
            padding: 22px 20px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            z-index: 1;
        }
        .brand { display: flex; align-items: center; gap: 10px; }
        .brand-logo {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            box-shadow: 0 6px 16px rgba(26,159,219,0.4);
        }
        .brand-name { font-size: 1.3rem; font-weight: 800; letter-spacing: -0.02em; }
        .brand-tag { font-size: 0.75rem; color: rgba(255,255,255,0.5); margin-top: 1px; }
        .hero { padding: 40px 20px 32px; position: relative; z-index: 1; }
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(26,159,219,0.15);
            border: 1px solid rgba(26,159,219,0.3);
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 0.78rem;
            font-weight: 700;
            color: #6dd5fa;
            margin-bottom: 16px;
        }
        .hero h1 {
            font-size: 2.4rem;
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: -0.03em;
            margin-bottom: 12px;
        }
        .hero h1 span {
            background: linear-gradient(90deg, #1A9FDB, #6dd5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p { color: rgba(255,255,255,0.65); font-size: 1rem; line-height: 1.6; }
        .panel {
            background: #0d1f2e;
            border-radius: 28px 28px 0 0;
            flex: 1;
            padding: 24px 20px 32px;
            border-top: 1px solid rgba(255,255,255,0.08);
            position: relative;
            z-index: 1;
        }
        .cta-grid { display: grid; gap: 12px; margin-bottom: 28px; }
        .btn {
            text-decoration: none;
            border-radius: 18px;
            padding: 18px 20px;
            font-weight: 800;
            font-size: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .btn:active { transform: scale(0.98); }
        .btn-primary {
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            color: white;
            box-shadow: 0 14px 28px rgba(26,159,219,0.35);
        }
        .btn-secondary {
            background: rgba(255,255,255,0.06);
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .trust { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 28px; }
        .trust-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px;
            padding: 14px 8px;
            text-align: center;
        }
        .trust-icon { font-size: 1.3rem; margin-bottom: 8px; }
        .trust-text { color: rgba(255,255,255,0.55); font-size: 0.78rem; font-weight: 700; line-height: 1.35; }
        .section-title {
            color: rgba(255,255,255,0.45);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 12px;
        }
        .link-list { display: grid; gap: 10px; }
        .link-card {
            text-decoration: none;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            transition: background 0.15s;
        }
        .link-card:hover { background: rgba(255,255,255,0.07); }
        .link-icon {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            flex-shrink: 0;
        }
        .link-body { flex: 1; }
        .link-title { color: white; font-weight: 800; font-size: 0.95rem; margin-bottom: 3px; }
        .link-sub { color: rgba(255,255,255,0.45); font-size: 0.82rem; }
        .arrow { color: rgba(255,255,255,0.3); font-size: 1.1rem; }
        @media (max-width: 420px) {
            .hero h1 { font-size: 2rem; }
            .trust { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

<!-- Splash loader -->
<div id="splash" style="position:fixed;inset:0;background:#060f1a;z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;transition:opacity 0.5s ease;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <img src="/static/icon-192.png" style="width:56px;height:56px;border-radius:16px;box-shadow:0 8px 24px rgba(26,159,219,0.4);">
        <div>
            <div style="font-size:1.8rem;font-weight:800;color:white;letter-spacing:-0.02em;">FareFlow</div>
            <div style="font-size:0.82rem;color:rgba(255,255,255,0.45);margin-top:2px;">The smarter way to pay your fare</div>
        </div>
    </div>
    <div id="splashSpinner" style="width:44px;height:44px;border:3px solid rgba(26,159,219,0.2);border-top:3px solid #1A9FDB;border-radius:50%;"></div>
    <style>
        @keyframes splashSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        #splashSpinner {
            animation: splashSpin 0.8s linear infinite;
        }
    </style>
</div>

<script>
window.addEventListener('load', function() {{
    setTimeout(function() {{
        const splash = document.getElementById('splash');
        splash.style.opacity = '0';
        setTimeout(() => splash.style.display = 'none', 500);
    }}, 2500);
}});
</script>
<div class="shell">
    <div class="bg-glow"></div>
    <div class="topbar">
        <div class="brand">
            <div class="brand-logo">🚕</div>
            <div>
                <div class="brand-name">FareFlow</div>
                <div class="brand-tag">Digital taxi payments</div>
            </div>
        </div>
    </div>
    <div class="hero">
        <div class="hero-badge">⚡ Instant &amp; secure</div>
        <h1>Pay your taxi fare <span>in seconds.</span></h1>
        <p>Scan the QR on your seat, choose how to pay, and get your receipt instantly.</p>
    </div>
    <div class="panel">
        <div class="cta-grid">
            <a class="btn btn-primary" href="/scan">📷 Scan Seat QR to Pay</a>
            <a class="btn btn-secondary" href="/fleet">🚕 Choose Your Taxi</a>
        </div>
        <div class="trust">
            <div class="trust-card">
                <div class="trust-icon">🛡️</div>
                <div class="trust-text">Secure payments</div>
            </div>
            <div class="trust-card">
                <div class="trust-icon">⚡</div>
                <div class="trust-text">Instant receipt</div>
            </div>
            <div class="trust-card">
                <div class="trust-icon">💵</div>
                <div class="trust-text">Cash welcome</div>
            </div>
        </div>
        <div class="section-title">Quick Access</div>
        <div class="link-list">
            <a class="link-card" href="/driver">
                <div class="link-icon" style="background:rgba(26,159,219,0.15);">🚗</div>
                <div class="link-body">
                    <div class="link-title">Driver Dashboard</div>
                    <div class="link-sub">Live seat map and trip controls</div>
                </div>
                <div class="arrow">›</div>
            </a>
            <a class="link-card" href="/admin">
                <div class="link-icon" style="background:rgba(74,201,107,0.15);">📊</div>
                <div class="link-body">
                    <div class="link-title">Admin Panel</div>
                    <div class="link-sub">Fleet, revenue and trip history</div>
                </div>
                <div class="arrow">›</div>
            </a>
            <a class="link-card" href="/payments/history">
                <div class="link-icon" style="background:rgba(244,197,66,0.15);">🧾</div>
                <div class="link-body">
                    <div class="link-title">Payment History</div>
                    <div class="link-sub">All trips and transactions</div>
                </div>
                <div class="arrow">›</div>
            </a>
        </div>
    </div>
</div>
<script>
if ('serviceWorker' in navigator) {{
    window.addEventListener('load', function() {{
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(reg) {{ console.log('SW registered'); }})
            .catch(function(err) {{ console.log('SW error', err); }});
    }});
}}
</script>
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


app.include_router(auth.router)
app.include_router(taxis.router)
app.include_router(trips.router)
app.include_router(payments.router)
app.include_router(seats.router)
app.include_router(pages.router)
app.include_router(debug.router)
app.include_router(receipts.router)
app.include_router(admin.router)
app.include_router(payfast.router)
