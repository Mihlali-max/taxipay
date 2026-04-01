# 🚕 FareFlow — Digital Taxi Fare Payments for South Africa

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-OpenResty-009639?style=for-the-badge&logo=nginx&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

> **Scan. Pay. Hamba.** — Digital taxi fare payments built for Cape Town's minibus taxi industry.

Live demo: [fareflow.onrender.com](https://fareflow.onrender.com)

---

## 🎯 The Problem

Every day, millions of South Africans ride minibus taxis. Paying the fare means:
- Fumbling for exact change in a moving vehicle
- Drivers distracted making change at high speed
- No receipt, no record, no accountability
- "Eish, andinamali" moments 😭

**FareFlow fixes this.** Riders scan a QR code on their seat, pay digitally, and the driver sees it live.

---

## ✨ Features

### 🧑🏾 Rider Experience
- 📱 Scan QR code on seat → instant payment page
- 💳 Pay via Bank Card, Apple Pay, Google Pay, SnapScan or Cash
- 📍 Set drop-off stop on live map — driver notified instantly
- 🧾 Digital receipt after payment
- 🗺️ Personal trip dashboard with live route map

### 🚗 Driver Dashboard
- 🗺️ Live seat map — see paid, cash, and open seats in real time
- 💵 Cash to driver — rider notifies driver, seat pulses yellow
- 📍 Drop-off alerts — see exactly where each rider wants to stop
- 🔄 Change route with searchable modal
- ✏️ Edit fare manually
- 📊 Trip summary with revenue breakdown

### 👨🏾‍💼 Admin Dashboard
- 📊 Fleet overview — taxis, trips, revenue
- 💳 Payment history with status labels
- 🗺️ Seat status across all trips

---

## 🏗️ Architecture

\`\`\`
┌─────────────────────────────────────────────────────────┐
│                     Internet                             │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP/HTTPS
┌─────────────────▼───────────────────────────────────────┐
│              OpenResty (Nginx + Lua)                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Lua WAF — blocks SQLi, XSS, Path Traversal     │    │
│  │  Rate Limiting — 5 req/min login, 10 payments   │    │
│  │  Security Headers — HSTS, CSP, X-Frame, etc.    │    │
│  │  Bot Blocking — sqlmap, nikto, nmap, etc.       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────────┘
                  │ Reverse Proxy
┌─────────────────▼───────────────────────────────────────┐
│              FastAPI Application                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Riders  │ │  Driver  │ │ Payments │ │  Admin   │  │
│  │  Pages   │ │Dashboard │ │ PayFast  │ │Dashboard │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌─────────────────────────────────────────────────┐   │
│  │          WebSocket Manager (Live updates)        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              PostgreSQL 16 (Supabase)                    │
│  taxis │ seats │ trips │ payments                        │
└─────────────────────────────────────────────────────────┘
\`\`\`

---

## 🛡️ Security Stack

| Layer | Technology | Protection |
|-------|-----------|------------|
| WAF | OpenResty + Lua | SQLi, XSS, Path Traversal |
| Rate Limiting | Nginx | Brute force, DDoS |
| Bot Blocking | Nginx map | sqlmap, nikto, nmap |
| Security Headers | Nginx | Clickjacking, MIME, XSS |
| Auth | itsdangerous | Session tokens, PIN |
| Infrastructure | UFW + Fail2ban | Port scanning, repeated attacks |

---

## 🧰 Tech Stack

| Category | Technology |
|----------|-----------|
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 (Supabase) |
| Reverse Proxy | OpenResty (Nginx + Lua) |
| Containerization | Docker, Docker Compose |
| Infrastructure | Terraform (Hetzner Cloud) |
| Configuration | Ansible |
| CI/CD | GitHub Actions |
| Payments | PayFast, SnapScan |
| Maps | OpenStreetMap, Leaflet.js, OSRM |
| Deployment | Render (auto-deploy via GitHub) |

---

## 🚀 Quick Start

### Run with Docker

\`\`\`bash
git clone https://github.com/Mihlali-max/taxipay.git
cd taxipay/backend
cp .env.example .env
docker-compose up -d
\`\`\`

Open \`http://localhost\` in your browser.

### Run locally

\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

---

## 📁 Project Structure

\`\`\`
taxipay/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routers/
│   │   │   ├── pages.py         # All HTML pages
│   │   │   ├── payments.py      # PayFast & SnapScan
│   │   │   ├── seats.py         # Seat management
│   │   │   ├── admin.py         # Admin dashboard
│   │   │   └── auth.py          # Login & sessions
│   │   ├── route_coords.py      # Cape Town taxi routes
│   │   └── fares.py             # Route fare pricing
│   ├── nginx/
│   │   ├── default.conf         # Nginx + rate limiting
│   │   └── lua/
│   │       └── waf.lua          # Custom Lua WAF
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml
├── ansible/
│   └── deploy.yml               # Server provisioning
├── terraform/
│   └── main.tf                  # Hetzner Cloud infra
└── .github/
    └── workflows/
        └── deploy.yml           # CI/CD pipeline
\`\`\`

---

## 🌍 Cape Town Routes

All major CODETA routes from **Kuwait Taxi Rank, Site C, Khayelitsha**:

Claremont · Wynberg · Cape Town CBD · Mitchell's Plain · Bellville · Parow · Eersterivier · Delft · Mfuleni · Gugulethu · Langa · Nyanga · Stellenbosch · Paarl · Kuils River · Century City · N1 City · Sea Point · Fishhoek · Atlantis · Malmesbury · and more...

---

## 💳 Payment Methods

| Method | Status |
|--------|--------|
| Bank Card (PayFast) | ✅ Live |
| Cash to Driver | ✅ Live |
| SnapScan | 🔄 Pending verification |
| Apple Pay | 🔄 Coming soon |
| Google Pay | 🔄 Coming soon |

---

## 👨🏾‍💻 Author

**Mihlali Momoza** — Built with FastAPI, OpenStreetMap, and Cape Town taxi knowledge 🚕

> *"Scan. Plata. Hamba."* 🇿🇦
