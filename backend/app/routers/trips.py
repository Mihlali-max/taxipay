from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Trip, Seat, Payment
from app.schemas import TripStart, TripAction

router = APIRouter()


@router.post("/trips/start")
def start_trip(payload: TripStart, db: Session = Depends(get_db)):
    taxi = db.query(Taxi).filter(Taxi.id == payload.taxi_id).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi not found")

    existing_active = (
        db.query(Trip)
        .filter(Trip.taxi_id == payload.taxi_id, Trip.status == "ACTIVE")
        .first()
    )
    if existing_active:
        return {
            "id": existing_active.id,
            "taxi_id": existing_active.taxi_id,
            "status": existing_active.status,
            "message": "Trip already active",
        }

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


@router.post("/trips/end")
def end_trip(payload: TripAction, db: Session = Depends(get_db)):
    taxi = db.query(Taxi).filter(Taxi.id == payload.taxi_id).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi not found")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == payload.taxi_id, Trip.status == "ACTIVE")
        .first()
    )
    if not trip:
        raise HTTPException(status_code=404, detail="No active trip found")

    trip.status = "COMPLETED"
    db.commit()

    return {
        "message": "Trip ended successfully",
        "trip_id": trip.id,
        "status": trip.status,
    }


@router.post("/trips/reset")
def reset_trip(payload: TripAction, db: Session = Depends(get_db)):
    taxi = db.query(Taxi).filter(Taxi.id == payload.taxi_id).first()
    if not taxi:
        raise HTTPException(status_code=404, detail="Taxi not found")

    seats = db.query(Seat).filter(Seat.taxi_id == payload.taxi_id).all()
    for seat in seats:
        seat.status = "UNPAID"

    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == payload.taxi_id, Trip.status == "ACTIVE")
        .first()
    )

    if active_trip:
        active_trip.status = "COMPLETED"

    new_trip = Trip(
        id=str(uuid4()),
        taxi_id=payload.taxi_id,
        status="ACTIVE",
    )
    db.add(new_trip)
    db.commit()

    return {
        "message": "Trip reset successfully",
        "trip_id": new_trip.id,
        "status": new_trip.status,
    }


@router.get("/trips/{trip_id}/seat-map")
def get_seat_map(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    taxi = db.query(Taxi).filter(Taxi.id == trip.taxi_id).first()

    seats = (
        db.query(Seat)
        .filter(Seat.taxi_id == trip.taxi_id)
        .order_by(Seat.seat_number)
        .all()
    )

    payments = db.query(Payment).filter(Payment.trip_id == trip.id).all()

    online_revenue = sum(p.amount for p in payments if "PAYFAST" in p.status or "MOCK" in p.status)
    cash_count = sum(1 for s in seats if s.status == "CASH")
    paid_count = sum(1 for s in seats if s.status == "PAID")
    unpaid_count = sum(1 for s in seats if s.status == "UNPAID")
    cash_revenue = cash_count * 20.0
    total_revenue = online_revenue + cash_revenue
    occupancy = ((paid_count + cash_count) / len(seats) * 100) if seats else 0

    payment_history = [
        {
            "payment_id": p.id,
            "seat_id": p.seat_id,
            "amount": p.amount,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in sorted(payments, key=lambda x: x.created_at or 0, reverse=True)
    ]

    return {
        "trip_id": trip.id,
        "taxi_id": trip.taxi_id,
        "vehicle_code": taxi.vehicle_code if taxi else "Unknown",
        "route_name": taxi.route_name if taxi else "Unknown",
        "trip_status": trip.status,
        "fare": 20.0,
        "seats": [
            {
                "id": s.id,
                "seat_number": s.seat_number,
                "qr_token": s.qr_token,
                "status": s.status,
            }
            for s in seats
        ],
        "summary": {
            "total_seats": len(seats),
            "paid_count": paid_count,
            "cash_count": cash_count,
            "open_count": unpaid_count,
            "online_revenue": round(online_revenue, 2),
            "cash_revenue": round(cash_revenue, 2),
            "total_revenue": round(total_revenue, 2),
            "occupancy_percent": round(occupancy, 1),
        },
        "payment_history": payment_history,
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
