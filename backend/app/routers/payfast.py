import hashlib
import logging
import os
import uuid
from decimal import Decimal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Seat, Trip
from app.ws import manager

router = APIRouter()
logger = logging.getLogger(__name__)

PAYFAST_SANDBOX = os.getenv("PAYFAST_SANDBOX", "true").lower() == "true"
PAYFAST_MERCHANT_ID = os.getenv("PAYFAST_MERCHANT_ID", "10000100")
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_MERCHANT_KEY", "46f0cd694581a")
PAYFAST_PASSPHRASE = os.getenv("PAYFAST_PASSPHRASE", "jt7NOE43FZPn")
BASE_URL = os.getenv("BASE_URL", "https://taxipay-api.onrender.com")

PAYFAST_PROCESS_URL = (
    "https://sandbox.payfast.co.za/eng/process"
    if PAYFAST_SANDBOX
    else "https://www.payfast.co.za/eng/process"
)

PAYFAST_VALIDATE_URL = (
    "https://sandbox.payfast.co.za/eng/query/validate"
    if PAYFAST_SANDBOX
    else "https://www.payfast.co.za/eng/query/validate"
)

FARE_AMOUNT = Decimal("20.00")


def _pf_encode(value: str) -> str:
    return urlencode({"x": value}).split("=", 1)[1]


def generate_signature(data: dict, passphrase: str | None = None) -> str:
    pairs = []
    for key, value in data.items():
        if value is None or str(value).strip() == "":
            continue
        pairs.append(f"{key}={_pf_encode(str(value).strip())}")

    param_string = "&".join(pairs)

    if passphrase:
        param_string += f"&passphrase={_pf_encode(passphrase.strip())}"

    return hashlib.md5(param_string.encode("utf-8")).hexdigest()


