from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from app.db import get_db
from app.models import Taxi, Seat, Trip

router = APIRouter()


@router.get("/rider/{qr_token}", response_class=HTMLResponse)
def rider_page(qr_token: str, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.qr_token == qr_token).first()
    if not seat:
        raise HTTPException(status_code=404, detail="QR token not found")

    taxi = db.query(Taxi).filter(Taxi.id == seat.taxi_id).first()
    active_trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == taxi.id, Trip.status == "ACTIVE")
        .first()
    )

    trip_id = active_trip.id if active_trip else ""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Taxi Pay</title>
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
        button {{
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            background: black;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }}
        .ok {{
            margin-top: 15px;
            color: green;
            font-weight: bold;
        }}
        .err {{
            margin-top: 15px;
            color: red;
            font-weight: bold;
        }}
        .muted {{
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Taxi Pay</h2>
        <p><strong>Vehicle:</strong> {taxi.vehicle_code}</p>
        <p><strong>Route:</strong> {taxi.route_name}</p>
        <p><strong>Seat:</strong> {seat.seat_number}</p>
        <p><strong>Fare:</strong> R20.00</p>
        <p class="muted">Status: <span id="seatStatus">{seat.status}</span></p>
        <button onclick="payNow()">Pay Now</button>
        <div id="result"></div>
    </div>

    <script>
        async function payNow() {{
            const result = document.getElementById("result");
            const seatStatus = document.getElementById("seatStatus");

            if (!"{trip_id}") {{
                result.innerHTML = '<div class="err">No active trip found for this taxi.</div>';
                return;
            }}

            result.innerHTML = "Processing payment...";

            const response = await fetch("/payments/mock", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                body: JSON.stringify({{
                    trip_id: "{trip_id}",
                    seat_id: "{seat.id}",
                    amount: 20.0
                }})
            }});

            const data = await response.json();

            if (response.ok) {{
                seatStatus.textContent = "PAID";
                result.innerHTML = `
                    <div class="ok">Payment successful.</di>
                    <div style="margin-top:10px;">
                        <a href="/receipt/${{data.payment_id}}" target="_blank">View Receipt</a>
                    </div>
                `;
            }} else {{
                result.innerHTML = '<div class="err">Payment failed: ' + (data.detail || 'Unknown error') + '</div>';
            }}
        }}
    </script>
</body>
</html>
"""
@router.get("/driver")
def driver_auto(db: Session = Depends(get_db)):
    active_trip = (
        db.query(Trip)
        .filter(Trip.status == "ACTIVE")
        .first()
    )

    if not active_trip:
        raise HTTPException(status_code=404, detail="No active trip")

    return RedirectResponse(url=f"/driver/{active_trip.id}")


@router.get("/driver/{trip_id}", response_class=HTMLResponse)
def driver_page(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Driver Seat Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 30px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 20px;
        }}
        .seat {{
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #ccc;
            background: white;
        }}
        .PAID {{
            background: #c8f7c5;
        }}
        .UNPAID {{
            background: #ffd6d6;
        }}
        .CASH {{
            background: #ffe7a8;
        }}
        button {{
            margin-top: 10px;
            padding: 8px 12px;
            border: none;
            border-radius: 8px;
            background: black;
            color: white;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <h2>Driver Seat Map</h2>
    <p>Trip ID: {trip_id}</p>
    <div id="seatGrid" class="grid"></div>

    <script>
        let socket = null;

        async function loadSeatMap() {{
            const res = await fetch("/trips/{trip_id}/seat-map");
            const data = await res.json();
            const grid = document.getElementById("seatGrid");
            grid.innerHTML = "";

            data.seats.forEach(seat => {{
                const div = document.createElement("div");
                div.className = "seat " + seat.status;

                if (seat.status === "UNPAID") {{
                    div.innerHTML = `
                        Seat ${{seat.seat_number}}<br>
                        ${{seat.status}}<br><br>
                        <button onclick="markCash('${{seat.id}}')">Mark Cash</button>
                    `;
                }} else {{
                    div.innerHTML = "Seat " + seat.seat_number + "<br>" + seat.status;
                }}

                grid.appendChild(div);
            }});
        }}

        async function markCash(seatId) {{
            const res = await fetch(`/seats/${{seatId}}/cash`, {{
                method: "POST"
            }});

            const data = await res.json();

            if (!res.ok) {{
                alert(data.detail || "Failed to mark cash");
                return;
            }}
        }}

        function connectWebSocket() {{
            const protocol = window.location.protocol === "https:" ? "wss" : "ws";
            socket = new WebSocket(`${{protocol}}://${{window.location.host}}/ws/{trip_id}`);

            socket.onopen = () => {{
                console.log("WebSocket connected");
            }};

            socket.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                if (data.type === "seat_update") {{
                    loadSeatMap();
                }}
            }};

            socket.onclose = () => {{
                console.log("WebSocket disconnected, retrying...");
                setTimeout(connectWebSocket, 2000);
            }};
        }}

        loadSeatMap();
        connectWebSocket();
    </script>
</body>
</html>
"""
