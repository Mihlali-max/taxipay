import os
import hashlib
import hmac
from datetime import datetime, timedelta
from jose import jwt, JWTError

SECRET_KEY = os.getenv("SECRET_KEY", "fareflow-secret-change-in-production")
ALGORITHM = "HS256"

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
    payload = {
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24 if role == "admin" else 12),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_session_token(token: str, role: str, max_age: int = 86400) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("role") == role
    except JWTError:
        return False
