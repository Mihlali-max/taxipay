from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import Taxi, Seat, Trip


def seed_demo_data(db: Session):
    taxi = db.query(Taxi).filter(Taxi.vehicle_code == "TX100").first()

    if not taxi:
        taxi = Taxi(
            id=str(uuid4()),
            vehicle_code="TX100",
            route_name="Town to Khayelitsha",
            seat_count=15,
        )
        db.add(taxi)
        db.commit()
        db.refresh(taxi)

    # ensure all 15 seats exist
    existing_seat_numbers = {
        seat.seat_number
        for seat in db.query(Seat).filter(Seat.taxi_id == taxi.id).all()
    }

    for i in range(1, 16):
        if i not in existing_seat_numbers:
            seat = Seat(
                id=str(uuid4()),
                taxi_id=taxi.id,
                seat_number=i,
                qr_token=f"tx100-seat-{i}",
                status="UNPAID",
            )
            db.add(seat)

    # ensure there is at least one active trip
    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE")
        .first()
    )

    if not active_trip:
        trip = Trip(
            id=str(uuid4()),
            taxi_id=taxi.id,
            status="ACTIVE",
        )
        db.add(trip)

    db.commit()
