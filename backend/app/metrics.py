import os
import time
import threading
import httpx

GRAFANA_URL = "https://prometheus-prod-us-east-3.grafana.net/api/prom/push"
GRAFANA_USER = "1593549"
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")

_metrics = {
    "payments_total": 0,
    "active_trips": 0,
    "waf_blocks": 0,
    "chat_requests": 0,
}

def increment(metric: str, value: int = 1):
    if metric in _metrics:
        _metrics[metric] += value

def set_metric(metric: str, value: int):
    _metrics[metric] = value

def push_metrics():
    while True:
        try:
            if GRAFANA_API_KEY:
                now_ms = int(time.time() * 1000)
                lines = []
                for name, value in _metrics.items():
                    lines.append(f'fareflow_{name}{{app="fareflow"}} {value} {now_ms}')
                
                payload = "\n".join(lines)
                
                httpx.post(
                    GRAFANA_URL,
                    content=payload,
                    headers={"Content-Type": "text/plain"},
                    auth=(GRAFANA_USER, GRAFANA_API_KEY),
                    timeout=10.0
                )
        except Exception:
            pass
        time.sleep(30)

def start_metrics_pusher():
    t = threading.Thread(target=push_metrics, daemon=True)
    t.start()
