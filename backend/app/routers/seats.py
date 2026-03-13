from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Seat, Trip, Payment
from app.ws import manager

router = APIRouter()


@router.post("/seats/{seat_id}/cash")
async def mark_cash(seat_id: str, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()

    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    if seat.status in ["PAID", "CASH"]:
        raise HTTPException(status_code=400, detail="Seat already settled")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )

    seat.status = "CASH"
    db.commit()

    if trip:
        cash_payment = Payment(
            id=f"cash-{seat.id}-{trip.id}",
            trip_id=trip.id,
            seat_id=seat.id,
            amount=20.0,
            status="SUCCESS_CASH",
        )
        existing = (
            db.query(Payment)
            .filter(Payment.trip_id == trip.id, Payment.seat_id == seat.id)
            .first()
        )
        if not existing:
            db.add(cash_payment)
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
        "message": "Seat marked as cash",
        "seat_id": seat.id,
        "status": seat.status,
    }
