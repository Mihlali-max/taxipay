import os
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer

SECRET_KEY = os.getenv("SECRET_KEY", "fareflow-secret-change-in-production")

serializer = URLSafeTimedSerializer(SECRET_KEY)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
ADMIN_PASSWORD_PLAIN = os.getenv("ADMIN_PASSWORD", "admin123")

DRIVER_PIN = os.getenv("DRIVER_PIN", "1234")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin(username: str, password: str) -> bool:
    if username != ADMIN_USERNAME:
        return False
    if ADMIN_PASSWORD_HASH:
        return hmac.compare_digest(hash_password(password), ADMIN_PASSWORD_HASH)
    return hmac.compare_digest(password, ADMIN_PASSWORD_PLAIN)


def verify_driver_pin(pin: str) -> bool:
    return hmac.compare_digest(pin.strip(), DRIVER_PIN)


def create_session_token(role: str) -> str:
    return serializer.dumps({"role": role, "ts": datetime.utcnow().isoformat()})


def verify_session_token(token: str, role: str, max_age: int = 86400) -> bool:
    try:
        data = serializer.loads(token, max_age=max_age)
        return data.get("role") == role
    except Exception:
        return False
