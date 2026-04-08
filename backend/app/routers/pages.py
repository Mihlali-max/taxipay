from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Seat, Trip
from app.fares import get_route_fare

router = APIRouter()

@router.get("/fleet", response_class=HTMLResponse)
def fleet_page(db: Session = Depends(get_db)):
    taxis = db.query(Taxi).all()
    taxi_cards = ""
    for taxi in taxis:
        trip = db.query(Trip).filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE").first()
        fare = trip.fare_amount if trip else 0
        paid = 0
        total = taxi.seat_count
        if trip:
            paid = db.query(Seat).filter(Seat.taxi_id == taxi.id, Seat.status.in_(["PAID","CASH"])).count()
        open_seats = total - paid
        token = f"{taxi.vehicle_code.replace(' ','').replace('-','').lower()}-master"
        taxi_cards += f"""
        <a href="/master/{token}" class="taxi-card">
            <div class="taxi-icon">🚕</div>
            <div class="taxi-body">
                <div class="taxi-code">{taxi.vehicle_code}</div>
                <div class="taxi-route">{taxi.route_name}</div>
                <div class="taxi-meta">
                    <span style="color:#4ac96b;">{paid} paid</span>
                    <span style="color:rgba(255,255,255,0.3);">·</span>
                    <span style="color:#f16b63;">{open_seats} open</span>
                    <span style="color:rgba(255,255,255,0.3);">·</span>
                    <span style="color:#1A9FDB;">R{fare:.2f}</span>
                </div>
            </div>
            <div class="taxi-arrow">›</div>
        </a>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - Choose Your Taxi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="manifest" href="/static/manifest.json" />
    <link rel="apple-touch-icon" href="/static/icon-192.png" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="FareFlow" />
    <meta name="theme-color" content="#060f1a" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #060f1a; min-height: 100vh; color: white;
            display: flex; justify-content: center;
        }}
        .shell {{
            width: 100%; max-width: 430px; min-height: 100vh;
            display: flex; flex-direction: column; position: relative;
        }}
        .bg-glow {{
            position: fixed; top: -80px; left: 50%;
            transform: translateX(-50%); width: 400px; height: 400px;
            background: radial-gradient(circle, rgba(26,159,219,0.2) 0%, transparent 70%);
            pointer-events: none;
        }}
        .topbar {{
            padding: 22px 20px 0; display: flex; align-items: center;
            gap: 10px; position: relative; z-index: 1;
        }}
        .back {{
            text-decoration: none; color: white; font-size: 1.8rem; line-height: 1;
        }}
        .topbar-title {{ font-size: 1.1rem; font-weight: 800; }}
        .content {{ flex: 1; padding: 20px 18px 32px; position: relative; z-index: 1; min-height: 400px; }}
        .hero-text {{
            font-size: 1.4rem; font-weight: 800; margin-bottom: 6px;
        }}
        .hero-sub {{
            color: rgba(255,255,255,0.45); font-size: 0.88rem; margin-bottom: 20px;
        }}
        .section-title {{
            color: rgba(255,255,255,0.4); font-size: 0.75rem; font-weight: 800;
            text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px;
        }}
        .taxi-card {{
            text-decoration: none;
            display: flex; align-items: center; gap: 14px;
            background: #0d1f2e; border: 1px solid rgba(255,255,255,0.07);
            border-radius: 20px; padding: 16px; margin-bottom: 10px;
            transition: border-color 0.15s, background 0.15s;
        }}
        .taxi-card:hover {{
            border-color: rgba(26,159,219,0.3);
            background: rgba(26,159,219,0.06);
        }}
        .taxi-icon {{
            width: 48px; height: 48px; border-radius: 14px;
            background: rgba(26,159,219,0.12); display: flex;
            align-items: center; justify-content: center; font-size: 1.4rem;
            flex-shrink: 0;
        }}
        .taxi-body {{ flex: 1; }}
        .taxi-code {{ color: white; font-weight: 800; font-size: 1rem; margin-bottom: 3px; }}
        .taxi-route {{ color: rgba(255,255,255,0.5); font-size: 0.85rem; margin-bottom: 6px; }}
        .taxi-meta {{ display: flex; gap: 8px; font-size: 0.8rem; font-weight: 700; }}
        .taxi-arrow {{ color: rgba(255,255,255,0.3); font-size: 1.3rem; }}
    </style>
</head>
<body>
<div class="shell">
    <div class="bg-glow"></div>
    <div class="topbar">
        <a href="/" class="back">‹</a>
        <span class="topbar-title">Choose Your Taxi</span>
    </div>
    <div class="content">
        <div class="hero-text">Active Taxis 🚕</div>
        <div class="hero-sub">Select your taxi to view the seat map and pay</div>
        <div class="section-title">Kuwait Rank · Site C · Khayelitsha</div>
        {taxi_cards}
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
</html>"""


