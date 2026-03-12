import os
import qrcode

from app.db import SessionLocal
from app.models import Seat

# Render URL
BASE_URL = "https://taxipay-api.onrender.com"

QR_DIR = "qrs"


def make_qr(url: str, filepath: str):
    img = qrcode.make(url)
    img.save(filepath)


def main():
    os.makedirs(QR_DIR, exist_ok=True)

    db = SessionLocal()

    try:
        seats = db.query(Seat).order_by(Seat.taxi_id, Seat.seat_number).all()

        if not seats:
            print("No seats found.")
            return

        processed_taxis = set()

        for seat in seats:
            rider_url = f"{BASE_URL}/rider/{seat.qr_token}"
            rider_file = os.path.join(QR_DIR, f"{seat.qr_token}.png")

            make_qr(rider_url, rider_file)
            print(f"Created {rider_file} -> {rider_url}")

            # create master QR once per taxi
            if seat.taxi_id not in processed_taxis:
                driver_url = f"{BASE_URL}/driver"
                master_file = os.path.join(QR_DIR, f"{seat.taxi_id}-master.png")

                make_qr(driver_url, master_file)
                print(f"Created {master_file} -> {driver_url}")

                processed_taxis.add(seat.taxi_id)

    finally:
        db.close()


if __name__ == "__main__":
    main()
