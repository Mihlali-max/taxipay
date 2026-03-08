from sqlalchemy import Column, String, Integer, Float, DateTime
from datetime import datetime

from app.db import Base


class Taxi(Base):
    __tablename__ = "taxis"

    id = Column(String, primary_key=True, index=True)
    vehicle_code = Column(String, nullable=False)
    route_name = Column(String, nullable=False)
    seat_count = Column(Integer, nullable=False)


class Seat(Base):
    __tablename__ = "seats"

    id = Column(String, primary_key=True, index=True)
    taxi_id = Column(String, nullable=False, index=True)
    seat_number = Column(Integer, nullable=False)
    qr_token = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, default="UNPAID")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True)
    taxi_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="ACTIVE")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, nullable=False, index=True)
    seat_id = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="SUCCESS")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
