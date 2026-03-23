from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Seat, Trip
from app.fares import get_route_fare

router = APIRouter()

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
    <script src="https://unpkg.com/html5-qrcode">

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
            margin-top: 16px;
            background: white;
            border-radius: 20px;
            padding: 16px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.06);
            border: 1px solid #E3EEF6;
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
        <div class="fare-card" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
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
                            <div class="pay-option-icon" style="background:#f0f0f0;">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.7 9.05 7.4c1.27.07 2.15.75 2.88.8.97-.17 1.9-.87 3.23-.94 1.72.09 3.02.77 3.86 2.01-3.54 2.13-2.95 6.82.59 8.14-.7 1.92-1.6 3.82-2.56 4.87zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" fill="#1a1a1a"/></svg>
                            </div>
                            <div class="pay-option-text">
                                <strong>Apple Pay</strong>
                                <span>Touch ID / Face ID</span>
                            </div>
                        </div>
                        <div id="method-google" class="pay-option" onclick="selectPaymentMethod('google')">
                            <div class="pay-option-icon" style="background:#fff8f0;">
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
                    </div>

                    <div id="qr-box-wrap" class="qr-box" style="display:none; background:#ffffff; border:1px solid #E3EEF6; border-radius:24px; padding:18px; box-shadow:0 8px 18px rgba(11,60,93,0.05);">
                        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                            <div style="font-size:1.05rem; font-weight:800; color:#0B3C5D;">SnapScan</div>
                            <div style="font-size:0.85rem; font-weight:800; color:#1A9FDB; background:#EEF8FF; border:1px solid #D6ECFB; padding:6px 10px; border-radius:999px;">Scan to pay</div>
                        </div>
                        <div class="qr-frame" onclick="openScanner()" style="cursor:pointer; min-height:240px; border:4px dashed #9BC7E8; border-radius:28px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#FBFDFF; color:#78A7CF; font-weight:800;">
                            <div style="font-size:1.8rem; margin-bottom:8px;">📱</div>
                            <div style="font-size:1.15rem;">SnapScan QR</div>
                            <div style="font-size:0.92rem; margin-top:8px; color:#6B8293;">Tap to use your camera</div>
                        </div>
                        <div id="qr-label" class="qr-label" style="margin-top:14px; text-align:center; color:#6B8293; font-size:0.98rem; font-weight:700;">Scan with SnapScan or continue below</div>
                        <input id="camera-input" type="file" accept="image/*" capture="environment" style="display:none;">
                    </div>

<div class="pay-wrap">
    <button id="pay-btn" class="pay-btn" onclick="payNow()">
        <span id="pay-btn-text">Pay with PayFast</span>
        <span class="pay-arrow">→</span>
    </button>
