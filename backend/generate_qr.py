import os
import re
import qrcode

from app.db import SessionLocal
from app.models import Seat, Taxi

BASE_URL = "https://taxipay-api.onrender.com/rider"
OUTPUT_DIR = "qrs"


def safe_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    db = SessionLocal()
    try:
        seats = db.query(Seat).order_by(Seat.taxi_id, Seat.seat_number).all()

        if not seats:
            print("No seats found in database.")
            return

        for seat in seats:
            taxi = db.query(Taxi).filter(Taxi.id == seat.taxi_id).first()
            if not taxi:
                print(f"Skipping seat {seat.id}: taxi not found")
                continue

            url = f"{BASE_URL}/{seat.qr_token}"

            taxi_code = safe_name(taxi.vehicle_code)
            filename = f"{taxi_code}-seat-{seat.seat_number}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)

            img = qrcode.make(url)
            img.save(filepath)

            print(f"Created {filepath} -> {url}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
