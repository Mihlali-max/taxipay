from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import Taxi, Seat, Trip, Payment

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_db)):
    taxi_count = db.query(Taxi).count()
    seat_count = db.query(Seat).count()
    trip_count = db.query(Trip).count()

    payment_count = db.query(Payment).count()
    total_payments = db.query(func.sum(Payment.amount)).scalar() or 0

    paid_seats = db.query(Seat).filter(Seat.status == "PAID").count()
    cash_seats = db.query(Seat).filter(Seat.status == "CASH").count()
    unpaid_seats = db.query(Seat).filter(Seat.status == "UNPAID").count()

    recent_payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .limit(10)
        .all()
    )

    payment_rows = ""
    for p in recent_payments:
        created_at = p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "N/A"
        payment_rows += f"""
        <tr>
            <td>{p.id}</td>
            <td>{p.trip_id}</td>
            <td>{p.seat_id}</td>
            <td>R{p.amount:.2f}</td>
            <td>{p.status}</td>
            <td>{created_at}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>TaxiPay Admin</title>
<style>
body {{
    font-family: Arial, sans-serif;
    max-width: 1000px;
    margin: 40px auto;
    background: #f8f8f8;
    padding: 20px;
}}
h1 {{
    margin-bottom: 30px;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 30px;
}}
.card {{
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.label {{
    color: #555;
    margin-bottom: 8px;
}}
.stat {{
    font-size: 28px;
    font-weight: bold;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
th, td {{
    padding: 12px;
    border-bottom: 1px solid #eee;
    text-align: left;
    font-size: 14px;
}}
th {{
    background: #f2f2f2;
}}
</style>
</head>
<body>

<h1>TaxiPay Admin Dashboard</h1>

<div class="grid">
    <div class="card">
        <div class="label">Taxi Count</div>
        <div class="stat">{taxi_count}</div>
    </div>

    <div class="card">
        <div class="label">Total Seats</div>
        <div class="stat">{seat_count}</div>
    </div>

    <div class="card">
        <div class="label">Trips Started</div>
        <div class="stat">{trip_count}</div>
    </div>

    <div class="card">
        <div class="label">Payments Made</div>
        <div class="stat">{payment_count}</div>
    </div>

    <div class="card">
        <div class="label">Revenue</div>
        <div class="stat">R{total_payments:.2f}</div>
    </div>

    <div class="card">
        <div class="label">Paid Seats</div>
        <div class="stat">{paid_seats}</div>
    </div>

    <div class="card">
        <div class="label">Cash Seats</div>
        <div class="stat">{cash_seats}</div>
    </div>

    <div class="card">
        <div class="label">Unpaid Seats</div>
        <div class="stat">{unpaid_seats}</div>
    </div>
</div>

<h2>Recent Payments</h2>

<table>
    <thead>
        <tr>
            <th>Payment ID</th>
            <th>Trip ID</th>
            <th>Seat ID</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Paid At</th>
        </tr>
    </thead>
    <tbody>
        {payment_rows}
    </tbody>
</table>

</body>
</html>
"""