@router.get("/master/{token}", response_class=HTMLResponse)
def master_page(token: str, db: Session = Depends(get_db)):
    taxi = db.query(Taxi).order_by(Taxi.vehicle_code).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi not found")

    seats = (
        db.query(Seat)
        .filter(Seat.taxi_id == taxi.id)
        .order_by(Seat.seat_number)
        .all()
    )

    seat_map = {seat.seat_number: seat for seat in seats}

    def seat_html(seat_number: int) -> str:
        seat = seat_map.get(seat_number)
        if not seat:
            return '<div class="seat seat-empty"></div>'

        status = seat.status.upper()

        if status == "UNPAID":
            return f"""
            <a class="seat seat-available" href="/rider/taxi/{seat.qr_token.rsplit('-seat-', 1)[0]}/seat/{seat.seat_number}">
                <span class="seat-number">{seat.seat_number}</span>
                <span class="seat-label">Available</span>
            </a>
            """

        if status == "PAID":
            return f"""
            <div class="seat seat-paid">
                <span class="seat-number">{seat.seat_number}</span>
                <span class="seat-label">Paid</span>
            </div>
            """

        if status == "CASH":
            return f"""
            <div class="seat seat-cash">
                <span class="seat-number">{seat.seat_number}</span>
                <span class="seat-label">Cash</span>
            </div>
            """

        return f"""
        <div class="seat seat-pending">
            <span class="seat-number">{seat.seat_number}</span>
            <span class="seat-label">{status.title()}</span>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - Select Your Seat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #060f1a !important;
            min-height: 100vh;
            color: white;
            display: flex;
            justify-content: center;
        }}
        .mobile-shell {{
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
        }}
        .bg-glow {{
            position: absolute;
            top: -60px;
            left: 50%;
            transform: translateX(-50%);
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(26,159,219,0.3) 0%, transparent 70%);
            pointer-events: none;
        }}
        .topbar {{
            padding: 22px 20px 0;
            display: flex;
            align-items: center;
            gap: 14px;
            position: relative;
            z-index: 1;
        }}
        .back {{
            text-decoration: none;
            color: white;
            font-size: 1.8rem;
            line-height: 1;
        }}
        .topbar-title {{
            font-size: 1.3rem;
            font-weight: 800;
            color: white;
        }}
        .hero {{
            padding: 24px 20px 20px;
            position: relative;
            z-index: 1;
        }}
        .hero h1 {{
            font-size: 1.7rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
        }}
        .hero p {{
            color: rgba(255,255,255,0.6);
            font-size: 0.9rem;
            line-height: 1.5;
            margin-bottom: 0;
        }}
        .route-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(26,159,219,0.12);
            border: 1px solid rgba(26,159,219,0.22);
            border-radius: 999px;
            padding: 7px 14px;
            font-size: 0.82rem;
            font-weight: 700;
            color: #6dd5fa;
            margin-bottom: 14px;
        }}
        .route-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4ac96b;
            box-shadow: 0 0 6px rgba(74,201,107,0.6);
            animation: pulse 2s infinite;
        }}
        .route-sep {{ opacity: 0.4; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        .panel {{
            background: #060f1a;
            border-radius: 28px 28px 0 0;
            flex: 1;
            padding: 20px 16px 32px;
            border-top: 1px solid rgba(255,255,255,0.06);
            position: relative;
            z-index: 1;
        }}
        .quantum {{
            background: linear-gradient(180deg, #0d1f2e 0%, #0a1825 100%);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 28px;
            padding: 12px 12px 16px;
            position: relative;
            margin: 0 auto 20px;
            max-width: 300px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
        }}
        .quantum-handle {{
            width: 32%;
            height: 4px;
            background: rgba(255,255,255,0.15);
            border-radius: 999px;
            margin: 0 auto 14px;
        }}
        .quantum-inner {{
            margin-top: 0;
            padding: 0;
        }}
        .driver-row {{
            display: grid;
            grid-template-columns: 1fr 0.6fr 1fr;
            gap: 8px;
            align-items: center;
            margin-bottom: 10px;
        }}
        .driver-box {{
            height: 68px;
            border-radius: 16px;
            background: linear-gradient(135deg, #6C5CE7, #4834d4);
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 700;
            box-shadow: 0 6px 16px rgba(108,92,231,0.35);
        }}
        .driver-box span {{ font-size: 1.3rem; margin-bottom: 4px; }}
        .aisle-label {{
            text-align: center;
            color: rgba(255,255,255,0.3);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .row-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }}
        .row-back {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 4px;
        }}
        .row-divider {{
            height: 1px;
            background: rgba(255,255,255,0.06);
            margin: 6px 0;
        }}
        .seat {{
            height: 68px;
            border-radius: 16px;
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            border: 1px solid rgba(255,255,255,0.08);
            transition: transform 0.12s, box-shadow 0.12s;
        }}
        .seat:active {{ transform: scale(0.96); }}
        .seat-number {{ font-size: 1.3rem; line-height: 1; }}
        .seat-label {{ margin-top: 5px; font-size: 0.7rem; font-weight: 700; opacity: 0.9; }}
        .seat-available {{
            background: linear-gradient(135deg, #4ac96b, #27AE60);
            color: white;
            box-shadow: 0 8px 20px rgba(39,174,96,0.4);
            border-color: rgba(74,201,107,0.3);
            animation: glow 2.5s ease-in-out infinite alternate;
        }}
        @keyframes glow {{
            from {{ box-shadow: 0 8px 18px rgba(39,174,96,0.3); }}
            to {{ box-shadow: 0 8px 28px rgba(39,174,96,0.55); }}
        }}
        .seat-paid {{
            background: rgba(231,76,60,0.2);
            border-color: rgba(231,76,60,0.3);
            color: #f16b63;
        }}
        .seat-cash {{
            background: rgba(244,197,66,0.2);
            border-color: rgba(244,197,66,0.3);
            color: #F4C542;
        }}
        .seat-pending {{
            background: rgba(26,159,219,0.15);
            border-color: rgba(26,159,219,0.25);
            color: #6dd5fa;
        }}
        .seat-empty {{ visibility: hidden; }}
        .legend {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin: 4px auto 0;
            max-width: 320px;
        }}
        .legend-item {{
            background: rgba(26,159,219,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 10px 12px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: rgba(255,255,255,0.6);
            font-size: 0.82rem;
            font-weight: 700;
        }}
        .legend-dot {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            flex-shrink: 0;
        }}
        .dot-available {{ background: #27AE60; }}
        .dot-paid {{ background: #E74C3C; }}
        .dot-cash {{ background: #F4C542; }}
        .dot-pending {{ background: #1A9FDB; }}
        .helper {{
            margin-top: 14px;
            text-align: center;
            color: rgba(255,255,255,0.35);
            font-size: 0.82rem;
            letter-spacing: 0.01em;
            max-width: 320px;
            margin-left: auto;
            margin-right: auto;
        }}
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
        }}

        .app {{
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }}

        .mobile-shell {{
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        .topbar {{
            padding: 20px 16px 18px;
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 800;
            font-size: 1.55rem;
        }}

        .back {{
            text-decoration: none;
            color: white;
            font-size: 1.8rem;
            line-height: 1;
        }}

        .content {{
            flex: 1;
            padding: 0 12px 20px;
        }}

        .panel {{
            background: #060f1a;
            border-radius: 28px 28px 0 0;
            flex: 1;
            padding: 20px 16px 32px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }}

        .title {{
            margin: 0;
            color: #0B3C5D;
            font-size: 1.5rem;
            font-weight: 800;
            text-align: center;
        }}

        .subtitle {{
            margin: 8px 0 16px;
            text-align: center;
            color: #667f90;
            font-size: 0.96rem;
            line-height: 1.4;
        }}

        .meta {{
            display: flex;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }}

        .chip {{
            background: #EAF5FC;
            color: #0B3C5D;
            border: 1px solid #D6E9F5;
            padding: 7px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
        }}

        .quantum {{
            background: linear-gradient(180deg, #1D3144 0%, #243D52 100%);
            border-radius: 32px;
            padding: 18px 10px 14px;
            position: relative;
            margin: 8px auto 18px;
            max-width: 320px;
            box-shadow: inset 0 0 0 6px #e9eef2, 0 14px 24px rgba(11,60,93,0.15);
        }}

        .quantum::before {{
            content: "";
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            width: 62%;
            height: 10px;
            background: rgba(255,255,255,0.25);
            border-radius: 999px;
        }}

        .driver-row {{
            display: grid;
            grid-template-columns: 1fr 0.6fr 1fr;
            gap: 8px;
            align-items: center;
            margin-bottom: 10px;
        }}

        .driver-box {{
            height: 64px;
            border-radius: 16px;
            background: linear-gradient(135deg, #6C5CE7, #4834d4);
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 0.78rem;
            font-weight: 700;
            box-shadow: 0 6px 16px rgba(108,92,231,0.35);
        }}

        .aisle-label {{
            text-align: center;
            color: rgba(255,255,255,0.3);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        .row-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }}

        .row-back {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 4px;
        }}

        .seat {{
            min-height: 68px;
            border-radius: 18px;
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            box-shadow: 0 8px 14px rgba(0,0,0,0.18);
            border: 2px solid rgba(255,255,255,0.18);
        }}

        .seat-number {{
            font-size: 1.3rem;
            line-height: 1;
        }}

        .seat-label {{
            margin-top: 6px;
            font-size: 0.72rem;
            font-weight: 700;
            opacity: 0.96;
        }}

        .seat-available {{
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
            color: white;
        }}

        .seat-paid {{
            background: linear-gradient(180deg, #f16b63 0%, #E74C3C 100%);
            color: white;
        }}

        .seat-cash {{
            background: linear-gradient(180deg, #f7d56b 0%, #F4C542 100%);
            color: #4a3b00;
        }}

        .seat-pending {{
            background: linear-gradient(180deg, #8fbff0 0%, #6da8e6 100%);
            color: white;
        }}

        .seat-empty {{
            visibility: hidden;
        }}

        .legend {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 16px;
        }}

        .legend-item {{
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 16px;
            padding: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #4f6778;
            font-size: 0.88rem;
            font-weight: 700;
        }}

        .legend-dot {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .dot-available {{ background: #27AE60; }}
        .dot-paid {{ background: #E74C3C; }}
        .dot-cash {{ background: #F4C542; }}
        .dot-pending {{ background: #6da8e6; }}

        .helper {{
            margin-top: 16px;
            text-align: center;
            color: #73899a;
            font-size: 0.86rem;
        }}

        @media (max-width: 520px) {{
            .topbar {{
                padding: 18px 14px 16px;
                font-size: 1.4rem;
            }}

            .panel {{
                padding: 16px 12px 22px;
            }}

            .quantum {{
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
<div class="mobile-shell">
    <div class="bg-glow"></div>
    <div class="topbar">
        <a href="/" class="back">‹</a>
        <span class="topbar-title">Select Your Seat</span>
    </div>
    <div class="hero">
        <div class="route-pill">
            <span class="route-dot"></span>
            <span>{taxi.route_name}</span>
            <span class="route-sep">·</span>
            <span>{taxi.vehicle_code}</span>
        </div>
        <h1>Pick your seat</h1>
        <p>Tap a seat below to pay instantly.</p>
    </div>
    <div class="panel">

        <div class="quantum">
            <div class="driver-row">
                <div class="driver-box">
                    <span>🧑🏽‍✈️</span>
                    <div>Driver</div>
                </div>
                <div class="aisle-label">Aisle</div>
                {seat_html(1)}
            </div>
            <div class="row-divider"></div>
            <div class="row-3">
                {seat_html(2)}
                {seat_html(3)}
                {seat_html(4)}
            </div>
            <div class="row-3">
                {seat_html(5)}
                {seat_html(6)}
                {seat_html(7)}
            </div>
            <div class="row-3">
                {seat_html(8)}
                {seat_html(9)}
                {seat_html(10)}
            </div>
            <div class="row-3">
                {seat_html(11)}
                {seat_html(12)}
                {seat_html(13)}
            </div>
            <div class="row-divider"></div>
            <div class="row-back">
                {seat_html(12)}
                {seat_html(13)}
                {seat_html(14)}
                {seat_html(15)}
            </div>
        </div>
        <div class="legend">
            <div class="legend-item"><span class="legend-dot dot-available"></span><span>Available</span></div>
            <div class="legend-item"><span class="legend-dot dot-paid"></span><span>Digital</span></div>
            <div class="legend-item"><span class="legend-dot dot-cash"></span><span>Cash</span></div>
            <div class="legend-item"><span class="legend-dot dot-pending"></span><span>Pending</span></div>
        </div>
        <div class="helper">🟢 Tap any green seat to pay</div>
    </div>
</div>
</body>
</html>
"""
@router.get("/scan", response_class=HTMLResponse)
def scan_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - Scan</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://unpkg.com/html5-qrcode"></script>

    const content = document.getElementById("summaryContent");

    content.innerHTML = ""
        + "<div><strong>Total Seats:</strong> " + data.total_seats + "</div>"
        + "<div><strong>Paid:</strong> " + data.paid_count + "</div>"
        + "<div><strong>Cash:</strong> " + data.cash_count + "</div>"
        + "<div><strong>Open:</strong> " + data.open_count + "</div>"
        + "<div><strong>Fare:</strong> R" + data.fare.toFixed(2) + "</div>"
        + "<div><strong>Online:</strong> R" + data.online_revenue.toFixed(2) + "</div>"
        + "<div><strong>Cash Revenue:</strong> R" + data.cash_revenue.toFixed(2) + "</div>"
        + "<div><strong>Total:</strong> R" + data.total_revenue.toFixed(2) + "</div>"
        + "<div><strong>Occupancy:</strong> " + data.occupancy_percent + "%</div>";

    document.getElementById("summaryModal").style.display = "flex";
}}

