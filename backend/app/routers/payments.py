from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trip, Seat, Payment
from app.schemas import MockPayment
from app.ws import manager

router = APIRouter()


async def finalize_seat_payment(
    db: Session,
    trip: Trip,
    seat: Seat,
    amount: float,
    source: str = "PAYFAST",
):
    if seat.status == "PAID":
        return {
            "message": "Seat already paid",
            "seat_status": seat.status,
            "already_paid": True,
        }

    if seat.status == "CASH":
        raise HTTPException(status_code=400, detail="Seat already settled with cash")

    payment = Payment(
        id=str(uuid4()),
        trip_id=trip.id,
        seat_id=seat.id,
        amount=amount,
        status=f"SUCCESS_{source}",
    )

    db.add(payment)
    seat.status = "PAID"
    db.commit()
    db.refresh(seat)

    await manager.broadcast(
        trip.id,
        {
            "type": "seat_update",
            "seat_id": seat.id,
            "seat_number": seat.seat_number,
            "status": seat.status,
        },
    )

    return {
        "message": f"{source} payment successful",
        "payment_id": payment.id,
        "seat_status": seat.status,
        "already_paid": False,
    }


@router.post("/payments/mock")
async def mock_payment(payload: MockPayment, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == payload.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    seat = db.query(Seat).filter(Seat.id == payload.seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    result = await finalize_seat_payment(
        db=db,
        trip=trip,
        seat=seat,
        amount=payload.amount,
        source="MOCK",
    )

    return result


@router.get("/payments/confirm", response_class=HTMLResponse)
async def payfast_confirm(
    seat_token: str,
    amount: float = 20.0,
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.qr_token == seat_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )
    if not trip:
        raise HTTPException(status_code=404, detail="Active trip not found")

    result = await finalize_seat_payment(
        db=db,
        trip=trip,
        seat=seat,
        amount=amount,
        source="PAYFAST_RETURN",
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment confirmed</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 40px auto;
                padding: 20px;
                background: #f7f7f7;
                color: #111;
            }}
            .card {{
                background: white;
                padding: 24px;
                border-radius: 16px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            }}
            .ok {{
                color: green;
                font-weight: bold;
            }}
            a {{
                color: #4b0082;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Payment confirmed</h1>
            <p>Seat <strong>{seat.seat_number}</strong> status: <span class="ok">{seat.status}</span></p>
            <p>{result["message"]}</p>
            <p><a href="/driver">Open driver view</a></p>
        </div>
    </body>
    </html>
    """


@router.post("/payments/payfast/itn")
async def payfast_itn(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()

    seat_token = form.get("custom_str1")
    amount_raw = form.get("amount_gross") or form.get("amount_net") or form.get("amount")
    payment_status = form.get("payment_status", "")

    if not seat_token:
        return JSONResponse({"ok": False, "error": "Missing custom_str1 seat token"}, status_code=400)

    seat = db.query(Seat).filter(Seat.qr_token == seat_token).first()
    if not seat:
        return JSONResponse({"ok": False, "error": "Seat not found"}, status_code=404)

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )
    if not trip:
        return JSONResponse({"ok": False, "error": "Active trip not found"}, status_code=404)

    try:
        amount = float(amount_raw) if amount_raw else 20.0
    except ValueError:
        amount = 20.0

    if payment_status.upper() not in {"COMPLETE", "COMPLETE "} and payment_status.lower() not in {"complete"}:
        return JSONResponse({"ok": True, "message": "Ignored non-complete payment"}, status_code=200)

    result = await finalize_seat_payment(
        db=db,
        trip=trip,
        seat=seat,
        amount=amount,
        source="PAYFAST_ITN",
    )

    return JSONResponse({"ok": True, **result}, status_code=200)


from fastapi.responses import HTMLResponse
import base64
from io import BytesIO
import qrcode

@router.get("/payments/snapscan/start", response_class=HTMLResponse)
def snapscan_start(
    trip_id: str,
    seat_id: str,
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not seat or not trip:
        raise HTTPException(status_code=404, detail="Invalid seat or trip")

    payment_link = f"/payments/snapscan/confirm?trip_id={trip_id}&seat_id={seat_id}"

    qr = qrcode.make(f"http://127.0.0.1:8000{payment_link}")
    buf = BytesIO()
    qr.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - SnapScan</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 18%, #EAF5FC 18%, #F7FBFF 100%);
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
            padding: 22px 16px 28px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
            text-align: center;
        }}
        .badge {{
            width: 88px;
            height: 88px;
            margin: 8px auto 18px;
            border-radius: 26px;
            background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.4rem;
            box-shadow: 0 16px 28px rgba(26,159,219,0.24);
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
        .detail-grid {{
            margin-top: 22px;
            display: grid;
            gap: 12px;
        }}
        .detail-card {{
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 14px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
            text-align: left;
        }}
        .detail-label {{
            color: #708798;
            font-size: 0.86rem;
            margin-bottom: 6px;
        }}
        .detail-value {{
            color: #0B3C5D;
            font-size: 1.08rem;
            font-weight: 800;
        }}
        .qr-wrap {{
            margin-top: 18px;
            background: #fff;
            border: 1px solid #E3EEF6;
            border-radius: 22px;
            padding: 18px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}
        .qr-wrap img {{
            width: 220px;
            margin: 0 auto;
            display: block;
            border-radius: 18px;
        }}
        .note {{
            margin-top: 14px;
            color: #7a909f;
            font-size: 0.92rem;
            line-height: 1.4;
        }}
        .actions {{
            display: grid;
            gap: 12px;
            margin-top: 22px;
        }}
        .btn {{
            display: block;
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
    </style>
</head>
<body>
    <div class="app">
        <div class="mobile-shell">
            <div class="topbar">TaxiPay</div>
            <div class="content">
                <div class="panel">
                    <div class="badge">📱</div>
                    <h1 class="title">SnapScan Payment</h1>
                    <p class="subtitle">Scan the QR with SnapScan or continue below to simulate a successful payment.</p>

                    <div class="detail-grid">
                        <div class="detail-card">
                            <div class="detail-label">Seat</div>
                            <div class="detail-value">{seat.seat_number}</div>
                        </div>
                        <div class="detail-card">
                            <div class="detail-label">Fare</div>
                            <div class="detail-value">R20.00</div>
                        </div>
                    </div>

                    <div class="qr-wrap">
                        <img src="data:image/png;base64,{img_b64}" alt="SnapScan QR" />
                        <div class="note">Point your phone at the code or use the button below.</div>
                    </div>

                    <div class="actions">
                        <a class="btn btn-primary" href="{payment_link}">Simulate SnapScan Payment →</a>
                        <a class="btn btn-secondary" href="/rider/{seat.qr_token}">Back to payment methods</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
@router.get("/payments/snapscan/confirm", response_class=HTMLResponse)
def snapscan_confirm(
    trip_id: str,
    seat_id: str,
    db: Session = Depends(get_db),
):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not seat or not trip:
        raise HTTPException(status_code=404, detail="Invalid seat or trip")

    existing_payment = (
        db.query(Payment)
        .filter(Payment.trip_id == trip_id, Payment.seat_id == seat.id)
        .first()
    )

    if seat.status != "PAID":
        seat.status = "PAID"

    payment = existing_payment

    if not payment:
        payment = Payment(
            id=str(uuid4()),
            trip_id=trip_id,
            seat_id=seat.id,
            amount=20.0,
            status="SUCCESS_SNAPSCAN_DEMO",
        )
        db.add(payment)

    db.commit()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>SnapScan Success</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 18%, #EAF5FC 18%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
        }}
        .app {{ min-height: 100vh; display: flex; justify-content: center; }}
        .shell {{ width: 100%; max-width: 430px; min-height: 100vh; }}
        .topbar {{ padding: 20px 16px 18px; color: white; font-weight: 800; font-size: 1.45rem; }}
        .content {{ padding: 0 12px 22px; }}
        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 22px 16px 28px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
            text-align: center;
        }}
        .badge {{
            width: 88px;
            height: 88px;
            margin: 8px auto 18px;
            border-radius: 26px;
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.4rem;
            box-shadow: 0 16px 28px rgba(39,174,96,0.24);
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
        .actions {{
            display: grid;
            gap: 12px;
            margin-top: 24px;
        }}
        .btn {{
            display: block;
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
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar">TaxiPay</div>
            <div class="content">
                <div class="panel">
                    <div class="badge">✓</div>
                    <h1 class="title">SnapScan Payment Successful</h1>
                    <p class="subtitle">Seat {seat.seat_number} is now marked as PAID.</p>
                    <div class="actions">
                        <a class="btn btn-primary" href="/payments/receipt/{payment.id}">View Receipt</a>
                        <a class="btn btn-secondary" href="/driver">Open Driver View</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


@router.get("/payments/history", response_class=HTMLResponse)
def payment_history(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(Payment.id.desc()).all()

    rows = ""
    for pay in payments:
        seat = db.query(Seat).filter(Seat.id == pay.seat_id).first()
        seat_no = seat.seat_number if seat else "Unknown"
        amount = f"R{float(pay.amount):.2f}" if pay.amount is not None else "R0.00"
        trip_short = pay.trip_id[:8] if pay.trip_id else "Unknown"

        rows += f"""
        <div class="item">
            <div>
                <div class="title">Seat {seat_no}</div>
                <div class="meta">Trip {trip_short} • {pay.status}</div>
            </div>
            <div style="text-align:right;">
                <div class="amount">{amount}</div>
                <a class="link" href="/payments/receipt/{pay.id}">View receipt</a>
            </div>
        </div>
        """

    if not rows:
        rows = '<div class="empty">No payments yet.</div>'

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - Payment History</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 18%, #EAF5FC 18%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
        }}
        .app {{ min-height: 100vh; display: flex; justify-content: center; }}
        .shell {{ width: 100%; max-width: 430px; min-height: 100vh; }}
        .topbar {{ padding: 20px 16px 18px; color: white; font-weight: 800; font-size: 1.45rem; }}
        .content {{ padding: 0 12px 22px; }}
        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 22px 16px 28px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
        }}
        .item {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}
        .title {{ color: #0B3C5D; font-size: 1.05rem; font-weight: 800; }}
        .meta {{ color: #6b8293; font-size: 0.9rem; margin-top: 4px; }}
        .amount {{ color: #0B3C5D; font-size: 1rem; font-weight: 800; }}
        .link {{ color: #0B72C6; text-decoration: none; font-weight: 800; font-size: 0.92rem; }}
        .empty {{
            text-align: center;
            color: #6b8293;
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 20px;
        }}
        .home {{
            display: block;
            text-align: center;
            margin-top: 16px;
            text-decoration: none;
            padding: 15px 16px;
            border-radius: 16px;
            background: #F2F8FC;
            color: #0B3C5D;
            border: 1px solid #DCEAF4;
            font-weight: 800;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar">TaxiPay</div>
            <div class="content">
                <div class="panel">
                    <h2 style="margin-top:0;color:#0B3C5D;">Payment History</h2>
                    {rows}
                    <a class="home" href="/master/tx100-master">Back to seats</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@router.get("/payments/receipt/{payment_id}", response_class=HTMLResponse)
def payment_receipt(payment_id: str, db: Session = Depends(get_db)):
    pay = db.query(Payment).filter(Payment.id == payment_id).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    seat = db.query(Seat).filter(Seat.id == pay.seat_id).first()
    seat_no = seat.seat_number if seat else "Unknown"
    amount = f"R{float(pay.amount):.2f}" if pay.amount is not None else "R0.00"
    trip_short = pay.trip_id[:8] if pay.trip_id else "Unknown"

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay - Receipt</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 18%, #EAF5FC 18%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
        }}
        .app {{ min-height: 100vh; display: flex; justify-content: center; }}
        .shell {{ width: 100%; max-width: 430px; min-height: 100vh; }}
        .topbar {{ padding: 20px 16px 18px; color: white; font-weight: 800; font-size: 1.45rem; }}
        .content {{ padding: 0 12px 22px; }}
        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px 26px 0 0;
            min-height: calc(100vh - 90px);
            padding: 22px 16px 28px;
            box-shadow: 0 -8px 22px rgba(11,60,93,0.08);
            text-align: center;
        }}
        .badge {{
            width: 88px;
            height: 88px;
            margin: 8px auto 18px;
            border-radius: 26px;
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.4rem;
            box-shadow: 0 16px 28px rgba(39,174,96,0.24);
        }}
        .card {{
            text-align: left;
            background: white;
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
            margin-top: 18px;
        }}
        .label {{ color: #708798; font-size: 0.88rem; margin-bottom: 6px; }}
        .value {{ color: #0B3C5D; font-size: 1.08rem; font-weight: 800; margin-bottom: 14px; }}
        .btn {{
            display: block;
            text-decoration: none;
            border-radius: 18px;
            padding: 16px 18px;
            font-weight: 800;
            font-size: 1rem;
            text-align: center;
            margin-top: 18px;
            background: linear-gradient(180deg, #1A9FDB 0%, #0B72C6 100%);
            color: white;
            box-shadow: 0 14px 24px rgba(26,159,219,0.24);
        }}
        .btn-secondary {{
            display: block;
            text-decoration: none;
            border-radius: 18px;
            padding: 16px 18px;
            font-weight: 800;
            font-size: 1rem;
            text-align: center;
            margin-top: 12px;
            background: #F2F8FC;
            color: #0B3C5D;
            border: 1px solid #DCEAF4;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar">TaxiPay</div>
            <div class="content">
                <div class="panel">
                    <div class="badge">✓</div>
                    <h2 style="margin:0;color:#0B3C5D;">Payment Receipt</h2>
                    <div class="card">
                        <div class="label">Seat</div>
                        <div class="value">{seat_no}</div>
                        <div class="label">Amount</div>
                        <div class="value">{amount}</div>
                        <div class="label">Status</div>
                        <div class="value">{pay.status}</div>
                        <div class="label">Trip</div>
                        <div class="value">{trip_short}</div>
                        <div class="label">Payment ID</div>
                        <div class="value">{pay.id[:8]}</div>
                    </div>
                    <a class="btn" href="/payments/history">View all payments</a>
                    <a class="btn-secondary" href="/master/tx100-master">Back to seats</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
