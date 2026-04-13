import os
import time
import threading
import httpx
import json

LOKI_URL = "https://logs-prod-042.grafana.net/loki/api/v1/push"
LOKI_USER = "1551338"
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")

def log_event(event: str, level: str = "info", **kwargs):
    """Send a log event to Grafana Loki"""
    try:
        if not GRAFANA_API_KEY:
            return
        now_ns = str(int(time.time() * 1e9))
        msg = json.dumps({"event": event, "level": level, **kwargs})
        payload = {
            "streams": [{
                "stream": {"app": "fareflow", "env": "production", "level": level},
                "values": [[now_ns, msg]]
            }]
        }
        httpx.post(
            LOKI_URL,
            json=payload,
            auth=(LOKI_USER, GRAFANA_API_KEY),
            timeout=5.0
        )
    except Exception:
        pass

def log_payment(route: str, amount: float, method: str):
    log_event("payment_completed", route=route, amount=amount, method=method)

def log_trip_started(taxi_code: str, route: str):
    log_event("trip_started", taxi=taxi_code, route=route)

def log_chat(question: str):
    log_event("chat_request", question=question[:50])

def log_waf_block(reason: str, ip: str):
    log_event("waf_block", level="warn", reason=reason, ip=ip)

_counters = {
    "payments": 0,
    "chat_requests": 0,
    "waf_blocks": 0,
    "active_websockets": 0,
}

def increment(metric: str):
    if metric in _counters:
        _counters[metric] += 1

def start_metrics_pusher():
    """Push metrics as logs every 30 seconds"""
    def push():
        while True:
            try:
                from app.db import SessionLocal
                from app.models import Trip, Seat, Payment
                db = SessionLocal()
                active_trips = db.query(Trip).filter(Trip.status=="ACTIVE").count()
                total_payments = db.query(Payment).count()
                paid_seats = db.query(Seat).filter(Seat.status=="PAID").count()
                db.close()
                log_event("metrics",
                    active_trips=active_trips,
                    total_payments=total_payments,
                    paid_seats=paid_seats,
                    chat_requests=_counters["chat_requests"],
                    waf_blocks=_counters["waf_blocks"],
                )
            except Exception:
                pass
            time.sleep(30)
    t = threading.Thread(target=push, daemon=True)
    t.start()