</script>
</body>
</html>
"""
@router.get("/rider/taxi/{taxi_id}/seat/{seat_number}", response_class=HTMLResponse)
def rider_page_by_seat(taxi_id: str, seat_number: int, db: Session = Depends(get_db)):
    qr_token = f"{taxi_id}-seat-{seat_number}"
    seat = db.query(Seat).filter(Seat.qr_token == qr_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    return rider_page(taxi_id, seat_number, db)

@router.get("/rider/{qr_token}")
def rider_redirect(qr_token: str, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.qr_token == qr_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="QR token not found")

    taxi_code = qr_token.rsplit("-seat-", 1)[0]
    return RedirectResponse(url=f"/rider/taxi/{taxi_code}/seat/{seat.seat_number}", status_code=307)

@router.get("/rider/taxi/{taxi_id}/seat/{seat_number}/view", response_class=HTMLResponse)
def rider_page(taxi_id: str, seat_number: int, db: Session = Depends(get_db)):
    qr_token = f"{taxi_id}-seat-{seat_number}"
    seat = db.query(Seat).filter(Seat.qr_token == qr_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="QR token not found")

    taxi = db.query(Taxi).filter(Taxi.id == seat.taxi_id).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi not found")

    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE")
        .first()
    )

    trip_id = active_trip.id if active_trip else ""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - Pay for Your Ride</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
        }}

        .app {{
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }}

        .mobile-shell {{
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        .topbar {{
            padding: 20px 16px 18px;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 800;
            font-size: 1.55rem;
        }}

        .top-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .back {{
            text-decoration: none;
            color: white;
            font-size: 1.8rem;
            line-height: 1;
        }}

        .shield {{
            font-size: 1.2rem;
            opacity: 0.95;
        }}

        .content {{
            flex: 1;
            padding: 0 12px 20px;
        }}

        .panel {{
            background: transparent;
            border-radius: 0;
            padding: 0;
            box-shadow: none;
        }}

        .hero {{
            background: #F4F8FC;
            border-radius: 24px;
            padding: 18px 16px;
            box-shadow: inset 0 0 0 1px #E3EDF5;
        }}

        .seat-line {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
        }}

        .seat-title {{
            margin: 0;
            font-size: 1.15rem;
            color: #0B3C5D;
            font-weight: 800;
        }}

        .seat-number-badge {{
            width: 54px;
            height: 54px;
            border-radius: 18px;
            background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
            font-weight: 800;
            box-shadow: 0 10px 18px rgba(26,159,219,0.22);
        }}

        .subline {{
            margin: 0;
            color: #6A8191;
            font-size: 0.98rem;
        }}

        .fare-card {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }}

        .metric-title {{
            color: #647c8e;
            font-size: 0.9rem;
            margin-bottom: 6px;
        }}

        .fare-value {{
            color: #1A9FDB;
            font-weight: 800;
            font-size: 2rem;
        }}

        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 999px;
            background: #EAF8EF;
            color: #27AE60;
            font-weight: 800;
            font-size: 0.98rem;
        }}

        .status-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #27AE60;
        }}

        .section-title {{
            margin: 22px 0 12px;
            color: #0B3C5D;
            font-size: 1.05rem;
            font-weight: 800;
        }}

        .payment-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 4px;
        }}

        .pay-option {{
            background: white;
            border: 2px solid #E3EEF6;
            border-radius: 20px;
            padding: 16px 14px;
            display: flex;
            align-items: center;
            gap: 14px;
            cursor: pointer;
            transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
            box-shadow: 0 4px 12px rgba(11,60,93,0.05);
        }}

        .pay-option:active {{
            transform: scale(0.98);
        }}

        .pay-option-icon {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            flex-shrink: 0;
        }}

        .pay-option-text strong {{
            display: block;
            font-size: 0.98rem;
            color: #0B3C5D;
            font-weight: 800;
        }}

        .pay-option-text span {{
            font-size: 0.8rem;
            color: #7a96a8;
            font-weight: 600;
        }}

        .active-method {{
            border-color: #1A9FDB !important;
            background: #EEF8FF !important;
            box-shadow: 0 6px 18px rgba(26,159,219,0.14) !important;
        }}

        .active-method .pay-option-text strong {{
            color: #0B72C6;
        }}

        .qr-box {{
            margin-top: 16px;
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 22px;
            padding: 18px 16px;
            text-align: center;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}

        .qr-frame {{
            width: 180px;
            height: 180px;
            margin: 0 auto 14px;
            border-radius: 20px;
            border: 2px dashed #8cc3ef;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #FBFDFF;
            color: #7aaed8;
            font-weight: 800;
        }}

        .qr-label {{
            color: #5d7587;
            font-size: 0.95rem;
            font-weight: 700;
        }}

        .pay-btn {{
            margin-top: 20px;
            width: 100%;
            border: none;
            border-radius: 18px;
            padding: 18px 20px;
            background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
            color: white;
            font-size: 1.35rem;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 14px 24px rgba(26,159,219,0.26);
        }}
       
        .pay-wrap {{
            margin-top: 20px;
        }}

        .pay-btn {{
            width: 100%;
            border: none;
            border-radius: 22px;
            padding: 18px 20px;
            background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
            color: white;
            font-size: 1.2rem;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 14px 24px rgba(26,159,219,0.26);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
        }}

        .pay-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 16px 28px rgba(26,159,219,0.30);
        }}

        .pay-btn:active {{
            transform: scale(0.99);
        }}

        .pay-btn.processing {{
            opacity: 0.88;
            pointer-events: none;
        }}

        .pay-arrow {{
            font-size: 1.3rem;
            line-height: 1;
        }}

        .pay-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}

        .secure {{
            margin-top: 14px;
            text-align: center;
            color: #687f91;
            font-size: 0.92rem;
            font-weight: 700;
        }}

        .err {{
            margin-top: 14px;
            color: #C0392B;
            font-weight: 700;
            text-align: center;
        }}

        @media (max-width: 520px) {{
            .topbar {{
                padding: 18px 14px 16px;
                font-size: 1.35rem;
            }}

            .panel {{
                padding: 16px 12px 22px;
            }}

            .fare-value {{
                font-size: 1.7rem;
            }}

            .payment-grid {{
                grid-template-columns: 1fr 1fr;
            }}
        }}

        .bg-glow {{
            position: fixed;
            top: -80px;
            left: 50%;
            transform: translateX(-50%);
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(26,159,219,0.2) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }}
        .topbar-title {{
            font-size: 1.1rem;
            font-weight: 800;
            color: white;
        }}
        .seat-hero {{
            background: linear-gradient(135deg, #0d1f2e, #0a1825);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 20px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }}
        .seat-title {{
            font-size: 1.25rem;
            font-weight: 800;
            color: white;
            margin-bottom: 5px;
        }}
        .seat-sub {{
            color: rgba(255,255,255,0.45);
            font-size: 0.85rem;
        }}
        .seat-badge {{
            width: 60px;
            height: 60px;
            border-radius: 18px;
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            font-weight: 800;
            box-shadow: 0 10px 24px rgba(26,159,219,0.4);
            flex-shrink: 0;
        }}
        .fare-item {{
            background: linear-gradient(135deg, #0d1f2e, #0a1825);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 18px;
        }}
        .fare-label {{
            color: rgba(255,255,255,0.4);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
<div class="app">
<div class="mobile-shell">
    <div class="bg-glow"></div>
    <div class="topbar">
        <div class="top-left">
            <a href="/master/tx100-master" class="back">‹</a>
            <span class="topbar-title">Pay for Your Ride</span>
        </div>
        <span class="shield">🛡️</span>
    </div>
    <div class="content" style="padding:20px 18px 32px;position:relative;z-index:1;">
        <div class="seat-hero">
            <div>
                <div class="seat-title">Seat {seat.seat_number} Selected</div>
                <div class="seat-sub">{taxi.route_name or "Route"} · {taxi.vehicle_code}</div>
            </div>
            <div class="seat-badge">{seat.seat_number}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
            <div class="fare-item">
                <div class="fare-label">Fare</div>
                <div class="fare-value">R{(active_trip.fare_amount if active_trip else 0):.2f}</div>
            </div>
            <div class="fare-item">
                <div class="fare-label">Status</div>
                <div class="status-pill">
                    <span class="status-dot"></span>
                    <span>{seat.status.title()}</span>
                </div>
            </div>
        </div>
        <div class="section-title" style="color:rgba(255,255,255,0.45);font-size:0.75rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">Choose Payment Method</div>
                    <div class="payment-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">
                        <div id="method-apple" class="pay-option" onclick="selectPaymentMethod('apple')">
                            <div class="pay-option-icon" style="background:rgba(255,255,255,0.08);">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.7 9.05 7.4c1.27.07 2.15.75 2.88.8.97-.17 1.9-.87 3.23-.94 1.72.09 3.02.77 3.86 2.01-3.54 2.13-2.95 6.82.59 8.14-.7 1.92-1.6 3.82-2.56 4.87zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" fill="#1a1a1a"/></svg>
                            </div>
                            <div class="pay-option-text">
                                <strong>Apple Pay</strong>
                                <span>Touch ID / Face ID</span>
                            </div>
                        </div>
                        <div id="method-google" class="pay-option" onclick="selectPaymentMethod('google')">
                            <div class="pay-option-icon" style="background:rgba(66,133,244,0.1);">
                                <svg width="24" height="24" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                            </div>
                            <div class="pay-option-text">
                                <strong>Google Pay</strong>
                                <span>Pay with Google</span>
                            </div>
                        </div>
                        <div id="method-card" class="pay-option active-method" onclick="selectPaymentMethod('card')">
                            <div class="pay-option-icon" style="background:#eef4ff;">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="14" rx="3" stroke="#1A9FDB" stroke-width="2"/><path d="M2 10h20" stroke="#1A9FDB" stroke-width="2"/><rect x="5" y="14" width="4" height="2" rx="1" fill="#1A9FDB"/></svg>
                            </div>
                            <div class="pay-option-text">
                                <strong>Bank Card</strong>
                                <span>Visa / Mastercard</span>
                            </div>
                        </div>
                        <div id="method-snapscan" class="pay-option" onclick="selectPaymentMethod('snapscan')">
                            <div class="pay-option-icon" style="background:#f0faf4;">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="7" rx="1.5" stroke="#27AE60" stroke-width="2"/><rect x="14" y="3" width="7" height="7" rx="1.5" stroke="#27AE60" stroke-width="2"/><rect x="3" y="14" width="7" height="7" rx="1.5" stroke="#27AE60" stroke-width="2"/><rect x="5" y="5" width="3" height="3" fill="#27AE60"/><rect x="16" y="5" width="3" height="3" fill="#27AE60"/><rect x="5" y="16" width="3" height="3" fill="#27AE60"/><path d="M14 14h3v3h-3zM17 17h3v3h-3zM14 17h3" stroke="#27AE60" stroke-width="1.5"/></svg>
                            </div>
                            <div class="pay-option-text">
                                <strong>Scan to Pay</strong>
                                <span>SnapScan / QR</span>
                            </div>
                        </div>
                        <div id="method-cash" class="pay-option" onclick="selectPaymentMethod('cash')" style="grid-column:1/-1;">
                            <div class="pay-option-icon" style="background:rgba(244,197,66,0.15);">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="2" y="6" width="20" height="12" rx="3" stroke="#F4C542" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="#F4C542" stroke-width="2"/><path d="M6 12h.01M18 12h.01" stroke="#F4C542" stroke-width="2" stroke-linecap="round"/></svg>
                            </div>
                            <div class="pay-option-text">
                                <strong>Cash to Driver</strong>
                                <span>Pay driver directly · they will confirm</span>
                            </div>
                        </div>
                    </div>

                    <div id="qr-box-wrap" style="display:none;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:24px;padding:18px;margin-bottom:16px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
                            <div style="font-size:1rem;font-weight:800;color:white;">SnapScan</div>
                            <div style="font-size:0.78rem;font-weight:800;color:#6dd5fa;background:rgba(26,159,219,0.12);border:1px solid rgba(26,159,219,0.2);padding:5px 10px;border-radius:999px;">Scan to pay</div>
                        </div>
                        <div onclick="openScanner()" style="cursor:pointer;min-height:180px;border:2px dashed rgba(26,159,219,0.3);border-radius:20px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:rgba(255,255,255,0.3);font-weight:800;">
                            <div style="font-size:2rem;margin-bottom:10px;">📱</div>
                            <div style="font-size:1rem;">Tap to scan QR</div>
                            <div style="font-size:0.8rem;margin-top:6px;opacity:0.6;">Use your camera</div>
                        </div>
                        <input id="camera-input" type="file" accept="image/*" capture="environment" style="display:none;">
                    </div>

<div id="cash-notice" style="display:none;background:rgba(244,197,66,0.1);border:1px solid rgba(244,197,66,0.25);border-radius:20px;padding:18px;margin-bottom:16px;text-align:center;">
    <div style="font-size:2rem;margin-bottom:10px;">💵</div>
    <div style="font-weight:800;font-size:1rem;color:#F4C542;margin-bottom:6px;">Pay R{(active_trip.fare_amount if active_trip else 0):.2f} to the driver</div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.85rem;margin-bottom:14px;">Hand your cash to the driver. They will mark your seat as paid.</div>
    <button onclick="notifyDriver()" style="width:100%;padding:14px;border:none;border-radius:14px;background:linear-gradient(135deg,#F4C542,#e6b800);color:#1a1200;font-weight:800;font-size:1rem;cursor:pointer;">
        Notify Driver →
    </button>
    <div id="cash-sent" style="display:none;margin-top:12px;color:#4ac96b;font-weight:800;">✓ Driver notified! Hand over your cash.</div>
</div>

<div class="pay-wrap">
    <button id="pay-btn" class="pay-btn" onclick="payNow()">
        <span id="pay-btn-text">Pay with PayFast</span>
        <span class="pay-arrow">→</span>
    </button>
</div>
                    <div id="result"></div>

                    <div class="secure" style="color:rgba(255,255,255,0.3);">🔒 Secure &amp; instant payment</div>
                </div>
            </div>
        </div>
    </div>

<script>

let selectedMethod = "card";

function setMethodStyles() {{
    const methods = ["apple", "google", "card", "snapscan"];
    methods.forEach(m => {{
        const el = document.getElementById("method-" + m);
        if (!el) return;
        el.classList.remove("active-method");
        el.style.border = "2px solid rgba(255,255,255,0.07)";
        el.style.background = "rgba(255,255,255,0.04)";
    }});

    const active = document.getElementById("method-" + selectedMethod);
    if (active) {{
        active.classList.add("active-method");
        active.style.border = "2px solid #1A9FDB";
        active.style.background = "rgba(26,159,219,0.12)";
    }}
}}

function selectPaymentMethod(method) {{
    selectedMethod = method;

    const qrBox = document.getElementById("qr-box-wrap");
    const btnText = document.getElementById("pay-btn-text");

    const labels = {{
        apple: "Pay with Apple Pay",
        google: "Pay with Google Pay",
        card: "Pay with Bank Card",
        snapscan: "Pay with SnapScan"
    }};

    btnText.textContent = labels[method] || "Pay Now";

    const cashNotice = document.getElementById("cash-notice");
    const payWrap = document.querySelector(".pay-wrap");

    if (method === "snapscan") {{
        qrBox.style.display = "block";
        cashNotice.style.display = "none";
        payWrap.style.display = "block";
    }} else if (method === "cash") {{
        qrBox.style.display = "none";
        cashNotice.style.display = "block";
        payWrap.style.display = "none";
    }} else {{
        qrBox.style.display = "none";
        cashNotice.style.display = "none";
        payWrap.style.display = "block";
    }}

    setMethodStyles();
}}

function openScanner() {{
    const input = document.getElementById("camera-input");
    if (input) input.click();
}}

document.addEventListener("DOMContentLoaded", function () {{
    selectPaymentMethod("card");
}});

async function notifyDriver() {{
    const btn = document.querySelector("#cash-notice button");
    if (btn) {{ btn.disabled = true; btn.textContent = "Notifying..."; }}

    try {{
        await fetch("/seats/{seat.id}/cash-intent", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }}
        }});
    }} catch(e) {{
        console.log("notify error", e);
    }}

    document.getElementById("cash-sent").style.display = "block";
    if (btn) {{ btn.style.display = "none"; }}
}}

function toggleChat() {{
    const modal = document.getElementById("chatModal");
    modal.style.display = modal.style.display === "none" ? "block" : "none";
    if (modal.style.display === "block") {{
        setTimeout(() => document.getElementById("chatInput").focus(), 100);
    }}
}}

async function sendChat() {{
    const input = document.getElementById("chatInput");
    const question = input.value.trim();
    if (!question) return;
    
    const messages = document.getElementById("chatMessages");
    
    // Add user message
    messages.innerHTML += `<div style="background:rgba(255,255,255,0.08);border-radius:14px;padding:10px 12px;color:white;font-size:0.88rem;align-self:flex-end;max-width:85%;">${{question}}</div>`;
    input.value = "";
    messages.scrollTop = messages.scrollHeight;
    
    // Show typing indicator
    const typingId = "typing_" + Date.now();
    messages.innerHTML += `<div id="${{typingId}}" style="background:rgba(26,159,219,0.12);border-radius:14px;padding:10px 12px;color:rgba(255,255,255,0.6);font-size:0.88rem;">typing...</div>`;
    messages.scrollTop = messages.scrollHeight;
    
    try {{
        const res = await fetch("/chat", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{
                question: question,
                route: "{taxi.route_name if taxi else ''}",
                fare: "{active_trip.fare_amount if active_trip else 0}"
            }})
        }});
        const data = await res.json();
        document.getElementById(typingId).remove();
        messages.innerHTML += `<div style="background:rgba(26,159,219,0.12);border-radius:14px;padding:10px 12px;color:rgba(255,255,255,0.85);font-size:0.88rem;">${{data.answer}}</div>`;
    }} catch(e) {{
        document.getElementById(typingId).remove();
        messages.innerHTML += `<div style="background:rgba(231,76,60,0.12);border-radius:14px;padding:10px 12px;color:#f16b63;font-size:0.88rem;">Sorry, I couldn't connect. Try again.</div>`;
    }}
    messages.scrollTop = messages.scrollHeight;
}}

function payNow() {{
    if (!"{trip_id}") {{
        document.getElementById("result").innerHTML =
            '<div class="err">No active trip found for this taxi.</div>';
        return;
    }}
    if (selectedMethod === "apple") {{ showApplePaySheet(); return; }}
    if (selectedMethod === "google") {{ showGooglePaySheet(); return; }}
    const payBtn = document.getElementById("pay-btn");
    const payBtnText = document.getElementById("pay-btn-text");
    payBtn.classList.add("processing");
    payBtnText.textContent = "Processing...";
    if (selectedMethod === "snapscan") {{
        window.location.href = "/payments/snapscan/start?trip_id={trip_id}&seat_id={seat.id}";
        return;
    }}
    window.location.href = "/payments/payfast/start?trip_id={trip_id}&seat_id={seat.id}";
}}

function showApplePaySheet() {{
    const sheet = document.getElementById("applePaySheet");
    sheet.style.display = "flex";
    setTimeout(() => sheet.querySelector(".ap-sheet").style.transform = "translateY(0)", 10);
}}

function showGooglePaySheet() {{
    const sheet = document.getElementById("googlePaySheet");
    sheet.style.display = "flex";
    setTimeout(() => sheet.querySelector(".gp-sheet").style.transform = "translateY(0)", 10);
}}

function closePaySheet(id) {{
    const sheet = document.getElementById(id);
    const inner = sheet.querySelector(".ap-sheet, .gp-sheet");
    if (inner) inner.style.transform = "translateY(100%)";
    setTimeout(() => sheet.style.display = "none", 300);
}}

async function processDemoPayment(method) {{
    closePaySheet(method === "apple" ? "applePaySheet" : "googlePaySheet");
    document.getElementById("demoProcessing").style.display = "flex";
    await new Promise(r => setTimeout(r, 2000));
    try {{
        await fetch("/payments/demo/confirm?trip_id={trip_id}&seat_id={seat.id}&method=" + method);
        document.getElementById("demoProcessing").style.display = "none";
        document.getElementById("demoSuccess").style.display = "flex";
        setTimeout(() => window.location.href = "/rider/dashboard/{seat.id}", 2000);
    }} catch(e) {{
        document.getElementById("demoProcessing").style.display = "none";
        alert("Payment failed. Try again.");
    }}
}}
</script>

<!-- Apple Pay Sheet -->
<div id="applePaySheet" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;align-items:flex-end;justify-content:center;">
    <div class="ap-sheet" style="width:100%;max-width:430px;background:#1c1c1e;border-radius:20px 20px 0 0;padding:0 0 40px;transform:translateY(100%);transition:transform 0.3s ease;">
        <div style="width:40px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;margin:12px auto;"></div>
        <div style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.7 9.05 7.4c1.27.07 2.15.75 2.88.8.97-.17 1.9-.87 3.23-.94 1.72.09 3.02.77 3.86 2.01-3.54 2.13-2.95 6.82.59 8.14-.7 1.92-1.6 3.82-2.56 4.87zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/></svg>
                <span style="color:white;font-size:1.1rem;font-weight:700;">Apple Pay</span>
            </div>
            <div style="color:rgba(255,255,255,0.5);font-size:0.85rem;">FareFlow · Seat {seat.seat_number}</div>
        </div>
        <div style="padding:20px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="color:rgba(255,255,255,0.6);">Fare</span>
                <span style="color:white;font-weight:700;">R{(active_trip.fare_amount if active_trip else 0):.2f}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:20px;">
                <span style="color:rgba(255,255,255,0.6);">Route</span>
                <span style="color:white;font-weight:700;">{taxi.route_name if taxi else ""}</span>
            </div>
            <button onclick="processDemoPayment('apple')" style="width:100%;padding:16px;border:none;border-radius:14px;background:white;color:black;font-size:1rem;font-weight:800;cursor:pointer;">
                Pay
            </button>
            <button onclick="closePaySheet('applePaySheet')" style="width:100%;padding:14px;border:none;border-radius:14px;background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.6);font-size:0.95rem;font-weight:700;cursor:pointer;margin-top:10px;">
                Cancel
            </button>
        </div>
    </div>
</div>

<!-- Google Pay Sheet -->
<div id="googlePaySheet" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;align-items:flex-end;justify-content:center;">
    <div class="gp-sheet" style="width:100%;max-width:430px;background:#202124;border-radius:20px 20px 0 0;padding:0 0 40px;transform:translateY(100%);transition:transform 0.3s ease;">
        <div style="width:40px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;margin:12px auto;"></div>
        <div style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                <svg width="24" height="24" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                <span style="color:white;font-size:1.1rem;font-weight:700;">Google Pay</span>
            </div>
            <div style="color:rgba(255,255,255,0.5);font-size:0.85rem;">FareFlow · Seat {seat.seat_number}</div>
        </div>
        <div style="padding:20px;">
            <div style="background:#2d2e31;border-radius:14px;padding:16px;margin-bottom:16px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                    <span style="color:rgba(255,255,255,0.6);font-size:0.88rem;">Total</span>
                    <span style="color:white;font-weight:800;font-size:1.1rem;">R{(active_trip.fare_amount if active_trip else 0):.2f}</span>
                </div>
                <div style="display:flex;align-items:center;gap:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);">
                    <div style="width:32px;height:20px;background:#1a1a2e;border-radius:4px;border:1px solid rgba(255,255,255,0.2);"></div>
                    <div>
                        <div style="color:white;font-size:0.85rem;font-weight:700;">Visa ···· 4242</div>
                        <div style="color:rgba(255,255,255,0.4);font-size:0.75rem;">Default card</div>
                    </div>
                </div>
            </div>
            <button onclick="processDemoPayment('google')" style="width:100%;padding:16px;border:none;border-radius:14px;background:#4285F4;color:white;font-size:1rem;font-weight:800;cursor:pointer;">
                Pay R{(active_trip.fare_amount if active_trip else 0):.2f}
            </button>
            <button onclick="closePaySheet('googlePaySheet')" style="width:100%;padding:14px;border:none;border-radius:14px;background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.6);font-size:0.95rem;font-weight:700;cursor:pointer;margin-top:10px;">
                Cancel
            </button>
        </div>
    </div>
</div>

<!-- Processing -->
<div id="demoProcessing" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.88);z-index:9999;align-items:center;justify-content:center;flex-direction:column;gap:16px;">
    <div style="width:56px;height:56px;border:4px solid rgba(255,255,255,0.1);border-top:4px solid #1A9FDB;border-radius:50%;animation:spin2 0.8s linear infinite;"></div>
    <div style="color:white;font-weight:800;">Processing payment...</div>
    <style>@keyframes spin2 {{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}</style>
</div>

<!-- Success -->
<div id="demoSuccess" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.88);z-index:9999;align-items:center;justify-content:center;flex-direction:column;gap:14px;">
    <div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#4ac96b,#27AE60);display:flex;align-items:center;justify-content:center;font-size:2.5rem;box-shadow:0 12px 32px rgba(39,174,96,0.4);">✓</div>
    <div style="color:white;font-weight:800;font-size:1.3rem;">Payment Successful!</div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.9rem;">Redirecting to your trip...</div>
</div>
<!-- AI Chatbot -->
<button id="chatBtn" onclick="toggleChat()" style="position:fixed;bottom:24px;right:20px;width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#1A9FDB,#0B72C6);border:none;color:white;font-size:1.4rem;cursor:pointer;box-shadow:0 8px 24px rgba(26,159,219,0.4);z-index:998;transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">💬</button>

<div id="chatModal" style="display:none;position:fixed;bottom:90px;right:16px;width:calc(100% - 32px);max-width:360px;background:#0d1f2e;border:1px solid rgba(255,255,255,0.1);border-radius:24px;box-shadow:0 20px 40px rgba(0,0,0,0.5);z-index:997;overflow:hidden;">
    <div style="padding:16px 18px;border-bottom:1px solid rgba(255,255,255,0.08);display:flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;border-radius:12px;background:linear-gradient(135deg,#1A9FDB,#0B72C6);display:flex;align-items:center;justify-content:center;font-size:1.1rem;">🤖</div>
        <div>
            <div style="font-weight:800;color:white;font-size:0.95rem;">FareFlow Assistant</div>
            <div style="color:rgba(255,255,255,0.45);font-size:0.78rem;">Ask me anything</div>
        </div>
        <button onclick="toggleChat()" style="margin-left:auto;border:none;background:rgba(255,255,255,0.08);color:white;border-radius:8px;padding:4px 10px;cursor:pointer;">✕</button>
    </div>
    <div id="chatMessages" style="height:240px;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;">
        <div style="background:rgba(26,159,219,0.12);border-radius:14px;padding:12px;color:rgba(255,255,255,0.85);font-size:0.88rem;">
            👋 Hi! I'm your FareFlow assistant. Ask me how to pay, about your route, or anything else!
        </div>
    </div>
    <div style="padding:12px;border-top:1px solid rgba(255,255,255,0.08);display:flex;gap:8px;">
        <input id="chatInput" type="text" placeholder="Ask me anything..." 
            style="flex:1;padding:10px 14px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:12px;color:white;font-size:0.9rem;outline:none;font-family:inherit;"
            onkeydown="if(event.key==='Enter') sendChat()">
        <button onclick="sendChat()" style="padding:10px 14px;border:none;border-radius:12px;background:linear-gradient(135deg,#1A9FDB,#0B72C6);color:white;font-weight:800;cursor:pointer;">→</button>
    </div>
</div>

<div id="cashToast" class="toast">💵 Seat <span id="toastSeat"></span> wants to pay cash!</div>

</body>
</html>
"""

