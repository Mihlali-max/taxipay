from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth import verify_admin, verify_driver_pin, create_session_token

router = APIRouter()

LOGIN_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    background: #060f1a;
    min-height: 100vh;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
}
.card {
    width: 100%;
    max-width: 380px;
    padding: 36px 28px;
    background: #0d1f2e;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 28px;
    box-shadow: 0 24px 48px rgba(0,0,0,0.4);
    margin: 20px;
}
.logo {
    width: 52px;
    height: 52px;
    border-radius: 16px;
    background: linear-gradient(135deg, #1A9FDB, #0B72C6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    margin: 0 auto 20px;
    box-shadow: 0 8px 20px rgba(26,159,219,0.35);
}
h1 {
    font-size: 1.4rem;
    font-weight: 800;
    text-align: center;
    margin-bottom: 6px;
    letter-spacing: -0.02em;
}
.subtitle {
    color: rgba(255,255,255,0.45);
    text-align: center;
    font-size: 0.88rem;
    margin-bottom: 28px;
}
.field {
    margin-bottom: 14px;
}
label {
    display: block;
    color: rgba(255,255,255,0.45);
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}
input {
    width: 100%;
    padding: 14px 16px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    color: white;
    font-size: 1rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
}
input:focus {
    border-color: #1A9FDB;
    background: rgba(26,159,219,0.08);
}
input::placeholder { color: rgba(255,255,255,0.25); }
.btn {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #1A9FDB, #0B72C6);
    color: white;
    border: none;
    border-radius: 14px;
    font-size: 1rem;
    font-weight: 800;
    cursor: pointer;
    margin-top: 8px;
    box-shadow: 0 10px 24px rgba(26,159,219,0.3);
    transition: transform 0.15s;
}
.btn:active { transform: scale(0.98); }
.error {
    background: rgba(231,76,60,0.12);
    border: 1px solid rgba(231,76,60,0.25);
    color: #f16b63;
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 0.88rem;
    font-weight: 700;
    margin-bottom: 16px;
    text-align: center;
}
.back {
    display: block;
    text-align: center;
    margin-top: 16px;
    color: rgba(255,255,255,0.35);
    text-decoration: none;
    font-size: 0.85rem;
}
.back:hover { color: rgba(255,255,255,0.6); }
"""


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(error: str = ""):
    error_html = f'<div class="error">❌ {error}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html><head>
    <title>FareFlow Admin Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />
    <style>{LOGIN_CSS}</style>
</head><body>
<div class="card">
    <div class="logo">📊</div>
    <h1>Admin Login</h1>
    <p class="subtitle">FareFlow fleet management</p>
    {error_html}
    <form method="post" action="/admin/login">
        <div class="field">
            <label>Username</label>
            <input type="text" name="username" placeholder="Enter username" autocomplete="username" required />
        </div>
        <div class="field">
            <label>Password</label>
            <input type="password" name="password" placeholder="Enter password" autocomplete="current-password" required />
        </div>
        <button class="btn" type="submit">Sign In →</button>
    </form>
    <a class="back" href="/">← Back to home</a>
</div>
</body></html>"""


@router.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if not verify_admin(username, password):
        return RedirectResponse(url="/admin/login?error=Invalid+username+or+password", status_code=302)
    token = create_session_token("admin")
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie("admin_session", token, httponly=True, max_age=86400, samesite="lax")
    return response


@router.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


@router.get("/driver/login", response_class=HTMLResponse)
def driver_login_page(error: str = ""):
    error_html = f'<div class="error">❌ {error}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html><head>
    <title>FareFlow Driver Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>{LOGIN_CSS}</style>
</head><body>
<div class="card">
    <div class="logo">🚗</div>
    <h1>Driver Access</h1>
    <p class="subtitle">Enter your 4-digit PIN</p>
    {error_html}
    <form method="post" action="/driver/login">
        <div class="field">
            <label>PIN</label>
            <input type="password" name="pin" placeholder="• • • •" maxlength="4" inputmode="numeric" pattern="[0-9]*" autocomplete="off" required />
        </div>
        <button class="btn" type="submit">Enter Dashboard →</button>
    </form>
    <a class="back" href="/">← Back to home</a>
</div>
</body></html>"""


@router.post("/driver/login")
def driver_login(pin: str = Form(...)):
    if not verify_driver_pin(pin):
        return RedirectResponse(url="/driver/login?error=Invalid+PIN", status_code=302)
    token = create_session_token("driver")
    response = RedirectResponse(url="/driver", status_code=302)
    response.set_cookie("driver_session", token, httponly=True, max_age=43200, samesite="lax")
    return response


@router.get("/driver/logout")
def driver_logout():
    response = RedirectResponse(url="/driver/login", status_code=302)
    response.delete_cookie("driver_session")
    return response
