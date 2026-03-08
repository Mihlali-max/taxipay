from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Taxi, Seat
from app.schemas import TaxiCreate

router = APIRouter()


@router.post("/taxis")
def create_taxi(payload: TaxiCreate, db: Session = Depends(get_db)):
    taxi_id = str(uuid4())

    taxi = Taxi(
        id=taxi_id,
        vehicle_code=payload.vehicle_code,
        route_name=payload.route_name,
        seat_count=payload.seat_count,
    )
    db.add(taxi)

    created_seats = []
    for i in range(1, payload.seat_count + 1):
        seat = Seat(
            id=str(uuid4()),
            taxi_id=taxi_id,
            seat_number=i,
            qr_token=f"{payload.vehicle_code.lower()}-seat-{i}",
            status="UNPAID",
        )
        db.add(seat)
        created_seats.append(seat)

    db.commit()

    return {
        "taxi": {
            "id": taxi.id,
            "vehicle_code": taxi.vehicle_code,
            "route_name": taxi.route_name,
            "seat_count": taxi.seat_count,
        },
        "seats": [
            {
                "id": s.id,
                "taxi_id": s.taxi_id,
                "seat_number": s.seat_number,
                "qr_token": s.qr_token,
                "status": s.status,
            }
            for s in created_seats
        ],
    }
