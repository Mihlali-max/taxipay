import hashlib
import logging
import os
import uuid
from decimal import Decimal
from urllib.parse import quote_plus

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
PAYFAST_MERCHANT_ID = os.getenv("PAYFAST_MERCHANT_ID", "10000100").strip()
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_MERCHANT_KEY", "46f0cd694581a").strip()
PAYFAST_PASSPHRASE = os.getenv("PAYFAST_PASSPHRASE", "jt7N0E43FZPn").strip()
BASE_URL = os.getenv("BASE_URL", "https://taxipay-api.onrender.com").strip()

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


def generate_signature(data: dict, passphrase: str | None = None) -> str:
    items = []
    for key in sorted(data.keys()):
        value = data[key]
        if value is None or str(value).strip() == "":
            continue
        items.append(f"{key}={quote_plus(str(value).strip(), safe='')}")
    param_string = "&".join(items)

    if passphrase:
        param_string += f"&passphrase={quote_plus(passphrase.strip(), safe='')}"

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

    merchant_payment_id = str(uuid.uuid4())

    data = {
        "merchant_id": PAYFAST_MERCHANT_ID,
        "merchant_key": PAYFAST_MERCHANT_KEY,
        "return_url": f"{BASE_URL}/payments/payfast/return?trip_id={trip_id}&seat_token={seat.qr_token}",
        "cancel_url": f"{BASE_URL}/payments/payfast/cancel?trip_id={trip_id}&seat_token={seat.qr_token}",
        "notify_url": f"{BASE_URL}/payments/payfast/notify",
        "m_payment_id": merchant_payment_id,
        "amount": f"{FARE_AMOUNT:.2f}",
        "item_name": f"Taxi Seat {seat.seat_number}",
        "item_description": f"TaxiPay seat payment for seat {seat.seat_number}",
        "custom_str1": seat.qr_token,
        "custom_str2": trip.id,
    }

    data["signature"] = generate_signature(data, PAYFAST_PASSPHRASE)

    logger.info(
        "PayFast start payload: merchant_id=%s return_url=%s notify_url=%s amount=%s seat_token=%s trip_id=%s",
        PAYFAST_MERCHANT_ID,
        data["return_url"],
        data["notify_url"],
        data["amount"],
        seat.qr_token,
        trip_id,
    )

    return build_auto_submit_form(PAYFAST_PROCESS_URL, data)


@router.post("/payments/payfast/notify")
async def payfast_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    payload = dict(form)

    seat_token = payload.get("custom_str1")
    trip_id = payload.get("custom_str2")
    payment_status = payload.get("payment_status", "")
    received_signature = payload.get("signature", "")

    logger.info(
        "PayFast notify received: payment_status=%s seat_token=%s trip_id=%s",
        payment_status,
        seat_token,
        trip_id,
    )

    if not seat_token or not trip_id:
        return PlainTextResponse("OK", status_code=200)

    signature_payload = {k: v for k, v in payload.items() if k != "signature"}
    expected_signature = generate_signature(signature_payload, PAYFAST_PASSPHRASE)

    if received_signature != expected_signature:
        logger.warning(
            "Invalid PayFast signature for seat_token=%s trip_id=%s expected=%s received=%s",
            seat_token,
            trip_id,
            expected_signature,
            received_signature,
        )
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
        seat = db.query(Seat).filter(Seat.qr_token == seat_token).first()

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
            logger.info("Seat marked PAID via PayFast: seat_token=%s trip_id=%s", seat_token, trip_id)
            await notify_trip_update(trip_id)

    return PlainTextResponse("OK", status_code=200)


