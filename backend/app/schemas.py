from pydantic import BaseModel


class TaxiCreate(BaseModel):
    vehicle_code: str
    route_name: str
    seat_count: int


class TripStart(BaseModel):
    taxi_id: str


class MockPayment(BaseModel):
    trip_id: str
    seat_id: str
    amount: float
