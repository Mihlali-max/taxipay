from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Trip, Seat, Payment

router = APIRouter()


@router.get("/debug/taxis")
def list_taxis(db: Session = Depends(get_db)):
    rows = db.query(Taxi).all()
    return [
        {
            "id": r.id,
            "vehicle_code": r.vehicle_code,
            "route_name": r.route_name,
            "seat_count": r.seat_count,
        }
        for r in rows
    ]


@router.get("/debug/trips")
def list_trips(db: Session = Depends(get_db)):
    rows = db.query(Trip).all()
    return [
        {
            "id": r.id,
            "taxi_id": r.taxi_id,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/debug/seats")
def list_seats(db: Session = Depends(get_db)):
    rows = db.query(Seat).order_by(Seat.seat_number).all()
    return [
        {
            "id": r.id,
            "taxi_id": r.taxi_id,
            "seat_number": r.seat_number,
            "qr_token": r.qr_token,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/debug/payments")
def list_payments(db: Session = Depends(get_db)):
    rows = db.query(Payment).all()
    return [
        {
            "id": r.id,
            "trip_id": r.trip_id,
            "seat_id": r.seat_id,
            "amount": r.amount,
            "status": r.status,
        }
        for r in rows
    ]
