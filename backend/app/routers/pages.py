from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Seat, Trip

router = APIRouter()


@router.get("/master/{token}", response_class=HTMLResponse)
def master_page(token: str, db: Session = Depends(get_db)):
    taxi = db.query(Taxi).filter(Taxi.vehicle_code == "TX100").first()
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
            <a class="seat seat-available" href="/rider/{seat.qr_token}">
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
    <title>TaxiPay - Select Your Seat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 18%, #EAF5FC 18%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
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
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 18px 14px 26px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
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
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            align-items: center;
            margin-bottom: 10px;
        }}

        .driver-box {{
            height: 62px;
            border-radius: 18px;
            background: linear-gradient(180deg, #5c6ee6 0%, #394fca 100%);
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 0.82rem;
            font-weight: 700;
            box-shadow: 0 6px 12px rgba(0,0,0,0.18);
        }}

        .aisle-label {{
            text-align: center;
            color: rgba(255,255,255,0.7);
            font-size: 0.78rem;
            font-weight: 700;
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
    <div class="app">
        <div class="mobile-shell">
            <div class="topbar">
                <a href="/" class="back">‹</a>
                <span>Select Your Seat</span>
            </div>

            <div class="content">
                <div class="panel">
                    <h1 class="title">Choose your seat</h1>
                    <p class="subtitle">
                        Pick an available seat in this Toyota Quantum and continue to payment.
                    </p>

                    <div class="meta">
                        <span class="chip">{taxi.vehicle_code}</span>
                        <span class="chip">{taxi.route_name}</span>
                        <span class="chip">15 passenger seats</span>
                    </div>

                    <div class="quantum">
                        <div class="driver-row">
                            <div class="driver-box">
                                <div style="font-size:1.2rem;">🧑🏽‍✈️</div>
                                <div>Driver</div>
                            </div>
                            <div class="aisle-label">Aisle</div>
                            {seat_html(1)}
                        </div>

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

                        <div class="row-back">
                            <div class="seat seat-empty"></div>
                            {seat_html(14)}
                            {seat_html(15)}
                            <div class="seat seat-empty"></div>
                        </div>
                    </div>

                    <div class="legend">
                        <div class="legend-item">
                            <span class="legend-dot dot-available"></span>
                            <span>Available</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-dot dot-paid"></span>
                            <span>Paid</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-dot dot-cash"></span>
                            <span>Cash</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-dot dot-pending"></span>
                            <span>Pending</span>
                        </div>
                    </div>

                    <div class="helper">
                        Tap a green seat to continue.
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


@router.get("/rider/{qr_token}", response_class=HTMLResponse)
def rider_page(qr_token: str, db: Session = Depends(get_db)):
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
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 18%, #EAF5FC 18%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
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
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 18px 14px 26px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
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
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}

        .pay-option {{
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 16px 10px;
            text-align: center;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}

        .pay-option strong {{
            display: block;
            margin-top: 8px;
            font-size: 0.98rem;
            color: #0B3C5D;
        }}

        .pay-option span {{
            font-size: 1.45rem;
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
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="mobile-shell">
            <div class="topbar">
                <div class="top-left">
                    <a href="/master/tx100-master" class="back">‹</a>
                    <span>Pay for Your Ride</span>
                </div>
                <span class="shield">🛡️</span>
            </div>

            <div class="content">
                <div class="panel">
                    <div class="hero">
                        <div class="seat-line">
                            <div>
                                <h1 class="seat-title">Seat {seat.seat_number} Selected</h1>
                                <p class="subline">Toyota Quantum • Taxi {taxi.vehicle_code}</p>
                            </div>
                            <div class="seat-number-badge">{seat.seat_number}</div>
                        </div>

                        <div class="fare-card">
                            <div>
                                <div class="metric-title">Fare</div>
                                <div class="fare-value">R20.00</div>
                            </div>
                            <div>
                                <div class="metric-title">Status</div>
                                <div class="status-pill">
                                    <span class="status-dot"></span>
                                    <span>{seat.status.title()}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="section-title">Choose Payment Method</div>

                    <div class="payment-grid">
                        <div class="pay-option">
                            <span>💳</span>
                            <strong>PayFast</strong>
                        </div>
                        <div class="pay-option">
                            <span>📱</span>
                            <strong>SnapScan</strong>
                        </div>
                        <div class="pay-option">
                            <span>🏦</span>
                            <strong>Card</strong>
                        </div>
                    </div>

                    <div class="qr-box">
                        <div class="qr-frame">QR</div>
                        <div class="qr-label">Scan to pay or continue below</div>
                    </div>

                    <button class="pay-btn" onclick="payNow()">Pay Now R20.00 →</button>

                    <div id="result"></div>

                    <div class="secure">🔒 Secure & instant payment</div>
                </div>
            </div>
        </div>
    </div>

<script>
function payNow() {{
    if (!"{trip_id}") {{
        document.getElementById("result").innerHTML =
            '<div class="err">No active trip found for this taxi.</div>';
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
    taxi = db.query(Taxi).filter(Taxi.vehicle_code == "TX100").first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Demo taxi not found")

    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE")
        .first()
    )

    if not active_trip:
        raise HTTPException(status_code=404, detail="No active trip")

    return RedirectResponse(url=f"/driver/{active_trip.id}")


@router.get("/driver/{trip_id}", response_class=HTMLResponse)
def driver_page(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    taxi = db.query(Taxi).filter(Taxi.id == trip.taxi_id).first()
    taxi_id = taxi.id if taxi else ""
    vehicle_code = taxi.vehicle_code if taxi else "TX100"

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
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
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

        .control-btn {{
            padding: 12px 16px;
            border: none;
            border-radius: 14px;
            color: white;
            font-weight: 800;
            cursor: pointer;
        }}

        .btn-blue {{
            background: #1A9FDB;
        }}

        .btn-red {{
            background: #E74C3C;
        }}

        .history-row {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
            padding: 12px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
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
            .wrap {{
                padding: 18px 12px 24px;
            }}

            .hero h1 {{
                font-size: 1.6rem;
            }}

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
                <p>{vehicle_code} • Live seat status and trip activity</p>
            </div>
            <div class="trip-badge">Trip ID: {trip_id}</div>
        </div>

        <div class="summary">
            <div class="stat"><div class="stat-label">Total seats</div><div class="stat-value" id="totalSeats">15</div></div>
            <div class="stat"><div class="stat-label">Paid</div><div class="stat-value" id="paidSeats">0</div></div>
            <div class="stat"><div class="stat-label">Cash</div><div class="stat-value" id="cashSeats">0</div></div>
            <div class="stat"><div class="stat-label">Open</div><div class="stat-value" id="openSeats">0</div></div>
            <div class="stat"><div class="stat-label">Revenue</div><div class="stat-value" id="totalRevenue">R0</div></div>
            <div class="stat"><div class="stat-label">Occupancy</div><div class="stat-value" id="occupancyPercent">0%</div></div>
        </div>

        <div class="panel" style="margin-bottom:18px;">
            <h2>Trip Controls</h2>
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <button onclick="resetTrip()" class="control-btn btn-blue">Reset Trip</button>
                <button onclick="endTrip()" class="control-btn btn-red">End Trip</button>
            </div>
        </div>

        <div class="panel" style="margin-bottom:18px;">
            <h2>Payment History</h2>
            <div id="paymentHistory" style="display:grid; gap:10px;"></div>
        </div>

        <div class="panel">
            <h2>Current Seats</h2>
            <div id="seatGrid" class="seat-grid"></div>
        </div>
    </div>

<script>
let socket = null;
const taxiId = "{taxi_id}";

async function loadSeatMap() {{
    const res = await fetch("/trips/{trip_id}/seat-map");
    const data = await res.json();

    const grid = document.getElementById("seatGrid");
    const paymentHistory = document.getElementById("paymentHistory");
    grid.innerHTML = "";
    paymentHistory.innerHTML = "";

    const summary = data.summary || {{}};
    const seats = data.seats || [];
    const history = data.payment_history || [];

    for (const seat of seats) {{
        const div = document.createElement("div");
        div.className = "seat " + seat.status;

        if (seat.status === "UNPAID") {{
            div.innerHTML =
                '<div class="seat-number">' + seat.seat_number + '</div>' +
                '<div class="seat-status">' + seat.status + '</div>' +
                '<button onclick="markCash(\\'' + seat.id + '\\')">Mark Cash</button>';
        }} else {{
            div.innerHTML =
                '<div class="seat-number">' + seat.seat_number + '</div>' +
                '<div class="seat-status">' + seat.status + '</div>';
        }}

        grid.appendChild(div);
    }}

    if (history.length === 0) {{
        paymentHistory.innerHTML = '<div style="color:rgba(255,255,255,0.7);">No payments yet.</div>';
    }} else {{
        for (const item of history.slice(0, 8)) {{
            const row = document.createElement("div");
            row.className = "history-row";
            row.innerHTML =
                '<div>' +
                    '<div style="font-weight:800;">' + item.status + '</div>' +
                    '<div style="font-size:0.86rem; opacity:0.8;">Seat ref: ' + item.seat_id.slice(0, 8) + '</div>' +
                '</div>' +
                '<div style="font-weight:800;">R' + Number(item.amount).toFixed(2) + '</div>';
            paymentHistory.appendChild(row);
        }}
    }}

    document.getElementById("totalSeats").innerText = summary.total_seats ?? seats.length;
    document.getElementById("paidSeats").innerText = summary.paid_count ?? 0;
    document.getElementById("cashSeats").innerText = summary.cash_count ?? 0;
    document.getElementById("openSeats").innerText = summary.open_count ?? 0;
    document.getElementById("totalRevenue").innerText = "R" + Number(summary.total_revenue ?? 0).toFixed(0);
    document.getElementById("occupancyPercent").innerText = String(summary.occupancy_percent ?? 0) + "%";
}}

async function markCash(seatId) {{
    const res = await fetch("/seats/" + seatId + "/cash", {{
        method: "POST"
    }});

    const data = await res.json();

    if (!res.ok) {{
        alert(data.detail || "Failed to mark cash");
        return;
    }}

    loadSeatMap();
}}

async function endTrip() {{
    const res = await fetch("/trips/end", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ taxi_id: taxiId }})
    }});

    const data = await res.json();

    if (!res.ok) {{
        alert(data.detail || "Failed to end trip");
        return;
    }}

    alert("Trip ended successfully");
    window.location.href = "/";
}}

async function resetTrip() {{
    const res = await fetch("/trips/reset", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ taxi_id: taxiId }})
    }});

    const data = await res.json();

    if (!res.ok) {{
        alert(data.detail || "Failed to reset trip");
        return;
    }}

    alert("Trip reset successfully");
    window.location.href = "/driver/" + data.trip_id;
}}

function connectWebSocket() {{
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(protocol + "://" + window.location.host + "/ws/{trip_id}");

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

loadSeatMap();
connectWebSocket();
</script>

</body>
</html>
"""
