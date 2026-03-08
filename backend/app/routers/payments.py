from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trip, Seat, Payment
from app.schemas import MockPayment
from app.ws import manager

router = APIRouter()


@router.post("/payments/mock")
async def mock_payment(payload: MockPayment, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == payload.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    seat = db.query(Seat).filter(Seat.id == payload.seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    if seat.status == "PAID":
        raise HTTPException(status_code=400, detail="Seat already paid")

    if seat.status == "CASH":
        raise HTTPException(status_code=400, detail="Seat already settled with cash")

    payment = Payment(
        id=str(uuid4()),
        trip_id=payload.trip_id,
        seat_id=payload.seat_id,
        amount=payload.amount,
        status="SUCCESS",
    )

    db.add(payment)
    seat.status = "PAID"
    db.commit()

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
        "message": "Mock payment successful",
        "payment_id": payment.id,
        "seat_status": seat.status,
    }
