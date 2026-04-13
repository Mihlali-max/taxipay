from uuid import uuid4
import os

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trip, Seat, Payment
from app.schemas import MockPayment
from app.ws import manager

router = APIRouter()
BASE_URL = os.getenv("BASE_URL", "https://fareflow.onrender.com")


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
    amount: float = None,
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
    <link rel="manifest" href="/static/manifest.json" />
    <link rel="apple-touch-icon" href="/static/icon-192.png" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="FareFlow" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
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
    <script>
if ('serviceWorker' in navigator) {{
    window.addEventListener('load', function() {{
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(reg) {{ console.log('SW registered'); }})
            .catch(function(err) {{ console.log('SW error', err); }});
    }});
}}
</script>
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
        amount = float(amount_raw) if amount_raw else trip.fare_amount
    except ValueError:
        amount = trip.fare_amount

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

    qr = qrcode.make(f"{BASE_URL}{payment_link}")
    buf = BytesIO()
    qr.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - SnapScan</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
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
            background: transparent;
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
            color: white;
            font-size: 1.6rem;
            font-weight: 800;
        }}
        .subtitle {{
            margin: 10px 0 0;
            color: rgba(255,255,255,0.45);
            font-size: 0.98rem;
            line-height: 1.45;
        }}
        .detail-grid {{
            margin-top: 22px;
            display: grid;
            gap: 12px;
        }}
        .detail-card {{
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 14px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
            text-align: left;
        }}
        .detail-label {{
            color: rgba(255,255,255,0.45);
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        .detail-value {{
            color: white;
            font-size: 1.2rem;
            font-weight: 800;
        }}
        .qr-wrap {{
            margin-top: 18px;
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 22px;
            padding: 18px;
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
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="mobile-shell">
            <div class="topbar"><span style="font-size:1.1rem;">🚕</span> FareFlow</div>
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
                            <div class="detail-value">R{trip.fare_amount:.2f}</div>
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
            amount=trip.fare_amount,
            status="SUCCESS_SNAPSCAN_DEMO",
        )
        db.add(payment)

    db.commit()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - Payment Successful</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
        }}
        .app {{ min-height: 100vh; display: flex; justify-content: center; }}
        .shell {{ width: 100%; max-width: 430px; min-height: 100vh; }}
        .topbar {{ padding: 20px 16px 18px; color: white; font-weight: 800; font-size: 1.1rem; }}
        .content {{ padding: 0 12px 22px; }}
        .panel {{
            background: transparent;
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
            color: white;
            font-size: 1.6rem;
            font-weight: 800;
        }}
        .subtitle {{
            margin: 10px 0 0;
            color: rgba(255,255,255,0.45);
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
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar"><span style="font-size:1.1rem;">🚕</span> FareFlow</div>
            <div class="content">
                <div class="panel">
                    <div class="badge">✓</div>
                    <h1 class="title">SnapScan Payment Successful</h1>
                    <p class="subtitle">Seat {seat.seat_number} is now marked as PAID.</p>
                    <div class="actions">
                        <a class="btn btn-primary" href="/rider/dashboard/{payment.seat_id}">My Trip Dashboard</a>
                        <a class="btn btn-secondary" href="/payments/receipt/{payment.id}">View Receipt</a>
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
    active_trip = (
        db.query(Trip)
        .filter(Trip.status == "ACTIVE")
        .order_by(Trip.started_at.desc())
        .first()
    )

    if active_trip:
        payments = (
            db.query(Payment)
            .filter(Payment.trip_id == active_trip.id)
            .order_by(Payment.created_at.desc())
            .all()
        )
    else:
        payments = []

    rows = ""
    for pay in payments:
        seat = db.query(Seat).filter(Seat.id == pay.seat_id).first()
        seat_no = seat.seat_number if seat else "Unknown"
        amount = f"R{float(pay.amount):.2f}" if pay.amount is not None else "R0.00"
        time = pay.created_at.strftime("%d %b %H:%M") if getattr(pay, "created_at", None) else ""
        status_labels = {
            "SUCCESS_SNAPSCAN_DEMO": "Paid via SnapScan",
            "SUCCESS_SNAPSCAN": "Paid via SnapScan",
            "SUCCESS_PAYFAST": "Paid via Card",
            "SUCCESS_CASH": "Paid in Cash",
        }
        status_label = status_labels.get(pay.status, pay.status)
        icon = "💳" if "PAYFAST" in pay.status else "📱" if "SNAPSCAN" in pay.status else "💵"
        rows += f"""
        <div class="item">
            <div>
                <div class="title" style="color:white;font-weight:800;">{icon} Seat {seat_no}</div>
                <div class="meta">{status_label} · {time}</div>
            </div>
            <div style="text-align:right;">
                <div class="amount" style="color:#1A9FDB;font-weight:800;font-size:1rem;">{amount}</div>
                <a class="link" href="/payments/receipt/{pay.id}">View receipt</a>
            </div>
        </div>
        """

    if not rows:
        rows = '<div class="empty">No payments yet. Start your first ride 🚕</div>'

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - Payment History</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
        }}
        .app {{ min-height: 100vh; display: flex; justify-content: center; }}
        .shell {{ width: 100%; max-width: 430px; min-height: 100vh; }}
        .topbar {{ padding: 20px 16px 18px; color: white; font-weight: 800; font-size: 1.1rem; }}
        .content {{ padding: 0 12px 22px; }}
        .panel {{
            background: transparent;
        }}
        .item {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}
        .title {{ color: #0B3C5D; font-size: 1.05rem; font-weight: 800; }}
        .meta {{ color: rgba(255,255,255,0.45); font-size: 0.9rem; margin-top: 4px; }}
        .amount {{ color: #0B3C5D; font-size: 1rem; font-weight: 800; }}
        .link {{ color: #1A9FDB; text-decoration: none; font-weight: 800; font-size: 0.92rem; }}
        .empty {{
            text-align: center;
            color: rgba(255,255,255,0.45);
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
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
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
            font-weight: 800;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar"><span style="font-size:1.1rem;">🚕</span> FareFlow</div>
            <div class="content">
                <div class="panel">
                    <h2 style="margin-top:0;color:white;font-size:1.1rem;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;">Payment History</h2>
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
    STATUS_LABELS = {
        "SUCCESS_SNAPSCAN_DEMO": "Paid via SnapScan",
        "SUCCESS_SNAPSCAN": "Paid via SnapScan",
        "SUCCESS_PAYFAST": "Paid via Card",
        "SUCCESS_CASH": "Paid in Cash",
    }
    pay = db.query(Payment).filter(Payment.id == payment_id).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    seat = db.query(Seat).filter(Seat.id == pay.seat_id).first()
    seat_no = seat.seat_number if seat else "Unknown"
    amount = f"R{float(pay.amount):.2f}" if pay.amount is not None else "R0.00"
    trip_short = pay.trip_id[:8] if pay.trip_id else "Unknown"
    status_labels = {
        "SUCCESS_SNAPSCAN_DEMO": "Paid via SnapScan",
        "SUCCESS_SNAPSCAN": "Paid via SnapScan",
        "SUCCESS_PAYFAST": "Paid via Card",
        "SUCCESS_CASH": "Paid in Cash",
    }
    status_label = status_labels.get(pay.status, pay.status)
    seat_id = pay.seat_id or ""
    seat_number = seat.seat_number if seat else 0
    from app.route_coords import get_route_coords
    import json as _json
    _trip = db.query(__import__("app.models", fromlist=["Trip"]).Trip).filter_by(id=pay.trip_id).first()
    _taxi = db.query(__import__("app.models", fromlist=["Taxi"]).Taxi).filter_by(id=_trip.taxi_id).first() if _trip else None
    _route_name = _taxi.route_name if _taxi else "Cape Town"
    route_coords_json = _json.dumps(get_route_coords(_route_name))
    taxi_route = _route_name

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FareFlow - Receipt</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#060f1a" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #060f1a;
            min-height: 100vh;
            color: white;
        }}
        .app {{ min-height: 100vh; display: flex; justify-content: center; }}
        .shell {{ width: 100%; max-width: 430px; min-height: 100vh; }}
        .topbar {{ padding: 20px 16px 18px; color: white; font-weight: 800; font-size: 1.1rem; }}
        .content {{ padding: 0 12px 22px; }}
        .panel {{
            background: transparent;
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
            background: #0d1f2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
            margin-top: 18px;
        }}
        .label {{ color: #708798; font-size: 0.88rem; margin-bottom: 6px; }}
        .value {{ color: white; font-size: 1.08rem; font-weight: 800; margin-bottom: 14px; }}
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
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar"><span style="font-size:1.1rem;">🚕</span> FareFlow</div>
            <div class="content">
                <div class="panel">
                    <div class="badge">✓</div>
                    <h2 style="margin:0 0 16px;color:white;font-size:1.4rem;font-weight:800;">Payment Receipt</h2>
                    <div class="card">
                        <div class="label">Seat</div>
                        <div class="value">{seat_no}</div>
                        <div class="label">Amount</div>
                        <div class="value">{amount}</div>
                        <div class="label">Status</div>
                        <div class="value" style="color:#4ac96b;">{status_label}</div>
                        <div class="label">Trip</div>
                        <div class="value">{trip_short}</div>
                        <div class="label">Payment ID</div>
                        <div class="value">{pay.id[:8]}</div>
                    </div>
                    <div style="margin-top:16px;margin-bottom:16px;">
                        <button onclick="openDropoffModal()"
                            style="width:100%;padding:15px;border:none;border-radius:18px;background:rgba(26,159,219,0.12);border:1px solid rgba(26,159,219,0.25);color:#6dd5fa;font-weight:800;font-size:0.95rem;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:10px;">
                            📍 Set My Drop-off Stop
                        </button>
                        <div id="dropoffSentInline" style="display:none;margin-top:10px;text-align:center;padding:12px;background:rgba(74,201,107,0.1);border:1px solid rgba(74,201,107,0.25);border-radius:14px;">
                            <div style="color:#4ac96b;font-weight:800;">✅ Driver Notified!</div>
                            <div id="dropoffAddrInline" style="color:rgba(255,255,255,0.5);font-size:0.82rem;margin-top:4px;"></div>
                        </div>
                    </div>

                    <!-- Drop-off Modal -->
                    <div id="dropoffModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.88);z-index:9999;flex-direction:column;">
                        <div style="background:#0d1f2e;padding:16px 18px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.08);">
                            <div>
                                <div style="font-weight:800;font-size:1rem;color:white;">Set Drop-off Stop</div>
                                <div style="color:rgba(255,255,255,0.45);font-size:0.82rem;">Tap your stop on the route</div>
                            </div>
                            <button onclick="closeDropoffModal()" style="border:none;background:rgba(255,255,255,0.08);color:white;border-radius:10px;padding:8px 14px;cursor:pointer;font-weight:700;">✕</button>
                        </div>
                        <div id="map" style="flex:1;width:100%;"></div>
                        <div id="dropoffInfo" style="display:none;background:#0d1f2e;padding:16px 18px;border-top:1px solid rgba(255,255,255,0.08);">
                            <div style="color:rgba(255,255,255,0.45);font-size:0.75rem;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Drop-off Location</div>
                            <div id="dropoffAddress" style="color:white;font-weight:800;font-size:0.95rem;margin-bottom:12px;"></div>
                            <button id="confirmBtn" onclick="confirmDropoff()" style="width:100%;padding:14px;border:none;border-radius:14px;background:linear-gradient(135deg,#1A9FDB,#0B72C6);color:white;font-weight:800;font-size:1rem;cursor:pointer;">
                                📍 Confirm → Notify Driver
                            </button>
                        </div>
                    </div>

                    <a class="btn" href="/payments/history">View all payments</a>
                    <a class="btn-secondary" href="/master/tx100-master">Back to seats</a>
                </div>
            </div>
        </div>
    </div>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var map = null;
var marker = null;
var latlng = null;

function openDropoffModal() {{
    document.getElementById("dropoffModal").style.display = "flex";
    document.getElementById("dropoffModal").style.flexDirection = "column";
    document.getElementById("dropoffInfo").style.display = "none";
    setTimeout(function() {{ initMap(); }}, 100);
}}

function closeDropoffModal() {{
    document.getElementById("dropoffModal").style.display = "none";
}}

function initMap() {{
    if (map) {{ map.invalidateSize(); return; }}

    var waypoints = {route_coords_json};
    var start = waypoints[0];
    var end = waypoints[waypoints.length - 1];
    var midLat = (start[0] + end[0]) / 2;
    var midLng = (start[1] + end[1]) / 2;

    map = L.map("map").setView([midLat, midLng], 12);
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
        attribution: "© OpenStreetMap"
    }}).addTo(map);

    // Start marker - CODETA Site C
    L.marker(start).addTo(map).bindPopup("CODETA Site C - Start");
    // End marker - destination
    L.marker(end).addTo(map).bindPopup("{taxi_route} Taxi Rank");

    // Draw real road route via OSRM
    var coords = waypoints.map(function(p) {{ return p[1] + "," + p[0]; }}).join(";");
    fetch("https://router.project-osrm.org/route/v1/driving/" + coords + "?overview=full&geometries=geojson")
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            if (data.routes && data.routes[0]) {{
                var line = L.geoJSON(data.routes[0].geometry, {{
                    style: {{ color: "#1A9FDB", weight: 5, opacity: 0.85 }}
                }}).addTo(map);
                map.fitBounds(line.getBounds(), {{padding: [30, 30]}});
            }}
        }})
        .catch(function() {{
            L.polyline(waypoints, {{color: "#1A9FDB", weight: 5, opacity: 0.8}}).addTo(map);
            map.fitBounds(L.polyline(waypoints).getBounds(), {{padding: [30, 30]}});
        }});

    map.on("click", function(e) {{
        latlng = e.latlng;
        if (marker) map.removeLayer(marker);
        marker = L.marker(e.latlng).addTo(map);
        document.getElementById("dropoffInfo").style.display = "block";
        document.getElementById("confirmBtn").style.display = "block";
        document.getElementById("dropoffAddress").textContent = "Fetching address...";
        fetch("https://nominatim.openstreetmap.org/reverse?lat=" + e.latlng.lat + "&lon=" + e.latlng.lng + "&format=json")
            .then(r => r.json())
            .then(d => {{
                document.getElementById("dropoffAddress").textContent =
                    d.display_name ? d.display_name.split(",").slice(0,3).join(", ") : e.latlng.lat.toFixed(4) + ", " + e.latlng.lng.toFixed(4);
            }})
            .catch(() => {{
                document.getElementById("dropoffAddress").textContent = e.latlng.lat.toFixed(4) + ", " + e.latlng.lng.toFixed(4);
            }});
    }});
}}

async function confirmDropoff() {{
    if (!latlng) return;
    var addr = document.getElementById("dropoffAddress").textContent;
    try {{
        await fetch("/seats/{seat_id}/dropoff", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{lat: latlng.lat, lng: latlng.lng, address: addr, seat_number: {seat_number}}})
        }});
    }} catch(e) {{}}
    closeDropoffModal();
    document.getElementById("dropoffSentInline").style.display = "block";
    document.getElementById("dropoffAddrInline").textContent = addr;
}}
</script>
</body>
</html>
"""


@router.post("/payments/snapscan/webhook")
async def snapscan_webhook(request: Request, db: Session = Depends(get_db)):
    """
    SnapScan sends a POST to this URL when a payment is made.
    The order number (reference) should be the qr_token e.g. tx100-seat-5
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    status = data.get("status", "")
    reference = data.get("merchantReference", "") or data.get("orderNum", "")
    amount = float(data.get("totalAmount", 0)) / 100  # SnapScan sends cents

    if status != "completed" or not reference:
        return {"status": "ignored"}

    # Find seat by qr_token (reference = tx100-seat-5)
    seat = db.query(Seat).filter(Seat.qr_token == reference).first()
    if not seat:
        return {"status": "seat not found", "reference": reference}

    if seat.status in ["PAID", "CASH"]:
        return {"status": "already paid"}

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )

    if not trip:
        return {"status": "no active trip"}

    seat.status = "PAID"
    db.commit()

    # Log to Grafana
    try:
        from app.metrics import log_payment
        log_payment(route=str(trip.fare_amount), amount=float(trip.fare_amount), method="snapscan")
    except Exception:
        pass

    payment = Payment(
        id=str(__import__("uuid").uuid4()),
        trip_id=trip.id,
        seat_id=seat.id,
        amount=amount or trip.fare_amount,
        status="SUCCESS_SNAPSCAN",
    )
    db.add(payment)
    db.commit()

    from app.ws import manager
    await manager.broadcast(
        trip.id,
        {
            "type": "seat_update",
            "seat_id": seat.id,
            "seat_number": seat.seat_number,
            "status": "PAID",
        }
    )

    return {"status": "ok", "seat": seat.seat_number}


@router.get("/payments/demo/confirm", response_class=HTMLResponse)
def demo_payment_confirm(trip_id: str, seat_id: str, method: str = "apple", db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not seat or not trip:
        raise HTTPException(status_code=404, detail="Not found")

    seat.status = "PAID"
    db.commit()

    status_map = {
        "apple": "SUCCESS_APPLE_PAY",
        "google": "SUCCESS_GOOGLE_PAY",
    }

    payment = Payment(
        id=str(__import__("uuid").uuid4()),
        trip_id=trip_id,
        seat_id=seat_id,
        amount=trip.fare_amount,
        status=status_map.get(method, "SUCCESS_DEMO"),
    )
    db.add(payment)
    db.commit()

    import asyncio
    from app.ws import manager
    asyncio.create_task(manager.broadcast(trip_id, {{
        "type": "seat_update",
        "seat_id": seat.id,
        "seat_number": seat.seat_number,
        "status": "PAID"
    }}))

    return "{{}}"