@router.get("/rider/dashboard/{seat_id}", response_class=HTMLResponse)
def rider_dashboard(seat_id: str, db: Session = Depends(get_db)):
    from app.models import Payment
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    taxi = db.query(Taxi).filter(Taxi.id == seat.taxi_id).first()
    trip = db.query(Trip).filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE").first()
    payment = db.query(Payment).filter(Payment.seat_id == seat_id).order_by(Payment.created_at.desc()).first()

    from app.route_coords import get_route_coords
    import json as _json
    _coords = get_route_coords(taxi.route_name if taxi else None)
    route_coords_json = _json.dumps(_coords)
    taxi_route = taxi.route_name if taxi else "Unknown"

    status_labels = {
        "SUCCESS_SNAPSCAN_DEMO": "Paid via SnapScan",
            "SUCCESS_APPLE_PAY": "Paid via Apple Pay",
            "SUCCESS_GOOGLE_PAY": "Paid via Google Pay",
        "SUCCESS_SNAPSCAN": "Paid via SnapScan",
        "SUCCESS_PAYFAST": "Paid via Card",
        "SUCCESS_CASH": "Paid in Cash",
    }
    pay_status = status_labels.get(payment.status, payment.status) if payment else "Unpaid"
    pay_amount = ("R" + f"{payment.amount:.2f}") if payment else ("R" + f"{trip.fare_amount:.2f}") if trip else "R0.00"
    trip_id = trip.id if trip else ""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - My Trip</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
            display: flex;
            justify-content: center;
        }}
        .shell {{
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
        }}
        .bg-glow {{
            position: fixed;
            top: -80px;
            left: 50%;
            transform: translateX(-50%);
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(74,201,107,0.15) 0%, transparent 70%);
            pointer-events: none;
        }}
        .topbar {{
            padding: 22px 20px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            z-index: 1;
        }}
        .topbar-left {{ display: flex; align-items: center; gap: 10px; }}
        .topbar-logo {{
            width: 32px; height: 32px; border-radius: 9px;
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            display: flex; align-items: center; justify-content: center; font-size: 1rem;
        }}
        .topbar-name {{ font-size: 1.1rem; font-weight: 800; }}
        .content {{ flex: 1; padding: 20px 18px 32px; position: relative; z-index: 1; }}

        .success-badge {{
            width: 64px; height: 64px; border-radius: 20px;
            background: linear-gradient(135deg, #4ac96b, #27AE60);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.8rem; margin: 0 auto 16px;
            box-shadow: 0 10px 24px rgba(39,174,96,0.35);
        }}
        .hero-title {{
            text-align: center; font-size: 1.4rem; font-weight: 800;
            margin-bottom: 6px;
        }}
        .hero-sub {{
            text-align: center; color: rgba(255,255,255,0.5);
            font-size: 0.88rem; margin-bottom: 24px;
        }}
        .info-grid {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 12px; margin-bottom: 20px;
        }}
        .info-card {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px; padding: 16px;
        }}
        .info-label {{
            color: rgba(255,255,255,0.4); font-size: 0.75rem;
            font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.06em; margin-bottom: 8px;
        }}
        .info-value {{ font-size: 1.2rem; font-weight: 800; color: white; }}
        .info-value.green {{ color: #4ac96b; }}
        .info-value.blue {{ color: #1A9FDB; }}

        .section-title {{
            color: rgba(255,255,255,0.4); font-size: 0.75rem;
            font-weight: 800; text-transform: uppercase;
            letter-spacing: 0.08em; margin-bottom: 12px;
        }}
        .map-container {{
            border-radius: 20px; overflow: hidden;
            height: 220px; margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .dropoff-btn {{
            width: 100%; padding: 15px; border: none;
            border-radius: 18px;
            background: rgba(26,159,219,0.12);
            border: 1px solid rgba(26,159,219,0.25);
            color: #6dd5fa; font-weight: 800;
            font-size: 0.95rem; cursor: pointer;
            margin-bottom: 20px;
        }}
        .dropoff-sent {{
            display: none; margin-bottom: 16px; text-align: center;
            padding: 12px; background: rgba(74,201,107,0.1);
            border: 1px solid rgba(74,201,107,0.25); border-radius: 14px;
        }}
        .btn {{
            display: block; text-decoration: none;
            border-radius: 18px; padding: 15px 18px;
            font-weight: 800; font-size: 1rem; text-align: center;
            margin-bottom: 10px; transition: transform 0.15s;
        }}
        .btn:active {{ transform: scale(0.98); }}
        .btn-primary {{
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            color: white; box-shadow: 0 10px 24px rgba(26,159,219,0.25);
        }}
        .btn-secondary {{
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
        }}

        /* Drop-off modal */
        .dropoff-modal {{
            display: none; position: fixed; inset: 0;
            background: rgba(0,0,0,0.88); z-index: 9999;
            flex-direction: column;
        }}
        .modal-topbar {{
            background: #0d1f2e; padding: 16px 18px;
            display: flex; align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .modal-map {{ flex: 1; width: 100%; }}
        .modal-footer {{
            display: none; background: #0d1f2e; padding: 16px 18px;
            border-top: 1px solid rgba(255,255,255,0.08);
        }}
        .confirm-btn {{
            width: 100%; padding: 14px; border: none;
            border-radius: 14px;
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            color: white; font-weight: 800; font-size: 1rem; cursor: pointer;
        }}
    </style>
</head>
<body>
<div class="shell">
    <div class="bg-glow"></div>
    <div class="topbar">
        <div class="topbar-left">
            <div class="topbar-logo">🚕</div>
            <div class="topbar-name">FareFlow</div>
        </div>
    </div>
    <div class="content">
        <div class="success-badge">✓</div>
        <div class="hero-title">You're on board!</div>
        <div class="hero-sub">{taxi_route} · Taxi {taxi.vehicle_code if taxi else ""}</div>

        <div class="info-grid">
            <div class="info-card">
                <div class="info-label">Your Seat</div>
                <div class="info-value blue">{seat.seat_number}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Fare</div>
                <div class="info-value">{pay_amount}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Payment</div>
                <div class="info-value green" style="font-size:0.9rem;">{pay_status}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Route</div>
                <div class="info-value" style="font-size:0.9rem;">{taxi_route}</div>
            </div>
        </div>

        <div class="section-title">Your Route</div>
        <div class="map-container" id="miniMap"></div>

        <button class="dropoff-btn" onclick="openDropoffModal()">
            📍 Set My Drop-off Stop
        </button>
        <div id="dropoffSentInline" class="dropoff-sent">
            <div style="color:#4ac96b;font-weight:800;">✅ Driver Notified!</div>
            <div id="dropoffAddrInline" style="color:rgba(255,255,255,0.5);font-size:0.82rem;margin-top:4px;"></div>
        </div>

        <a class="btn btn-primary" href="/payments/receipt/{payment.id if payment else ""}">View Receipt</a>
        <a class="btn btn-secondary" href="/master/tx100-master">Back to Seat Map</a>
    </div>
</div>

<!-- Drop-off Modal -->
<div id="dropoffModal" class="dropoff-modal">
    <div class="modal-topbar">
        <div>
            <div style="font-weight:800;font-size:1rem;">Set Drop-off Stop</div>
            <div style="color:rgba(255,255,255,0.45);font-size:0.82rem;">Tap your stop on the route</div>
        </div>
        <button onclick="closeDropoffModal()" style="border:none;background:rgba(255,255,255,0.08);color:white;border-radius:10px;padding:8px 14px;cursor:pointer;font-weight:700;">✕</button>
    </div>
    <div id="dropoffMap" class="modal-map"></div>
    <div id="dropoffFooter" class="modal-footer">
        <div style="color:rgba(255,255,255,0.45);font-size:0.75rem;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Drop-off Location</div>
        <div id="dropoffAddress" style="color:white;font-weight:800;margin-bottom:12px;"></div>
        <button class="confirm-btn" onclick="confirmDropoff()">📍 Confirm → Notify Driver</button>
    </div>
</div>

<script>
var miniMap = null, dropoffMap = null, dropoffMarker = null, dropoffLatLng = null;
var routeCoords = {route_coords_json};

function initMiniMap() {{
    if (miniMap) return;
    miniMap = L.map("miniMap", {{zoomControl:false, dragging:false, scrollWheelZoom:false}});
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{attribution:"© OpenStreetMap"}}).addTo(miniMap);
    var coords = routeCoords.map(function(p) {{ return p[1] + "," + p[0]; }}).join(";");
    fetch("https://router.project-osrm.org/route/v1/driving/" + coords + "?overview=full&geometries=geojson")
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            if (data.routes && data.routes[0]) {{
                var line = L.geoJSON(data.routes[0].geometry, {{style:{{color:"#1A9FDB",weight:4,opacity:0.85}}}}).addTo(miniMap);
                miniMap.fitBounds(line.getBounds(), {{padding:[20,20]}});
            }}
        }})
        .catch(function() {{
            var line = L.polyline(routeCoords, {{color:"#1A9FDB",weight:4}}).addTo(miniMap);
            miniMap.fitBounds(line.getBounds(), {{padding:[20,20]}});
        }});
    L.marker(routeCoords[0]).addTo(miniMap).bindPopup("Kuwait Taxi Rank");
    L.marker(routeCoords[routeCoords.length-1]).addTo(miniMap).bindPopup("{taxi_route}");
}}

function openDropoffModal() {{
    document.getElementById("dropoffModal").style.display = "flex";
    setTimeout(function() {{
        if (!dropoffMap) {{
            dropoffMap = L.map("dropoffMap");
            L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{attribution:"© OpenStreetMap"}}).addTo(dropoffMap);
            var coords = routeCoords.map(function(p) {{ return p[1] + "," + p[0]; }}).join(";");
            fetch("https://router.project-osrm.org/route/v1/driving/" + coords + "?overview=full&geometries=geojson")
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    if (data.routes && data.routes[0]) {{
                        var line = L.geoJSON(data.routes[0].geometry, {{style:{{color:"#1A9FDB",weight:5,opacity:0.85}}}}).addTo(dropoffMap);
                        dropoffMap.fitBounds(line.getBounds(), {{padding:[30,30]}});
                    }}
                }});
            L.marker(routeCoords[0]).addTo(dropoffMap).bindPopup("Kuwait Taxi Rank - Start");
            L.marker(routeCoords[routeCoords.length-1]).addTo(dropoffMap).bindPopup("{taxi_route} Taxi Rank");
            dropoffMap.on("click", function(e) {{
                dropoffLatLng = e.latlng;
                if (dropoffMarker) dropoffMap.removeLayer(dropoffMarker);
                dropoffMarker = L.marker(e.latlng).addTo(dropoffMap);
                document.getElementById("dropoffFooter").style.display = "block";
                document.getElementById("dropoffAddress").textContent = "Fetching address...";
                fetch("https://nominatim.openstreetmap.org/reverse?lat=" + e.latlng.lat + "&lon=" + e.latlng.lng + "&format=json")
                    .then(function(r) {{ return r.json(); }})
                    .then(function(d) {{
                        document.getElementById("dropoffAddress").textContent =
                            d.display_name ? d.display_name.split(",").slice(0,3).join(", ") : e.latlng.lat.toFixed(4) + ", " + e.latlng.lng.toFixed(4);
                    }});
            }});
        }} else {{
            dropoffMap.invalidateSize();
        }}
    }}, 100);
}}

