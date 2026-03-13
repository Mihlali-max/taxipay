from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Seat, Taxi, Trip

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_db)):
    taxis = db.query(Taxi).all()
    trips = db.query(Trip).all()
    seats = db.query(Seat).all()
    payments = db.query(Payment).all()

    total_taxis = len(taxis)
    total_trips = len(trips)
    total_payments = len(payments)
    total_revenue = sum(p.amount for p in payments) if payments else 0.0

    paid_count = sum(1 for s in seats if s.status == "PAID")
    cash_count = sum(1 for s in seats if s.status == "CASH")
    unpaid_count = sum(1 for s in seats if s.status == "UNPAID")

    active_trip = next((t for t in trips if t.status == "ACTIVE"), None)

    recent_payments_html = ""
    if payments:
        for p in payments[-8:][::-1]:
            recent_payments_html += f"""
            <div class="payment-row">
                <div>
                    <div class="payment-title">Payment {p.id[:8]}</div>
                    <div class="payment-sub">Trip {p.trip_id[:8]} • Seat {p.seat_id[:8]}</div>
                </div>
                <div class="payment-amount">R{p.amount:.2f}</div>
            </div>
            """
    else:
        recent_payments_html = """
        <div class="empty-state">No payments recorded yet.</div>
        """

    taxi_cards_html = ""
    if taxis:
        for taxi in taxis:
            taxi_cards_html += f"""
            <div class="mini-card">
                <div class="mini-title">{taxi.vehicle_code}</div>
                <div class="mini-sub">{taxi.route_name}</div>
                <div class="mini-meta">{taxi.seat_count} passenger seats</div>
            </div>
            """
    else:
        taxi_cards_html = '<div class="empty-state">No taxis found.</div>'

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>TaxiPay Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0B3C5D" />
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #0B3C5D 0%, #1A9FDB 16%, #EAF5FC 16%, #F7FBFF 100%);
            min-height: 100vh;
            color: #16324a;
        }}

        .app {{
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }}

        .shell {{
            width: 100%;
            max-width: 1180px;
            min-height: 100vh;
            padding: 20px 14px 30px;
        }}

        .topbar {{
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }}

        .topbar h1 {{
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
        }}

        .topbar p {{
            margin: 8px 0 0;
            color: rgba(255,255,255,0.88);
        }}

        .back {{
            text-decoration: none;
            color: white;
            font-weight: 700;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.16);
            padding: 10px 14px;
            border-radius: 14px;
        }}

        .panel {{
            background: rgba(255,255,255,0.98);
            border-radius: 26px;
            padding: 20px;
            box-shadow: 0 14px 28px rgba(11,60,93,0.10);
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 18px;
        }}

        .stat {{
            background: linear-gradient(180deg, #ffffff 0%, #f6fbff 100%);
            border: 1px solid #E3EEF6;
            border-radius: 20px;
            padding: 18px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.05);
        }}

        .stat-label {{
            color: #647c8e;
            font-size: 0.92rem;
            margin-bottom: 8px;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 800;
            color: #0B3C5D;
        }}

        .grid {{
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 18px;
        }}

        .card {{
            background: #ffffff;
            border: 1px solid #E3EEF6;
            border-radius: 22px;
            padding: 18px;
            box-shadow: 0 8px 18px rgba(11,60,93,0.04);
        }}

        .card h2 {{
            margin: 0 0 14px;
            font-size: 1.15rem;
            color: #0B3C5D;
        }}

        .status-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}

        .status-box {{
            border-radius: 18px;
            padding: 16px;
            color: white;
            font-weight: 800;
        }}

        .status-box small {{
            display: block;
            font-size: 0.85rem;
            opacity: 0.95;
            margin-bottom: 8px;
            font-weight: 700;
        }}

        .status-box strong {{
            font-size: 1.7rem;
        }}

        .paid {{
            background: linear-gradient(180deg, #4ac96b 0%, #27AE60 100%);
        }}

        .cash {{
            background: linear-gradient(180deg, #f7d56b 0%, #F4C542 100%);
            color: #4a3b00;
        }}

        .open {{
            background: linear-gradient(180deg, #f16b63 0%, #E74C3C 100%);
        }}

        .payment-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #EDF3F8;
        }}

        .payment-row:last-child {{
            border-bottom: none;
        }}

        .payment-title {{
            font-weight: 800;
            color: #0B3C5D;
        }}

        .payment-sub {{
            color: #708798;
            font-size: 0.88rem;
            margin-top: 4px;
        }}

        .payment-amount {{
            font-weight: 800;
            color: #1A9FDB;
            white-space: nowrap;
        }}

        .mini-grid {{
            display: grid;
            gap: 12px;
        }}

        .mini-card {{
            border: 1px solid #E3EEF6;
            border-radius: 18px;
            padding: 14px;
            background: #F9FCFE;
        }}

        .mini-title {{
            font-weight: 800;
            color: #0B3C5D;
            margin-bottom: 4px;
        }}

        .mini-sub {{
            color: #667f90;
            margin-bottom: 6px;
        }}

        .mini-meta {{
            color: #1A9FDB;
            font-weight: 700;
            font-size: 0.92rem;
        }}

        .info-list {{
            display: grid;
            gap: 10px;
        }}

        .info-item {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 14px;
            border-radius: 16px;
            background: #F6FBFF;
            border: 1px solid #E3EEF6;
        }}

        .info-item span:first-child {{
            color: #6d8394;
        }}

        .info-item strong {{
            color: #0B3C5D;
        }}

        .empty-state {{
            color: #758b9b;
            padding: 14px 0;
        }}

        @media (max-width: 900px) {{
            .stats {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .grid {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 560px) {{
            .shell {{
                padding: 16px 10px 24px;
            }}

            .topbar h1 {{
                font-size: 1.6rem;
            }}

            .panel {{
                padding: 14px;
            }}

            .stats {{
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }}

            .stat-value {{
                font-size: 1.55rem;
            }}

            .status-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="shell">
            <div class="topbar">
                <div>
                    <h1>Admin Dashboard</h1>
                    <p>System overview for taxis, trips, seats, and payments</p>
                </div>
                <a href="/" class="back">← Back Home</a>
            </div>

            <div class="panel">
                <div class="stats">
                    <div class="stat">
                        <div class="stat-label">Total Taxis</div>
                        <div class="stat-value">{total_taxis}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Total Trips</div>
                        <div class="stat-value">{total_trips}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Total Payments</div>
                        <div class="stat-value">{total_payments}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Revenue</div>
                        <div class="stat-value">R{total_revenue:.2f}</div>
                    </div>
                </div>

                <div class="grid">
                    <div style="display:grid; gap:18px;">
                        <div class="card">
                            <h2>Seat Status Overview</h2>
                            <div class="status-grid">
                                <div class="status-box paid">
                                    <small>Paid</small>
                                    <strong>{paid_count}</strong>
                                </div>
                                <div class="status-box cash">
                                    <small>Cash</small>
                                    <strong>{cash_count}</strong>
                                </div>
                                <div class="status-box open">
                                    <small>Open</small>
                                    <strong>{unpaid_count}</strong>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <h2>Recent Payments</h2>
                            {recent_payments_html}
                        </div>
                    </div>

                    <div style="display:grid; gap:18px;">
                        <div class="card">
                            <h2>Taxi Fleet</h2>
                            <div class="mini-grid">
                                {taxi_cards_html}
                            </div>
                        </div>

                        <div class="card">
                            <h2>Current System Snapshot</h2>
                            <div class="info-list">
                                <div class="info-item">
                                    <span>Active Trip</span>
                                    <strong>{active_trip.id[:8] if active_trip else "None"}</strong>
                                </div>
                                <div class="info-item">
                                    <span>Trip Status</span>
                                    <strong>{active_trip.status if active_trip else "N/A"}</strong>
                                </div>
                                <div class="info-item">
                                    <span>Total Seats Tracked</span>
                                    <strong>{len(seats)}</strong>
                                </div>
                                <div class="info-item">
                                    <span>System Mode</span>
                                    <strong>Demo</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