</div>
                    <div id="result"></div>

                    <div class="secure">🔒 Secure & instant payment</div>
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
        el.style.border = "2px solid #E3EEF6";
        el.style.background = "white";
    }});

    const active = document.getElementById("method-" + selectedMethod);
    if (active) {{
        active.classList.add("active-method");
        active.style.border = "2px solid #1A9FDB";
        active.style.background = "#EEF8FF";
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

    if (method === "snapscan") {{
        qrBox.style.display = "block";
    }} else {{
        qrBox.style.display = "none";
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

function payNow() {{
    if (!"{trip_id}") {{
        document.getElementById("result").innerHTML =
            '<div class="err">No active trip found for this taxi.</div>';
        return;
    }}

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

</script>

</body>
</html>
"""

@router.get("/driver")
def driver_auto(db: Session = Depends(get_db)):
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
    <title>TaxiPay Driver Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #081f33 0%, #0B3C5D 16%, #0f2740 100%);
            min-height: 100vh;
            color: white;
        }}
        .wrap {{
            max-width: 980px;
            margin: 0 auto;
            padding: 24px 16px 32px;
        }}
        .hero {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }}
        .hero h1 {{
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
        }}
        .hero p {{
            margin: 8px 0 0;
            color: rgba(255,255,255,0.78);
        }}
        .trip-badge {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 16px;
            padding: 14px 16px;
            color: rgba(255,255,255,0.92);
            font-weight: 700;
            min-width: 240px;
        }}
        .trip-badge button {{
            display: block;
            width: 100%;
            margin-top: 8px;
            padding: 8px 10px;
            border: none;
            border-radius: 10px;
            color: white;
            font-weight: 700;
            cursor: pointer;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin: 20px 0 22px;
        }}
        .stat {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.12);
        }}
        .stat-label {{
            color: rgba(255,255,255,0.72);
            font-size: 0.92rem;
            margin-bottom: 8px;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: 800;
        }}
        .panel {{
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 18px;
            box-shadow: 0 12px 24px rgba(0,0,0,0.12);
        }}
        .panel h2 {{
            margin: 0 0 14px;
            font-size: 1.2rem;
        }}
        .seat-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
        }}
        .seat {{
            min-height: 110px;
            border-radius: 18px;
            padding: 14px 10px;
            text-align: center;
            font-weight: 800;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-shadow: 0 10px 18px rgba(0,0,0,0.14);
        }}
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
        .cash-result {{
            display: none;
            margin: 0 0 18px;
            background: linear-gradient(180deg, #12324d 0%, #0f2740 100%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.14);
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
                grid-template-columns: repeat(2, 1fr);
            }}
            .seat-grid {{
                grid-template-columns: repeat(3, 1fr);
            }}
        }}
        @media (max-width: 560px) {{
            .summary {{
                grid-template-columns: 1fr 1fr;
                gap: 12px;
            }}
            .seat-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .stat-value {{
                font-size: 1.55rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="hero">
            <div>
                <h1>Driver Dashboard</h1>
                <p>Live seat status and trip activity</p>
            </div>
            <div class="trip-badge">
                <div>Trip #{trip_id[-4:].upper()}</div>
                <div style="margin-top:8px;">Route: <span id="routeName">{taxi.route_name if taxi else "Unknown"}</span></div>
                <div style="margin-top:8px;">Fare: R<span id="fareValue">{trip.fare_amount:.2f}</span></div>
                <button type="button" onclick="changeRoute()" style="display:block;width:100%;margin-top:10px;padding:8px 10px;border:none;border-radius:10px;background:#6C5CE7;color:white;font-weight:700;cursor:pointer;">Change Route</button>
                <button type="button" onclick="editFare()" style="display:block;width:100%;margin-top:8px;padding:8px 10px;border:none;border-radius:10px;background:#1A9FDB;color:white;font-weight:700;cursor:pointer;">Edit Fare</button>
                <button type="button" onclick="showTripSummary()" style="display:block;width:100%;margin-top:8px;padding:8px 10px;border:none;border-radius:10px;background:#E74C3C;color:white;font-weight:700;cursor:pointer;">End Trip</button>
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

        <div class="summary">
            <div class="stat">
                <div class="stat-label">Total seats</div>
                <div class="stat-value" id="totalSeats">15</div>
            </div>
            <div class="stat">
                <div class="stat-label">Paid</div>
                <div class="stat-value" id="paidSeats">0</div>
            </div>
            <div class="stat">
                <div class="stat-label">Cash</div>
                <div class="stat-value" id="cashSeats">0</div>
            </div>
            <div class="stat">
                <div class="stat-label">Open</div>
                <div class="stat-value" id="openSeats">0</div>
            </div>
        </div>

        <div class="panel">
            <h2>Current Seats</h2>
            <div id="seatGrid" class="seat-grid"></div>
        </div>
    </div>

<script>
async function changeRoute() {{
    const res = await fetch("/routes");
    const routes = await res.json();
    const routeNames = routes.map(r => r.route_name).join("\\n");
    const selected = prompt("Enter route name exactly as shown:\\n\\n" + routeNames, document.getElementById("routeName").textContent);
    if (!selected) return;

    const updateRes = await fetch("/trips/{trip_id}/route?route_name=" + encodeURIComponent(selected), {{
        method: "POST"
    }});
    const data = await updateRes.json();

    if (!updateRes.ok) {{
        alert(data.detail || "Failed to update route");
        return;
    }}

    document.getElementById("routeName").textContent = data.route_name;
    document.getElementById("fareValue").textContent = parseFloat(data.fare).toFixed(2);
    await loadSeatMap();
    alert("Route updated successfully");
}}

async function editFare() {{
    const newFare = prompt("Enter new fare (ZAR):", document.getElementById("fareValue").textContent);
    if (!newFare) return;

    const res = await fetch("/trips/{trip_id}/fare?fare=" + encodeURIComponent(newFare), {{
        method: "POST"
    }});
    if (!res.ok) {{
        alert("Failed to update fare");
        return;
    }}

    const data = await res.json();
    document.getElementById("fareValue").textContent = parseFloat(data.new_fare).toFixed(2);
    await loadSeatMap();
    alert("Fare updated successfully");
}}

let socket = null;

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

        const div = document.createElement("div");
        div.className = "seat " + seat.status;

        if (seat.status === "UNPAID") {{
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
    const amountText = prompt("Enter cash received (fare is R" + fare.toFixed(2) + "):", fare.toFixed(2));
    if (!amountText) return;

    const amount = parseFloat(amountText);
    if (Number.isNaN(amount)) {{
        alert("Please enter a valid amount");
        return;
    }}

    const res = await fetch(`/seats/${{seatId}}/cash`, {{
        method: "POST",
        headers: {{
            "Content-Type": "application/json"
        }},
        body: JSON.stringify(amount)
    }});

    const data = await res.json();
    if (!res.ok) {{
        alert(data.detail || "Failed to mark cash");
        return;
    }}

    document.getElementById("cashResultSeat").textContent = data.seat_number ? ("Seat " + data.seat_number) : "Captured";
    document.getElementById("cashResultFare").textContent = "R" + parseFloat(data.fare || 0).toFixed(2);
    document.getElementById("cashResultReceived").textContent = "R" + parseFloat(data.amount_received || 0).toFixed(2);
    document.getElementById("cashResultChange").textContent = "R" + parseFloat(data.change || 0).toFixed(2);
    document.getElementById("cashResult").classList.add("show");

    await loadSeatMap();
}}

function connectWebSocket() {{
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${{protocol}}://${{window.location.host}}/ws/{trip_id}`);

    socket.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        if (data.type === "seat_update") {{
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

</body>
</html>
"""