function closeDropoffModal() {{
    document.getElementById("dropoffModal").style.display = "none";
}}

async function confirmDropoff() {{
    if (!dropoffLatLng) return;
    var addr = document.getElementById("dropoffAddress").textContent;
    try {{
        await fetch("/seats/{seat_id}/dropoff", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{lat: dropoffLatLng.lat, lng: dropoffLatLng.lng, address: addr, seat_number: {seat.seat_number}}})
        }});
    }} catch(e) {{}}
    closeDropoffModal();
    document.getElementById("dropoffSentInline").style.display = "block";
    document.getElementById("dropoffAddrInline").textContent = addr;
}}

window.onload = function() {{ initMiniMap(); }};
</script>
</body>
</html>"""


@router.get("/driver")
def driver_auto(db: Session = Depends(get_db), driver_session: Optional[str] = Cookie(default=None)):
    from app.auth import verify_session_token as _verify
    if not driver_session or not _verify(driver_session, "driver"):
        return RedirectResponse(url="/driver/login", status_code=302)
    taxi = db.query(Taxi).order_by(Taxi.vehicle_code).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="No taxi found")

    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE")
        .order_by(Trip.started_at.desc())
        .first()
    )

    if not active_trip:
        active_trip = Trip(
            id=str(uuid4()),
            taxi_id=taxi.id,
            fare_amount=get_route_fare(taxi.route_name),
            status="ACTIVE",
        )
        db.add(active_trip)
        db.commit()
        db.refresh(active_trip)

    return RedirectResponse(url=f"/driver/{active_trip.id}")


@router.get("/driver/{trip_id}", response_class=HTMLResponse)
def driver_page(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    taxi = db.query(Taxi).filter(Taxi.id == trip.taxi_id).first()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow Driver</title>
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
        .bg-glow {{
            position: fixed;
            top: -100px;
            left: 50%;
            transform: translateX(-50%);
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(26,159,219,0.12) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }}
        .wrap {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 28px 20px 48px;
            position: relative;
            z-index: 1;
        }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 28px;
            flex-wrap: wrap;
        }}
        .topbar-left {{ display: flex; align-items: center; gap: 14px; }}
        .topbar-logo {{
            width: 46px;
            height: 46px;
            border-radius: 14px;
            background: linear-gradient(135deg, #1A9FDB, #0B72C6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 6px 18px rgba(26,159,219,0.35);
            flex-shrink: 0;
        }}
        .topbar h1 {{
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}
        .topbar p {{
            color: rgba(255,255,255,0.4);
            font-size: 0.85rem;
            margin-top: 3px;
        }}
        .trip-badge {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
            padding: 16px 18px;
            min-width: 260px;
        }}
        .trip-badge-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
            font-size: 0.88rem;
        }}
        .trip-badge-label {{ color: rgba(255,255,255,0.4); font-weight: 700; }}
        .trip-badge-value {{ color: white; font-weight: 800; }}
        .trip-badge button {{
            display: block;
            width: 100%;
            margin-top: 10px;
            padding: 9px 12px;
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: 700;
            cursor: pointer;
            font-size: 0.88rem;
            transition: opacity 0.15s;
        }}
        .trip-badge button:hover {{ opacity: 0.85; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin: 0 0 24px;
        }}
        .stat {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.12);
        }}
        .stat-label {{
            color: rgba(255,255,255,0.4);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: 800;
            color: white;
        }}
        .panel {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 24px;
            padding: 20px;
        }}
        .toast {{
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: linear-gradient(135deg, #F4C542, #e6b800);
            color: #1a1200;
            font-weight: 800;
            padding: 14px 24px;
            border-radius: 999px;
            font-size: 1rem;
            box-shadow: 0 8px 24px rgba(244,197,66,0.4);
            transition: transform 0.3s ease;
            z-index: 9999;
            white-space: nowrap;
        }}
        .toast.show {{
            transform: translateX(-50%) translateY(0);
        }}
        .panel h2 {{
            margin: 0 0 16px;
            font-size: 0.85rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: rgba(255,255,255,0.45);
        }}
        .seat-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
        }}
        .seat {{
            min-height: 100px;
            border-radius: 18px;
            padding: 12px 8px;
            text-align: center;
            font-weight: 800;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            transition: transform 0.12s;
        }}
        .seat:hover {{ transform: translateY(-2px); }}
        .seat-number {{
            font-size: 1.5rem;
            margin-bottom: 6px;
        }}
        .seat-status {{
            font-size: 0.85rem;
            opacity: 0.95;
        }}
        .seat button {{
            margin-top: 10px;
            padding: 8px 10px;
            border: none;
            border-radius: 12px;
            background: rgba(0,0,0,0.2);
            color: white;
            font-weight: 700;
            cursor: pointer;
        }}
        .PAID {{
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
            color: white;
        }}
        .UNPAID {{
            background: linear-gradient(180deg, #f16b63 0%, #E74C3C 100%);
            color: white;
        }}
        .CASH {{
            background: linear-gradient(180deg, #f7d56b 0%, #F4C542 100%);
            color: #4a3b00;
        }}
        .CASH_INTENT {{
            background: rgba(244,197,66,0.15);
            border: 2px solid rgba(244,197,66,0.4) !important;
            color: #F4C542;
            animation: pulse-cash 1.5s ease-in-out infinite alternate;
        }}
        @keyframes pulse-cash {{
            from {{ box-shadow: 0 0 0 rgba(244,197,66,0.3); }}
            to {{ box-shadow: 0 0 18px rgba(244,197,66,0.5); }}
        }}
        .cash-result {{
            display: none;
            margin: 0 0 20px;
            background: #0d1f2e;
            border: 1px solid rgba(26,159,219,0.2);
            border-radius: 20px;
            padding: 18px;
            box-shadow: 0 10px 28px rgba(0,0,0,0.2);
        }}
        .cash-result.show {{
            display: block;
        }}
        .cash-result-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }}
        .cash-result-item {{
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 12px;
        }}
        .cash-result-label {{
            color: rgba(255,255,255,0.7);
            font-size: 0.82rem;
            margin-bottom: 6px;
        }}
        .cash-result-value {{
            font-size: 1.15rem;
            font-weight: 800;
        }}
        @media (max-width: 900px) {{
            .summary {{
                grid-template-columns: repeat(4, 1fr);
            }}
            .seat-grid {{
                grid-template-columns: repeat(5, 1fr);
            }}
        }}
        @media (max-width: 600px) {{
            .summary {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .seat-grid {{
                grid-template-columns: repeat(3, 1fr);
            }}
            .stat-value {{
                font-size: 1.55rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="bg-glow"></div>
    <div class="wrap">
        <div class="topbar">
            <div class="topbar-left">
                <div class="topbar-logo">🚗</div>
                <div>
                    <h1>Driver Dashboard</h1>
                    <p>Live seat status · <span id="subtitleRoute">{taxi.route_name if taxi else ""}</span> · {taxi.vehicle_code if taxi else ""}</p>
                </div>
            </div>
            <div class="trip-badge">
                <div class="trip-badge-row">
                    <span class="trip-badge-label">Trip</span>
                    <span class="trip-badge-value">#{trip_id[-4:].upper()}</span>
                </div>
                <div class="trip-badge-row">
                    <span class="trip-badge-label">Route</span>
                    <span class="trip-badge-value" id="routeName">{taxi.route_name if taxi else "Unknown"}</span>
                </div>
                <div class="trip-badge-row">
                    <span class="trip-badge-label">Fare</span>
                    <span class="trip-badge-value">R<span id="fareValue">{trip.fare_amount:.2f}</span></span>
                </div>
                <button type="button" onclick="changeRoute()" style="display:block;width:100%;margin-top:10px;padding:8px 10px;border:none;border-radius:10px;background:#6C5CE7;color:white;font-weight:700;cursor:pointer;">Change Route</button>
                <button type="button" onclick="editFare()" style="display:block;width:100%;margin-top:8px;padding:8px 10px;border:none;border-radius:10px;background:#1A9FDB;color:white;font-weight:700;cursor:pointer;">Edit Fare</button>
                <button type="button" onclick="showTripSummary()" style="display:block;width:100%;margin-top:8px;padding:8px 10px;border:none;border-radius:10px;background:#E74C3C;color:white;font-weight:700;cursor:pointer;">End Trip</button>
                <a href="/driver/logout" style="display:block;width:100%;margin-top:8px;padding:8px 10px;border:none;border-radius:10px;background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);font-weight:700;cursor:pointer;text-align:center;text-decoration:none;font-size:0.85rem;">Sign Out</a>
            </div>
        </div>

        <div class="summary">
            <div class="stat">
                <div class="stat-label">Total Seats</div>
                <div class="stat-value" id="totalSeats">15</div>
            </div>
            <div class="stat">
                <div class="stat-label">Paid</div>
                <div class="stat-value" id="paidSeats" style="color:#4ac96b;">0</div>
            </div>
            <div class="stat">
                <div class="stat-label">Cash</div>
                <div class="stat-value" id="cashSeats" style="color:#F4C542;">0</div>
            </div>
            <div class="stat">
                <div class="stat-label">Open</div>
                <div class="stat-value" id="openSeats" style="color:#f16b63;">0</div>
            </div>
        </div>

        <div id="cashResult" class="cash-result">
            <div style="font-size:1rem;font-weight:800;margin-bottom:10px;">Cash Payment Captured</div>
            <div class="cash-result-grid">
                <div class="cash-result-item">
                    <div class="cash-result-label">Seat</div>
                    <div class="cash-result-value" id="cashResultSeat">--</div>
                </div>
                <div class="cash-result-item">
                    <div class="cash-result-label">Fare</div>
                    <div class="cash-result-value" id="cashResultFare">R0.00</div>
                </div>
                <div class="cash-result-item">
                    <div class="cash-result-label">Received</div>
                    <div class="cash-result-value" id="cashResultReceived">R0.00</div>
                </div>
                <div class="cash-result-item">
                    <div class="cash-result-label">Change Due</div>
                    <div class="cash-result-value" id="cashResultChange">R0.00</div>
                </div>
            </div>
        </div>

        <div id="fareModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;align-items:center;justify-content:center;padding:18px;">
    <div style="width:100%;max-width:320px;background:#0d1f2e;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:24px;box-shadow:0 20px 40px rgba(0,0,0,0.5);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
            <div style="font-size:1.1rem;font-weight:800;color:white;">Edit Fare</div>
            <button onclick="document.getElementById('fareModal').style.display='none'" style="border:none;background:rgba(255,255,255,0.08);color:white;border-radius:10px;padding:6px 14px;cursor:pointer;font-weight:700;">✕</button>
        </div>
        <div style="color:rgba(255,255,255,0.45);font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Fare Amount (ZAR)</div>
        <input id="fareInput" type="number" step="0.50" min="0"
            style="width:100%;padding:14px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:14px;color:white;font-size:1.6rem;font-weight:800;outline:none;margin-bottom:16px;font-family:inherit;box-sizing:border-box;text-align:center;"
            onkeydown="if(event.key==='Enter') submitFare()">
        <button onclick="submitFare()" style="width:100%;padding:14px;border:none;border-radius:14px;background:linear-gradient(135deg,#1A9FDB,#0B72C6);color:white;font-weight:800;font-size:1rem;cursor:pointer;">
            ✓ Update Fare
        </button>
    </div>
</div>

<div id="routeModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;align-items:center;justify-content:center;padding:18px;">
    <div style="width:100%;max-width:420px;background:#0d1f2e;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:22px;max-height:80vh;display:flex;flex-direction:column;box-shadow:0 20px 40px rgba(0,0,0,0.5);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div style="font-size:1.1rem;font-weight:800;color:white;">Change Route</div>
            <button onclick="document.getElementById('routeModal').style.display='none'" style="border:none;background:rgba(255,255,255,0.08);color:white;border-radius:10px;padding:6px 14px;cursor:pointer;font-weight:700;">✕</button>
        </div>
        <input id="routeSearch" type="text" placeholder="Search route..." oninput="filterRoutes(this.value)"
            style="width:100%;padding:12px 14px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:14px;color:white;font-size:1rem;outline:none;margin-bottom:12px;font-family:inherit;box-sizing:border-box;">
        <div id="routeList" style="overflow-y:auto;flex:1;max-height:400px;"></div>
    </div>
</div>

<div id="summaryModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:999;align-items:center;justify-content:center;padding:18px;">
            <div style="width:100%;max-width:520px;background:linear-gradient(180deg,#102b45 0%,#0b2238 100%);border:1px solid rgba(255,255,255,0.10);border-radius:24px;padding:22px;box-shadow:0 20px 40px rgba(0,0,0,0.35);">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px;">
                    <div>
                        <div style="font-size:1.35rem;font-weight:800;">Trip Summary</div>
                        <div style="color:rgba(255,255,255,0.72);margin-top:4px;">Close-out report for this trip</div>
                    </div>
                    <button onclick="startNewTrip()" style="border:none;background:#1A9FDB;color:white;border-radius:12px;padding:8px 12px;font-weight:700;cursor:pointer;">Start New Trip</button>
                </div>

                <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;">
                    <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;">
                        <div style="color:rgba(255,255,255,0.68);font-size:0.82rem;">Route</div>
                        <div id="summaryRoute" style="font-weight:800;font-size:1.05rem;margin-top:6px;">--</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;">
                        <div style="color:rgba(255,255,255,0.68);font-size:0.82rem;">Fare</div>
                        <div id="summaryFare" style="font-weight:800;font-size:1.05rem;margin-top:6px;">R0.00</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;">
                        <div style="color:rgba(255,255,255,0.68);font-size:0.82rem;">Paid</div>
                        <div id="summaryPaid" style="font-weight:800;font-size:1.05rem;margin-top:6px;">0</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;">
                        <div style="color:rgba(255,255,255,0.68);font-size:0.82rem;">Cash</div>
                        <div id="summaryCash" style="font-weight:800;font-size:1.05rem;margin-top:6px;">0</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;">
                        <div style="color:rgba(255,255,255,0.68);font-size:0.82rem;">Open</div>
                        <div id="summaryOpen" style="font-weight:800;font-size:1.05rem;margin-top:6px;">0</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:14px;">
                        <div style="color:rgba(255,255,255,0.68);font-size:0.82rem;">Occupancy</div>
                        <div id="summaryOccupancy" style="font-weight:800;font-size:1.05rem;margin-top:6px;">0%</div>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
                    <div style="background:rgba(26,159,219,0.12);border:1px solid rgba(26,159,219,0.20);border-radius:18px;padding:16px;">
                        <div style="color:rgba(255,255,255,0.72);font-size:0.82rem;">Online</div>
                        <div id="summaryOnline" style="font-size:1.2rem;font-weight:800;margin-top:6px;">R0.00</div>
                    </div>
                    <div style="background:rgba(244,197,66,0.12);border:1px solid rgba(244,197,66,0.20);border-radius:18px;padding:16px;">
                        <div style="color:rgba(255,255,255,0.72);font-size:0.82rem;">Cash Revenue</div>
                        <div id="summaryCashRevenue" style="font-size:1.2rem;font-weight:800;margin-top:6px;">R0.00</div>
                    </div>
                    <div style="background:rgba(74,201,107,0.12);border:1px solid rgba(74,201,107,0.20);border-radius:18px;padding:16px;">
                        <div style="color:rgba(255,255,255,0.72);font-size:0.82rem;">Total</div>
                        <div id="summaryTotal" style="font-size:1.2rem;font-weight:800;margin-top:6px;">R0.00</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="panel">
            <h2>Current Seats</h2>
            <div id="seatGrid" class="seat-grid"></div>
        </div>
    </div>

<script>
let _allRoutes = [];

function filterRoutes(query) {{
    const list = document.getElementById("routeList");
    const q = query.toLowerCase();
    const filtered = _allRoutes.filter(r => r.route_name.toLowerCase().includes(q));
    if (filtered.length === 0) {{
        list.innerHTML = '<div style="color:rgba(255,255,255,0.4);padding:12px;text-align:center;">No routes found</div>';
        return;
    }}
    list.innerHTML = filtered.map(r => `
        <div onclick="selectRoute('${{r.route_name}}', ${{r.fare}})"
            style="padding:14px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;"
            onmouseover="this.style.background='rgba(26,159,219,0.15)'"
            onmouseout="this.style.background='rgba(255,255,255,0.05)'">
            <span style="font-weight:700;color:white;">${{r.route_name}}</span>
            <span style="color:#1A9FDB;font-weight:800;">R${{r.fare.toFixed(2)}}</span>
        </div>
    `).join("");
}}

async function selectRoute(routeName, fare) {{
    document.getElementById("routeModal").style.display = "none";
    const updateRes = await fetch("/trips/{trip_id}/route?route_name=" + encodeURIComponent(routeName), {{method:"POST"}});
    const data = await updateRes.json();
    if (!updateRes.ok) {{ alert(data.detail || "Failed to update route"); return; }}
    document.getElementById("routeName").textContent = data.route_name;
    if (document.getElementById("subtitleRoute")) document.getElementById("subtitleRoute").textContent = data.route_name;
    document.getElementById("fareValue").textContent = parseFloat(data.fare).toFixed(2);
    await loadSeatMap();
}}

async function changeRoute() {{
    if (_allRoutes.length === 0) {{
        const res = await fetch("/routes");
        _allRoutes = await res.json();
    }}
    document.getElementById("routeSearch").value = "";
    filterRoutes("");
    document.getElementById("routeModal").style.display = "flex";
    setTimeout(() => document.getElementById("routeSearch").focus(), 100);
}}

async function editFare() {{
    document.getElementById("fareInput").value = document.getElementById("fareValue").textContent;
    document.getElementById("fareModal").style.display = "flex";
    setTimeout(() => document.getElementById("fareInput").focus(), 100);
}}

async function submitFare() {{
    const newFare = document.getElementById("fareInput").value;
    if (!newFare) return;
    document.getElementById("fareModal").style.display = "none";
    const res = await fetch("/trips/{trip_id}/fare?fare=" + encodeURIComponent(newFare), {{method:"POST"}});
    if (!res.ok) {{ alert("Failed to update fare"); return; }}
    const data = await res.json();
    document.getElementById("fareValue").textContent = parseFloat(data.new_fare).toFixed(2);
    await loadSeatMap();
}}


let socket = null;

const cashIntentSeats = new Set();

async function loadSeatMap() {{
    const res = await fetch("/trips/{trip_id}/seat-map");
    const data = await res.json();

    const grid = document.getElementById("seatGrid");
    grid.innerHTML = "";

    let paid = 0;
    let cash = 0;
    let unpaid = 0;

    data.seats.forEach(seat => {{
        if (seat.status === "PAID") paid++;
        if (seat.status === "CASH") cash++;
        if (seat.status === "UNPAID") unpaid++;
        seat.cash_intent = cashIntentSeats.has(String(seat.id));

        const div = document.createElement("div");
        div.className = "seat " + seat.status;

        if (seat.status === "UNPAID" && seat.cash_intent) {{
            div.className = "seat CASH_INTENT";
            div.innerHTML = `
                <div class="seat-number">${{seat.seat_number}}</div>
                <div class="seat-status" style="font-size:0.7rem;">💵 Cash</div>
                <button onclick="markCash('${{seat.id}}')">Confirm</button>
            `;
        }} else if (seat.status === "UNPAID") {{
            div.innerHTML = `
                <div class="seat-number">${{seat.seat_number}}</div>
                <div class="seat-status">${{seat.status}}</div>
                <button onclick="markCash('${{seat.id}}')">Mark Cash</button>
            `;
        }} else {{
            div.innerHTML = `
                <div class="seat-number">${{seat.seat_number}}</div>
                <div class="seat-status">${{seat.status}}</div>
            `;
        }}

        grid.appendChild(div);
    }});

    document.getElementById("totalSeats").innerText = data.seats.length;
    document.getElementById("paidSeats").innerText = paid;
    document.getElementById("cashSeats").innerText = cash;
    document.getElementById("openSeats").innerText = unpaid;
}}

async function markCash(seatId) {{
    const fareText = document.getElementById("fareValue").textContent;
    const fare = parseFloat(fareText || "0");
    document.getElementById("cashModalFare").textContent = "R" + fare.toFixed(2);
    document.getElementById("cashAmountInput").value = fare.toFixed(2);
    document.getElementById("_cashSeatId").value = seatId;
    document.getElementById("cashModal").style.display = "flex";
    setTimeout(() => document.getElementById("cashAmountInput").focus(), 100);
}}

async function submitCash() {{
    const seatId = document.getElementById("_cashSeatId").value;
    const amount = parseFloat(document.getElementById("cashAmountInput").value);
    if (Number.isNaN(amount)) {{ alert("Enter a valid amount"); return; }}
    document.getElementById("cashModal").style.display = "none";
    const res = await fetch(`/seats/${{seatId}}/cash`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(amount)
    }});
    const data = await res.json();
    if (!res.ok) {{ alert(data.detail || "Failed to mark cash"); return; }}
    document.getElementById("cashResultSeat").textContent = data.seat_number ? ("Seat " + data.seat_number) : "Captured";
    document.getElementById("cashResultFare").textContent = "R" + parseFloat(data.fare || 0).toFixed(2);
    document.getElementById("cashResultReceived").textContent = "R" + parseFloat(data.amount_received || 0).toFixed(2);
    document.getElementById("cashResultChange").textContent = "R" + parseFloat(data.change || 0).toFixed(2);
    document.getElementById("cashResult").classList.add("show");
    await loadSeatMap();
}}

// AI Voice announcements via ElevenLabs (James)
async function speak(text) {{
    try {{
        const res = await fetch("/speak?text=" + encodeURIComponent(text), {{method:"POST"}});
        if (!res.ok) throw new Error("TTS failed");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play();
        audio.onended = () => URL.revokeObjectURL(url);
    }} catch(e) {{
        // Fallback to browser voice
        if (window.speechSynthesis) {{
            const msg = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(msg);
        }}
    }}
}}

function connectWebSocket() {{
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${{protocol}}://${{window.location.host}}/ws/{trip_id}`);

    socket.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        if (data.type === "seat_update") {{
            loadSeatMap();
            speak("Seat " + (data.seat_number || "") + " paid");
        }}
        if (data.type === "cash_intent") {{
            const toast = document.getElementById("cashToast");
            document.getElementById("toastSeat").textContent = data.seat_number;
            toast.classList.add("show");
            setTimeout(() => toast.classList.remove("show"), 4000);
            cashIntentSeats.add(String(data.seat_id));
            speak("Seat " + data.seat_number + " wants to pay cash");
            loadSeatMap();
        }}
    }};

    socket.onclose = () => {{
        setTimeout(connectWebSocket, 2000);
    }};
}}


async function showTripSummary() {{
    const res = await fetch("/trips/{trip_id}/summary");
    const data = await res.json();

    if (!res.ok) {{
        alert(data.detail || "Failed to load trip summary");
        return;
    }}

    document.getElementById("summaryRoute").textContent = document.getElementById("routeName").textContent;
    document.getElementById("summaryFare").textContent = "R" + parseFloat(data.fare || 0).toFixed(2);
    document.getElementById("summaryPaid").textContent = data.paid_count;
    document.getElementById("summaryCash").textContent = data.cash_count;
    document.getElementById("summaryOpen").textContent = data.open_count;
    document.getElementById("summaryOccupancy").textContent = data.occupancy_percent + "%";
    document.getElementById("summaryOnline").textContent = "R" + parseFloat(data.online_revenue || 0).toFixed(2);
    document.getElementById("summaryCashRevenue").textContent = "R" + parseFloat(data.cash_revenue || 0).toFixed(2);
    document.getElementById("summaryTotal").textContent = "R" + parseFloat(data.total_revenue || 0).toFixed(2);
    document.getElementById("summaryModal").style.display = "flex";
}}

function closeSummary() {{
    document.getElementById("summaryModal").style.display = "none";
}}



async function startNewTrip() {{
    const btn = document.querySelector("#summaryModal button");
    if (btn) {{ btn.disabled = true; btn.textContent = "Starting..."; }}
    const res = await fetch("/trips/reset", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ taxi_id: "{trip.taxi_id}" }})
    }});
    const data = await res.json();
    if (!res.ok) {{
        if (btn) {{ btn.disabled = false; btn.textContent = "Start New Trip"; }}
        alert(data.detail || "Failed to start new trip");
        return;
    }}
    window.location.href = "/driver";
}}

loadSeatMap();
connectWebSocket();
</script>

<div id="cashModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;align-items:center;justify-content:center;padding:18px;">
    <div style="width:100%;max-width:320px;background:#0d1f2e;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:24px;box-shadow:0 20px 40px rgba(0,0,0,0.5);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
            <div style="font-size:1.1rem;font-weight:800;color:white;">💵 Mark Cash</div>
            <button onclick="document.getElementById('cashModal').style.display='none'" style="border:none;background:rgba(255,255,255,0.08);color:white;border-radius:10px;padding:6px 14px;cursor:pointer;font-weight:700;">✕</button>
        </div>
        <div style="color:rgba(255,255,255,0.45);font-size:0.78rem;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Fare</div>
        <div id="cashModalFare" style="color:#F4C542;font-size:1.3rem;font-weight:800;margin-bottom:14px;"></div>
        <div style="color:rgba(255,255,255,0.45);font-size:0.78rem;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Cash Received (ZAR)</div>
        <input id="cashAmountInput" type="number" step="0.50" min="0"
            style="width:100%;padding:14px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:14px;color:white;font-size:1.6rem;font-weight:800;outline:none;margin-bottom:16px;font-family:inherit;box-sizing:border-box;text-align:center;"
            onkeydown="if(event.key==='Enter') submitCash()">
        <input type="hidden" id="_cashSeatId">
        <button onclick="submitCash()" style="width:100%;padding:14px;border:none;border-radius:14px;background:linear-gradient(135deg,#F4C542,#e6b800);color:#1a1200;font-weight:800;font-size:1rem;cursor:pointer;">
            ✓ Confirm Cash
        </button>
    </div>
</div>

<div id="cashToast" class="toast">💵 Seat <span id="toastSeat"></span> wants to pay cash!</div>

</body>
</html>
"""
