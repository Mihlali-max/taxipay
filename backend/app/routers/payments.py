from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trip, Seat, Payment
from app.schemas import MockPayment
from app.ws import manager

router = APIRouter()


async def finalize_seat_payment(
    db: Session,
    trip: Trip,
    seat: Seat,
    amount: float,
    source: str = "PAYFAST",
):
    if seat.status == "PAID":
        return {
            "message": "Seat already paid",
            "seat_status": seat.status,
            "already_paid": True,
        }

    if seat.status == "CASH":
        raise HTTPException(status_code=400, detail="Seat already settled with cash")

    payment = Payment(
        id=str(uuid4()),
        trip_id=trip.id,
        seat_id=seat.id,
        amount=amount,
        status=f"SUCCESS_{source}",
    )

    db.add(payment)
    seat.status = "PAID"
    db.commit()
    db.refresh(seat)

    await manager.broadcast(
        trip.id,
        {
            "type": "seat_update",
            "seat_id": seat.id,
            "seat_number": seat.seat_number,
            "status": seat.status,
        },
    )

    return {
        "message": f"{source} payment successful",
        "payment_id": payment.id,
        "seat_status": seat.status,
        "already_paid": False,
    }


@router.post("/payments/mock")
async def mock_payment(payload: MockPayment, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == payload.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    seat = db.query(Seat).filter(Seat.id == payload.seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    result = await finalize_seat_payment(
        db=db,
        trip=trip,
        seat=seat,
        amount=payload.amount,
        source="MOCK",
    )

    return result


@router.get("/payments/confirm", response_class=HTMLResponse)
async def payfast_confirm(
    seat_token: str,
    amount: float = 20.0,
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.qr_token == seat_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )
    if not trip:
        raise HTTPException(status_code=404, detail="Active trip not found")

    result = await finalize_seat_payment(
        db=db,
        trip=trip,
        seat=seat,
        amount=amount,
        source="PAYFAST_RETURN",
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment confirmed</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 40px auto;
                padding: 20px;
                background: #f7f7f7;
                color: #111;
            }}
            .card {{
                background: white;
                padding: 24px;
                border-radius: 16px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            }}
            .ok {{
                color: green;
                font-weight: bold;
            }}
            a {{
                color: #4b0082;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Payment confirmed</h1>
            <p>Seat <strong>{seat.seat_number}</strong> status: <span class="ok">{seat.status}</span></p>
            <p>{result["message"]}</p>
            <p><a href="/driver">Open driver view</a></p>
        </div>
    </body>
    </html>
    """


@router.post("/payments/payfast/itn")
async def payfast_itn(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()

    seat_token = form.get("custom_str1")
    amount_raw = form.get("amount_gross") or form.get("amount_net") or form.get("amount")
    payment_status = form.get("payment_status", "")

    if not seat_token:
        return JSONResponse({"ok": False, "error": "Missing custom_str1 seat token"}, status_code=400)

    seat = db.query(Seat).filter(Seat.qr_token == seat_token).first()
    if not seat:
        return JSONResponse({"ok": False, "error": "Seat not found"}, status_code=404)

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )
    if not trip:
        return JSONResponse({"ok": False, "error": "Active trip not found"}, status_code=404)

    try:
        amount = float(amount_raw) if amount_raw else 20.0
    except ValueError:
        amount = 20.0

    if payment_status.upper() not in {"COMPLETE", "COMPLETE "} and payment_status.lower() not in {"complete"}:
        return JSONResponse({"ok": True, "message": "Ignored non-complete payment"}, status_code=200)

    result = await finalize_seat_payment(
        db=db,
        trip=trip,
        seat=seat,
        amount=amount,
        source="PAYFAST_ITN",
    )

    return JSONResponse({"ok": True, **result}, status_code=200)
