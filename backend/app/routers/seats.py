from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Seat, Trip, Payment
from app.ws import manager

router = APIRouter()


@router.post("/seats/{seat_id}/cash")
async def mark_cash(seat_id: str, amount: float = Body(...), db: Session = Depends(get_db)):
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

    if not trip:
        raise HTTPException(status_code=400, detail="No active trip")

    fare = trip.fare_amount
    change = amount - fare

    seat.status = "CASH"
    db.commit()

    existing = (
        db.query(Payment)
        .filter(Payment.trip_id == trip.id, Payment.seat_id == seat.id)
        .first()
    )

    if not existing:
        cash_payment = Payment(
            id=f"cash-{seat.id}-{trip.id}",
            trip_id=trip.id,
            seat_id=seat.id,
            amount=fare,
            status="SUCCESS_CASH",
        )
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
        "seat_id": seat.id,
        "seat_number": seat.seat_number,
        "fare": fare,
        "amount_received": amount,
        "change": change,
        "status": seat.status
    }

@router.post("/seats/{seat_id}/cash-intent")
async def cash_intent(seat_id: str, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )

    if trip:
        await manager.broadcast(
            trip.id,
            {
                "type": "cash_intent",
                "seat_id": seat.id,
                "seat_number": seat.seat_number,
                "message": f"Seat {seat.seat_number} wants to pay cash"
            }
        )

    return {"status": "notified", "seat_number": seat.seat_number}
