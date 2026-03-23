from fastapi import APIRouter, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from app.auth import verify_session_token
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Seat, Taxi, Trip

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_db), admin_session: Optional[str] = Cookie(default=None)):
    if not admin_session or not verify_session_token(admin_session, "admin"):
        return RedirectResponse(url="/admin/login", status_code=302)
    taxis = db.query(Taxi).all()
    trips = db.query(Trip).all()

    active_trip = next((t for t in trips if t.status == "ACTIVE"), None)

    if active_trip:
        seats = db.query(Seat).filter(Seat.taxi_id == active_trip.taxi_id).all()
        payments = db.query(Payment).filter(Payment.trip_id == active_trip.id).all()
        total_trips = 1
    else:
        seats = db.query(Seat).all()
        payments = []
        total_trips = 0

    total_taxis = len(taxis)
    total_payments = len(payments)
    total_revenue = sum(p.amount for p in payments) if payments else 0.0

    paid_count = sum(1 for s in seats if s.status == "PAID")
    cash_count = sum(1 for s in seats if s.status == "CASH")
    unpaid_count = sum(1 for s in seats if s.status == "UNPAID")

    recent_payments_html = ""
    if payments:
        recent_payments = sorted(payments, key=lambda p: p.created_at, reverse=True)[:8]
        seat_lookup = {s.id: s for s in seats}

        for p in recent_payments:
            seat_obj = seat_lookup.get(p.seat_id)
            seat_label = f"Seat {seat_obj.seat_number}" if seat_obj else f"Seat {p.seat_id[:8]}"
            time_label = p.created_at.strftime("%d %b %H:%M") if getattr(p, "created_at", None) else "No time"

            recent_payments_html += f"""
            <div class="payment-row">
                <div>
                    <div class="payment-title">{seat_label}</div>
                    <div class="payment-sub">Trip {p.trip_id[:8]} • {p.status} • {time_label}</div>
                </div>
                <div class="payment-amount">R{p.amount:.2f}</div>
            </div>
            """
    else:
        recent_payments_html = """
        <div class="empty-state">No payments recorded yet. Start your first ride 🚕</div>
        """

    taxi_cards_html = ""
    if taxis:
        for taxi in taxis:
            taxi_cards_html += f"""
            <div class="mini-card">
                <div class="mini-title">{taxi.vehicle_code}</div>
                <div class="mini-sub">{taxi.route_name}</div>
                <div class="mini-meta">{taxi.seat_count} passenger seats</div>
            </div>
            """
    else:
        taxi_cards_html = '<div class="empty-state">No taxis found.</div>'

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
        }}
        .wrap {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 20px 48px;
        }}
        .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 32px;
            flex-wrap: wrap;
        }}
        .topbar-left {{ display: flex; align-items: center; gap: 14px; }}
        .logo {{
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            box-shadow: 0 6px 16px rgba(26,159,219,0.4);
            flex-shrink: 0;
        }}
        .topbar h1 {{ font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em; }}
        .topbar p {{ color: rgba(255,255,255,0.45); font-size: 0.88rem; margin-top: 3px; }}
        .back {{
            text-decoration: none;
            color: rgba(255,255,255,0.7);
            font-weight: 700;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            padding: 10px 16px;
            border-radius: 12px;
            font-size: 0.9rem;
            white-space: nowrap;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 24px;
        }}
        .stat {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 20px;
            padding: 20px;
        }}
        .stat-label {{ color: rgba(255,255,255,0.45); font-size: 0.82rem; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
        .stat-value {{ font-size: 2rem; font-weight: 800; color: white; }}
        .stat-value.green {{ color: #4ac96b; }}
        .stat-value.blue {{ color: #1A9FDB; }}
        .quick-actions {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }}
        .quick-card {{
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 12px;
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 16px;
            transition: border-color 0.15s, background 0.15s;
        }}
        .quick-card:hover {{
            border-color: rgba(26,159,219,0.3);
            background: rgba(26,159,219,0.06);
        }}
        .quick-icon {{
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }}
        .quick-title {{ font-weight: 800; color: white; font-size: 0.95rem; margin-bottom: 3px; }}
        .quick-sub {{ color: rgba(255,255,255,0.45); font-size: 0.82rem; }}
        .grid {{
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 18px;
        }}
        .card {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 20px;
            padding: 20px;
        }}
        .card h2 {{
            font-size: 1rem;
            font-weight: 800;
            color: rgba(255,255,255,0.7);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 16px;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 0;
        }}
        .status-box {{
            border-radius: 16px;
            padding: 16px 12px;
            font-weight: 800;
        }}
        .status-box small {{
            display: block;
            font-size: 0.78rem;
            opacity: 0.8;
            margin-bottom: 8px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .status-box strong {{ font-size: 2rem; }}
        .paid {{ background: rgba(74,201,107,0.15); border: 1px solid rgba(74,201,107,0.25); color: #4ac96b; }}
        .cash {{ background: rgba(244,197,66,0.15); border: 1px solid rgba(244,197,66,0.25); color: #F4C542; }}
        .open {{ background: rgba(231,76,60,0.15); border: 1px solid rgba(231,76,60,0.25); color: #f16b63; }}
        .payment-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .payment-row:last-child {{ border-bottom: none; }}
        .payment-title {{ font-weight: 800; color: white; font-size: 0.92rem; }}
        .payment-sub {{ color: rgba(255,255,255,0.4); font-size: 0.8rem; margin-top: 3px; }}
        .payment-amount {{ font-weight: 800; color: #1A9FDB; white-space: nowrap; font-size: 1rem; }}
        .view-all {{
            display: inline-block;
            margin-top: 14px;
            text-decoration: none;
            color: #1A9FDB;
            font-weight: 800;
            font-size: 0.88rem;
        }}
        .mini-card {{
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
            padding: 14px;
            margin-bottom: 10px;
        }}
        .mini-card:last-child {{ margin-bottom: 0; }}
        .mini-title {{ font-weight: 800; color: white; margin-bottom: 4px; }}
        .mini-sub {{ color: rgba(255,255,255,0.45); font-size: 0.85rem; margin-bottom: 6px; }}
        .mini-meta {{ color: #1A9FDB; font-weight: 700; font-size: 0.85rem; }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 11px 14px;
            border-radius: 12px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 8px;
        }}
        .info-item:last-child {{ margin-bottom: 0; }}
        .info-item span {{ color: rgba(255,255,255,0.45); font-size: 0.88rem; }}
        .info-item strong {{ color: white; font-size: 0.88rem; }}
        .empty-state {{ color: rgba(255,255,255,0.35); padding: 10px 0; font-size: 0.9rem; }}
        @media (max-width: 900px) {{
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
            .grid {{ grid-template-columns: 1fr; }}
            .quick-actions {{ grid-template-columns: 1fr 1fr; }}
        }}
        @media (max-width: 560px) {{
            .stats {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
            .quick-actions {{ grid-template-columns: 1fr; }}
            .status-grid {{ grid-template-columns: 1fr; }}
            .topbar h1 {{ font-size: 1.3rem; }}
        }}
    </style>
</head>
<body>
<div class="wrap">
    <div class="topbar">
        <div class="topbar-left">
            <div class="logo">📊</div>
            <div>
                <h1>Admin Dashboard</h1>
                <p>Fleet overview · active trip · revenue</p>
            </div>
        </div>
        <a href="/" class="back">← Home</a>
        <a href="/admin/logout" style="text-decoration:none;color:rgba(255,255,255,0.5);font-weight:700;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);padding:10px 16px;border-radius:12px;font-size:0.9rem;">Sign Out</a>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="stat-label">Taxis</div>
            <div class="stat-value blue">{total_taxis}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Active Trips</div>
            <div class="stat-value">{total_trips}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Payments</div>
            <div class="stat-value">{total_payments}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Revenue</div>
            <div class="stat-value green">R{total_revenue:.2f}</div>
        </div>
    </div>

    <div class="quick-actions">
        <a class="quick-card" href="/driver">
            <div class="quick-icon" style="background:rgba(26,159,219,0.15);">🚗</div>
            <div>
                <div class="quick-title">Driver View</div>
                <div class="quick-sub">Live seat map</div>
            </div>
        </a>
        <a class="quick-card" href="/payments/history">
            <div class="quick-icon" style="background:rgba(244,197,66,0.15);">🧾</div>
            <div>
                <div class="quick-title">Payment History</div>
                <div class="quick-sub">All transactions</div>
            </div>
        </a>
        <a class="quick-card" href="/master/tx100-master">
            <div class="quick-icon" style="background:rgba(74,201,107,0.15);">🗺️</div>
            <div>
                <div class="quick-title">Seat Map</div>
                <div class="quick-sub">Live rider view</div>
            </div>
        </a>
    </div>

    <div class="grid">
        <div style="display:grid;gap:18px;">
            <div class="card">
                <h2>Seat Status</h2>
                <div class="status-grid">
                    <div class="status-box paid">
                        <small>Paid</small>
                        <strong>{paid_count}</strong>
                    </div>
                    <div class="status-box cash">
                        <small>Cash</small>
                        <strong>{cash_count}</strong>
                    </div>
                    <div class="status-box open">
                        <small>Open</small>
                        <strong>{unpaid_count}</strong>
                    </div>
                </div>
            </div>
            <div class="card">
                <h2>Recent Payments</h2>
                {recent_payments_html}
                <a class="view-all" href="/payments/history">View all payments →</a>
            </div>
        </div>

        <div style="display:grid;gap:18px;">
            <div class="card">
                <h2>Taxi Fleet</h2>
                {taxi_cards_html}
            </div>
            <div class="card">
                <h2>System Status</h2>
                <div class="info-item">
                    <span>Active Trip</span>
                    <strong>#{active_trip.id[-4:].upper() if active_trip else "None"}</strong>
                </div>
                <div class="info-item">
                    <span>Trip Fare</span>
                    <strong>{"R" + f"{active_trip.fare_amount:.2f}" if active_trip else "N/A"}</strong>
                </div>
                <div class="info-item">
                    <span>Seats Tracked</span>
                    <strong>{len(seats)}</strong>
                </div>
                <div class="info-item">
                    <span>Mode</span>
                    <strong style="color:#4ac96b;">Live</strong>
                </div>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""
