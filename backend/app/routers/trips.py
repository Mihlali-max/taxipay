from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Trip, Seat
from app.schemas import TripStart

router = APIRouter()


@router.post("/trips/start")
def start_trip(payload: TripStart, db: Session = Depends(get_db)):
    taxi = db.query(Taxi).filter(Taxi.id == payload.taxi_id).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi not found")

    trip = Trip(
        id=str(uuid4()),
        taxi_id=payload.taxi_id,
        status="ACTIVE",
    )
    db.add(trip)
    db.commit()

    return {
        "id": trip.id,
        "taxi_id": trip.taxi_id,
        "status": trip.status,
    }


@router.get("/trips/{trip_id}/seat-map")
def get_seat_map(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    seats = (
        db.query(Seat)
        .filter(Seat.taxi_id == trip.taxi_id)
        .order_by(Seat.seat_number)
        .all()
    )

    return {
        "trip_id": trip.id,
        "taxi_id": trip.taxi_id,
        "seats": [
            {
                "id": s.id,
                "seat_number": s.seat_number,
                "qr_token": s.qr_token,
                "status": s.status,
            }
            for s in seats
        ],
    }


@router.get("/scan/{qr_token}")
def scan_qr(qr_token: str, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.qr_token == qr_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="QR token not found")

    taxi = db.query(Taxi).filter(Taxi.id == seat.taxi_id).first()
    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE")
        .first()
    )

    return {
        "taxi_id": taxi.id,
        "vehicle_code": taxi.vehicle_code,
        "route_name": taxi.route_name,
        "seat_id": seat.id,
        "seat_number": seat.seat_number,
        "qr_token": seat.qr_token,
        "seat_status": seat.status,
        "trip_id": active_trip.id if active_trip else None,
        "fare": 20.00,
        "currency": "ZAR",
    }
