from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Seat, Trip, Taxi

router = APIRouter()


@router.get("/receipt/{payment_id}", response_class=HTMLResponse)
def receipt_page(payment_id: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Receipt not found")

    seat = db.query(Seat).filter(Seat.id == payment.seat_id).first()
    trip = db.query(Trip).filter(Trip.id == payment.trip_id).first()
    taxi = db.query(Taxi).filter(Taxi.id == trip.taxi_id).first()

    paid_time = payment.created_at.strftime("%Y-%m-%d %H:%M:%S") if payment.created_at else "N/A"
    started_time = trip.started_at.strftime("%Y-%m-%d %H:%M:%S") if trip.started_at else "N/A"

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay Receipt</title>
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
        .shell {{
            width: 100%;
            max-width: 430px;
            padding: 18px 12px 24px;
        }}
        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px;
            padding: 22px 16px 26px;
            box-shadow: 0 12px 22px rgba(11,60,93,0.08);
        }}
        .badge {{
            width: 84px;
            height: 84px;
            margin: 0 auto 16px;
            border-radius: 24px;
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.6rem;
            font-weight: 800;
        }}
        h1 {{
            margin: 0;
            text-align: center;
            color: #0B3C5D;
            font-size: 1.5rem;
        }}
        .ok {{
            text-align: center;
            color: #27AE60;
            font-weight: 800;
            margin: 8px 0 18px;
        }}
        .line {{
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 10px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.04);
        }}
        .label {{
            color: #718797;
            font-size: 0.85rem;
            margin-bottom: 5px;
        }}
        .value {{
            color: #0B3C5D;
            font-weight: 800;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="panel">
                <div class="badge">✓</div>
                <h1>TaxiPay Receipt</h1>
                <p class="ok">Payment Confirmed</p>

                <div class="line"><div class="label">Vehicle</div><div class="value">{taxi.vehicle_code}</div></div>
                <div class="line"><div class="label">Route</div><div class="value">{taxi.route_name}</div></div>
                <div class="line"><div class="label">Seat</div><div class="value">{seat.seat_number}</div></div>
                <div class="line"><div class="label">Amount</div><div class="value">R{payment.amount:.2f}</div></div>
                <div class="line"><div class="label">Status</div><div class="value">{payment.status}</div></div>
                <div class="line"><div class="label">Payment ID</div><div class="value">{payment.id}</div></div>
                <div class="line"><div class="label">Trip ID</div><div class="value">{trip.id}</div></div>
                <div class="line"><div class="label">Trip Started</div><div class="value">{started_time}</div></div>
                <div class="line"><div class="label">Paid At</div><div class="value">{paid_time}</div></div>
            </div>
        </div>
    </div>
</body>
</html>
"""
