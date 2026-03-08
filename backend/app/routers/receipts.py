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
    <title>Receipt</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 420px;
            margin: 40px auto;
            padding: 20px;
            background: #f7f7f7;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h2 {{
            margin-top: 0;
        }}
        .ok {{
            color: green;
            font-weight: bold;
        }}
        .line {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Taxi Pay Receipt</h2>
        <p class="ok">Payment Confirmed</p>

        <p class="line"><strong>Vehicle:</strong> {taxi.vehicle_code}</p>
        <p class="line"><strong>Route:</strong> {taxi.route_name}</p>
        <p class="line"><strong>Seat:</strong> {seat.seat_number}</p>
        <p class="line"><strong>Amount:</strong> R{payment.amount:.2f}</p>
        <p class="line"><strong>Status:</strong> {payment.status}</p>
        <p class="line"><strong>Payment ID:</strong> {payment.id}</p>
        <p class="line"><strong>Trip ID:</strong> {trip.id}</p>
        <p class="line"><strong>Trip Started:</strong> {started_time}</p>
        <p class="line"><strong>Paid At:</strong> {paid_time}</p>
    </div>
</body>
</html>
"""