@router.get("/payments/payfast/return", response_class=HTMLResponse)
def payfast_return(
    trip_id: str = Query(...),
    seat_token: str = Query(...),
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.qr_token == seat_token).first()
    status = seat.status if seat else "UNKNOWN"

    if status == "PAID":
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - Payment Successful</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 20%, #EAF5FC 20%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
        }}
        .app {{
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }}
        .mobile-shell {{
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .topbar {{
            padding: 20px 16px 18px;
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 800;
            font-size: 1.45rem;
        }}
        .content {{
            flex: 1;
            padding: 0 12px 22px;
        }}
        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 22px 16px 28px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
            text-align: center;
        }}
        .success-badge {{
            width: 96px;
            height: 96px;
            margin: 8px auto 18px;
            border-radius: 28px;
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3rem;
            box-shadow: 0 16px 28px rgba(39, 174, 96, 0.28);
        }}
        .title {{
            margin: 0;
            color: #0B3C5D;
            font-size: 1.6rem;
            font-weight: 800;
        }}
        .subtitle {{
            margin: 10px 0 0;
            color: #6b8293;
            font-size: 0.98rem;
            line-height: 1.45;
        }}
        .details {{
            margin-top: 22px;
            display: grid;
            gap: 12px;
        }}
        .detail-card {{
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
            text-align: left;
        }}
        .detail-label {{
            color: #708798;
            font-size: 0.88rem;
            margin-bottom: 6px;
        }}
        .detail-value {{
            color: #0B3C5D;
            font-size: 1.15rem;
            font-weight: 800;
        }}
        .actions {{
            display: grid;
            gap: 12px;
            margin-top: 24px;
        }}
        .btn {{
            display: block;
            width: 100%;
            text-decoration: none;
            border-radius: 18px;
            padding: 16px 18px;
            font-weight: 800;
            font-size: 1rem;
            text-align: center;
        }}
        .btn-primary {{
            background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
            color: white;
            box-shadow: 0 14px 24px rgba(26,159,219,0.24);
        }}
        .btn-secondary {{
            background: #F2F8FC;
            color: #0B3C5D;
            border: 1px solid #DCEAF4;
        }}
        .note {{
            margin-top: 18px;
            color: #7a909f;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="mobile-shell">
            <div class="topbar">
                <span>TaxiPay</span>
            </div>
            <div class="content">
                <div class="panel">
                    <div class="success-badge">✓</div>
                    <h1 class="title">Payment Successful</h1>
                    <p class="subtitle">
                        Your seat payment has been confirmed successfully.
                    </p>

                    <div class="details">
                        <div class="detail-card">
                            <div class="detail-label">Seat</div>
                            <div class="detail-value">{seat.seat_number if seat else "Unknown"}</div>
                        </div>
                        <div class="detail-card">
                            <div class="detail-label">Status</div>
                            <div class="detail-value">{status}</div>
                        </div>
                        <div class="detail-card">
                            <div class="detail-label">Trip</div>
                            <div class="detail-value">{trip_id[:8]}</div>
                        </div>
                    </div>

                    <div class="actions">
                        <a class="btn btn-primary" href="/driver">Open Driver View</a>
                        <a class="btn btn-secondary" href="/master/tx100-master">Back to Seats</a>
                    </div>

                    <div class="note">Thank you for using TaxiPay.</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - Payment Processing</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <meta http-equiv="refresh" content="3">
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 20%, #EAF5FC 20%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
        }}
        .app {{
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }}
        .mobile-shell {{
            width: 100%;
            max-width: 430px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .topbar {{
            padding: 20px 16px 18px;
            color: white;
            font-weight: 800;
            font-size: 1.45rem;
        }}
        .content {{
            flex: 1;
            padding: 0 12px 22px;
        }}
        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 24px 16px 28px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
            text-align: center;
        }}
        .loader {{
            width: 84px;
            height: 84px;
            margin: 8px auto 18px;
            border-radius: 50%;
            border: 8px solid #D9ECF8;
            border-top-color: #1A9FDB;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .title {{
            margin: 0;
            color: #0B3C5D;
            font-size: 1.5rem;
            font-weight: 800;
        }}
        .subtitle {{
            margin: 10px 0 0;
            color: #6b8293;
            font-size: 0.98rem;
            line-height: 1.45;
        }}
        .status-card {{
            margin-top: 22px;
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}
        .status-label {{
            color: #708798;
            font-size: 0.88rem;
            margin-bottom: 6px;
        }}
        .status-value {{
            color: #0B3C5D;
            font-size: 1.15rem;
            font-weight: 800;
        }}
        .link {{
            display: inline-block;
            margin-top: 20px;
            color: #0B72C6;
            text-decoration: none;
            font-weight: 800;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="mobile-shell">
            <div class="topbar">TaxiPay</div>
            <div class="content">
                <div class="panel">
                    <div class="loader"></div>
                    <h1 class="title">Payment Processing</h1>
                    <p class="subtitle">
                        Your payment is being confirmed. This page refreshes automatically.
                    </p>

                    <div class="status-card">
                        <div class="status-label">Current seat status</div>
                        <div class="status-value">{status}</div>
                    </div>

                    <a class="link" href="/driver">Open driver view</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


@router.get("/payments/payfast/cancel", response_class=HTMLResponse)
def payfast_cancel(
    trip_id: str | None = Query(default=None),
    seat_token: str | None = Query(default=None),
):
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Payment Cancelled</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 420px;
            margin: 40px auto;
            padding: 20px;
            background: #f7f7f7;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        a {
            color: #0B72C6;
            text-decoration: none;
            font-weight: 700;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>Payment cancelled</h2>
        <p>No payment was completed.</p>
        <p><a href="/master/tx100-master">Back to seats</a></p>
    </div>
</body>
</html>
"""