def build_auto_submit_form(action: str, data: dict) -> str:
    inputs = "\n".join(
        f"<input type='hidden' name='{k}' value='{str(v)}' />"
        for k, v in data.items()
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Redirecting to PayFast</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body style="font-family: Arial, sans-serif; max-width: 420px; margin: 40px auto;">
    <h2>Redirecting to PayFast...</h2>
    <p>Please wait while we take you to the secure payment page.</p>
    <form id="payfast-form" action="{action}" method="post">
        {inputs}
        <noscript><button type="submit">Continue to PayFast</button></noscript>
    </form>
    <script>
        document.getElementById("payfast-form").submit();
    </script>
</body>
</html>
"""


async def validate_with_payfast(payload: dict) -> bool:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            PAYFAST_VALIDATE_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return response.text.strip() == "VALID"


async def notify_trip_update(trip_id: str) -> None:
    for method_name in [
        "broadcast_to_trip",
        "broadcast_trip",
        "notify_trip",
        "send_trip_update",
        "broadcast",
    ]:
        method = getattr(manager, method_name, None)
        if callable(method):
            try:
                result = method(
                    trip_id,
                    {"type": "seat_update", "trip_id": trip_id},
                )
                if hasattr(result, "__await__"):
                    await result
                return
            except TypeError:
                try:
                    result = method({"type": "seat_update", "trip_id": trip_id})
                    if hasattr(result, "__await__"):
                        await result
                    return
                except Exception:
                    pass
            except Exception:
                pass


@router.get("/payments/payfast/start", response_class=HTMLResponse)
def start_payfast_payment(
    trip_id: str = Query(...),
    seat_id: str = Query(...),
    db: Session = Depends(get_db),
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    if seat.taxi_id != trip.taxi_id:
        raise HTTPException(status_code=400, detail="Seat does not belong to this trip")

    if seat.status == "PAID":
        raise HTTPException(status_code=400, detail="Seat already paid")

    logger.info("Starting PayFast payment: trip_id=%s seat_id=%s", trip_id, seat_id)

    merchant_payment_id = str(uuid.uuid4())

    data = {
        "merchant_id": PAYFAST_MERCHANT_ID,
        "merchant_key": PAYFAST_MERCHANT_KEY,
        "return_url": f"{BASE_URL}/payments/payfast/return?trip_id={trip_id}&seat_id={seat_id}",
        "cancel_url": f"{BASE_URL}/payments/payfast/cancel?trip_id={trip_id}&seat_id={seat_id}",
        "notify_url": f"{BASE_URL}/payments/payfast/notify",
        "m_payment_id": merchant_payment_id,
        "amount": f"{FARE_AMOUNT:.2f}",
        "item_name": f"Taxi Seat {seat.seat_number}",
        "item_description": f"TaxiPay seat payment for seat {seat.seat_number}",
        "custom_str1": seat.id,
        "custom_str2": trip.id,
        "custom_str3": seat.qr_token,
    }

    data["signature"] = generate_signature(data, PAYFAST_PASSPHRASE)
    return build_auto_submit_form(PAYFAST_PROCESS_URL, data)


@router.post("/payments/payfast/notify")
async def payfast_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    payload = dict(form)

    seat_id = payload.get("custom_str1")
    trip_id = payload.get("custom_str2")
    payment_status = payload.get("payment_status", "")
    received_signature = payload.get("signature", "")

    logger.info(
        "PayFast notify received: payment_status=%s seat_id=%s trip_id=%s",
        payment_status,
        seat_id,
        trip_id,
    )

    if not seat_id or not trip_id:
        return PlainTextResponse("OK", status_code=200)

    signature_payload = {k: v for k, v in payload.items() if k != "signature"}
    expected_signature = generate_signature(signature_payload, PAYFAST_PASSPHRASE)

    if received_signature != expected_signature:
        logger.warning("Invalid PayFast signature for seat_id=%s trip_id=%s", seat_id, trip_id)
        return PlainTextResponse("OK", status_code=200)

    try:
        amount_gross = Decimal(str(payload.get("amount_gross", "0")))
    except Exception:
        return PlainTextResponse("OK", status_code=200)

    if abs(amount_gross - FARE_AMOUNT) > Decimal("0.01"):
        return PlainTextResponse("OK", status_code=200)

    try:
        is_valid = await validate_with_payfast(payload)
    except Exception:
        return PlainTextResponse("OK", status_code=200)

    if not is_valid:
        return PlainTextResponse("OK", status_code=200)

    if payment_status == "COMPLETE":
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        seat = db.query(Seat).filter(Seat.id == seat_id).first()

        if trip and seat and seat.taxi_id == trip.taxi_id:
            existing_payment = (
                db.query(Payment)
                .filter(Payment.trip_id == trip.id, Payment.seat_id == seat.id)
                .first()
            )

            if seat.status != "PAID":
                seat.status = "PAID"

            if not existing_payment:
                payment = Payment(
                    id=str(uuid.uuid4()),
                    trip_id=trip.id,
                    seat_id=seat.id,
                    amount=float(amount_gross),
                    status="SUCCESS_PAYFAST",
                )
                db.add(payment)

            db.commit()
            logger.info("Seat marked PAID via PayFast: seat_id=%s trip_id=%s", seat_id, trip_id)
            await notify_trip_update(trip_id)

    return PlainTextResponse("OK", status_code=200)


@router.get("/payments/payfast/return", response_class=HTMLResponse)
def payfast_return(
    trip_id: str = Query(...),
    seat_id: str = Query(...),
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    status = seat.status if seat else "UNKNOWN"

    if status == "PAID":
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Payment Successful</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 420px;
            margin: 40px auto;
            padding: 20px;
            background: #f7f7f7;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .ok {{
            color: green;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Payment successful</h2>
        <p class="ok">Seat payment confirmed.</p>
        <p><strong>Seat status:</strong> {status}</p>
        <p><a href="/driver">Open driver view</a></p>
    </div>
</body>
</html>
"""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Payment Return</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta http-equiv="refresh" content="3">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 420px;
            margin: 40px auto;
            padding: 20px;
            background: #f7f7f7;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Payment processing</h2>
        <p>Your payment is being confirmed.</p>
        <p><strong>Current seat status:</strong> {status}</p>
        <p>This page refreshes automatically.</p>
        <p><a href="/driver">Open driver view</a></p>
    </div>
</body>
</html>
"""


@router.get("/payments/payfast/cancel", response_class=HTMLResponse)
def payfast_cancel():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Payment Cancelled</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body style="font-family: Arial, sans-serif; max-width: 420px; margin: 40px auto;">
    <h2>Payment cancelled</h2>
    <p>No payment was completed.</p>
</body>
</html>
"""
