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

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

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
        :root {
            --bg: #060f1a;
            --bg2: #0d1f2e;
            --text: white;
            --text-muted: rgba(255,255,255,0.5);
            --border: rgba(255,255,255,0.08);
            --card-bg: rgba(255,255,255,0.04);
        }
        [data-theme="light"] {
            --bg: #ffffff;
            --bg2: #f7f9fc;
            --text: #0d1f2e;
            --text-muted: rgba(13,31,46,0.5);
            --border: rgba(13,31,46,0.1);
            --card-bg: rgba(13,31,46,0.03);
        }
        [data-theme="light"] body {
            background: linear-gradient(180deg, #e8f4fd 0%, #f5f8fb 100%);
        }
        [data-theme="light"] .trust-card {
            box-shadow: 0 4px 16px rgba(13,31,46,0.08);
        }
        [data-theme="light"] .link-card {
            box-shadow: 0 4px 16px rgba(13,31,46,0.07);
        }
        [data-theme="light"] .link-card:hover {
            box-shadow: 0 8px 24px rgba(26,159,219,0.15);
            border-color: rgba(26,159,219,0.25);
        }
        [data-theme="light"] .panel {
            box-shadow: 0 -8px 32px rgba(13,31,46,0.08);
        }
        [data-theme="light"] .btn-primary {
            box-shadow: 0 8px 24px rgba(26,159,219,0.35);
        }
        [data-theme="light"] .btn-secondary {
            box-shadow: 0 4px 12px rgba(13,31,46,0.08);
        }
        [data-theme="light"] .brand-name { color: #0d1f2e; }
        [data-theme="light"] .brand-tag { color: rgba(13,31,46,0.5); }
        [data-theme="light"] .hero h1 { color: #0d1f2e; }
        [data-theme="light"] .hero p { color: rgba(13,31,46,0.6); }
        [data-theme="light"] .hero-badge {
            background: rgba(26,159,219,0.1);
            border-color: rgba(26,159,219,0.3);
            color: #0B72C6;
        }
        [data-theme="light"] .panel {
            background: #ffffff;
            border-top: 1px solid rgba(13,31,46,0.08);
            box-shadow: 0 -4px 24px rgba(13,31,46,0.06);
        }
        [data-theme="light"] .btn-secondary {
            background: rgba(13,31,46,0.06);
            color: #0d1f2e;
            border-color: rgba(13,31,46,0.12);
        }
        [data-theme="light"] .trust-card {
            background: #f7f9fc;
            border-color: rgba(13,31,46,0.08);
        }
        [data-theme="light"] .trust-text { color: rgba(13,31,46,0.55); }
        [data-theme="light"] .section-title { color: rgba(13,31,46,0.45); }
        [data-theme="light"] .link-card {
            background: #f7f9fc;
            border-color: rgba(13,31,46,0.08);
        }
        [data-theme="light"] .link-card:hover { background: #eef3f8; }
        [data-theme="light"] .link-title { color: #0d1f2e; }
        [data-theme="light"] .link-sub { color: rgba(13,31,46,0.45); }
        [data-theme="light"] .arrow { color: rgba(13,31,46,0.3); }
        [data-theme="light"] .theme-toggle {
            background: rgba(13,31,46,0.06);
            border-color: rgba(13,31,46,0.12);
            color: #0d1f2e;
        }
        .theme-toggle {
            width: 40px; height: 40px; border-radius: 12px;
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--text); font-size: 1.1rem;
            cursor: pointer; display: flex;
            align-items: center; justify-content: center;
            transition: background 0.2s;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }

        /* Premium animations */
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(24px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-6px); }
        }
        @keyframes shimmer {
            0% { background-position: -200% center; }
            100% { background-position: 200% center; }
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 14px 28px rgba(26,159,219,0.35); }
            50% { box-shadow: 0 14px 36px rgba(26,159,219,0.6); }
        }

        .brand { animation: fadeIn 0.6s ease; }
        .hero-badge { animation: fadeUp 0.5s ease 0.1s both; }
        .hero h1 { animation: fadeUp 0.5s ease 0.2s both; }
        .hero p { animation: fadeUp 0.5s ease 0.3s both; }
        .panel { animation: fadeUp 0.6s ease 0.4s both; }

        .brand-logo { transition: transform 0.2s ease; }

        .btn-primary {
            animation: pulse-glow 2.5s ease-in-out infinite;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            animation: none;
            box-shadow: 0 18px 36px rgba(26,159,219,0.5);
        }

        .link-card {
            transition: transform 0.2s ease, background 0.2s, border-color 0.2s, box-shadow 0.2s;
        }
        .link-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 28px rgba(26,159,219,0.15);
            border-color: rgba(26,159,219,0.25);
        }

        .trust-card {
            transition: transform 0.2s ease, box-shadow 0.2s;
        }
        .trust-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(26,159,219,0.12);
        }

        .theme-toggle {
            transition: transform 0.2s, background 0.2s;
        }
        .theme-toggle:hover { transform: scale(1.1); }
        .theme-toggle:active { transform: scale(0.95); }
        .theme-toggle span { display:inline-block; transition: transform 0.4s ease; }
        .theme-toggle.flipping span { transform: rotateY(360deg); }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: var(--bg);
            min-height: 100vh;
            color: var(--text);
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
            background: var(--card-bg);
            border: 1px solid var(--border);
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
            background: var(--card-bg);
            border: 1px solid var(--border);
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
            <img src="/static/icon-192.png" style="width:44px;height:44px;border-radius:12px;box-shadow:0 4px 12px rgba(26,159,219,0.3);">
            <div>
                <div class="brand-name">FareFlow</div>
                <div class="brand-tag">Digital taxi payments</div>
            </div>
        </div>
        <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn"><span>🌙</span></button>
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
function toggleTheme() {{
    const html = document.documentElement;
    const btn = document.getElementById("themeBtn");
    btn.classList.add("flipping");
    setTimeout(() => btn.classList.remove("flipping"), 400);
    if (html.getAttribute("data-theme") === "light") {{
        html.removeAttribute("data-theme");
        btn.innerHTML = "<span>🌙</span>";
        localStorage.setItem("theme", "dark");
    }} else {{
        html.setAttribute("data-theme", "light");
        btn.innerHTML = "<span>☀️</span>";
        localStorage.setItem("theme", "light");
    }}
}}
// Apply saved theme on load
(function() {{
    if (localStorage.getItem("theme") === "light") {{
        document.documentElement.setAttribute("data-theme", "light");
        document.addEventListener("DOMContentLoaded", function() {{
            const btn = document.getElementById("themeBtn");
            if (btn) btn.textContent = "☀️";
        }});
    }}
}})();
</script>
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