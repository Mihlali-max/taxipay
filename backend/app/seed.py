from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import Taxi, Seat, Trip


def seed_demo_data(db: Session):
    existing = db.query(Taxi).filter(Taxi.vehicle_code == "TX100").first()
    if existing:
        return

    taxi_id = str(uuid4())

    taxi = Taxi(
        id=taxi_id,
        vehicle_code="TX100",
        route_name="Town to Khayelitsha",
        seat_count=15,  # 15 passenger seats, 16 incl driver
    )
    db.add(taxi)

    for i in range(1, 16):
        seat = Seat(
            id=str(uuid4()),
            taxi_id=taxi_id,
            seat_number=i,
            qr_token=f"tx100-seat-{i}",
            status="UNPAID",
        )
        db.add(seat)

    trip = Trip(
        id=str(uuid4()),
        taxi_id=taxi_id,
        status="ACTIVE",
    )
    db.add(trip)

    db.commit()
