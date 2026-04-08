from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Seat, Trip, Payment
from app.ws import manager

router = APIRouter()


@router.post("/seats/{seat_id}/cash")
async def mark_cash(seat_id: str, amount: float = Body(...), db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()

    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    if seat.status in ["PAID", "CASH"]:
        raise HTTPException(status_code=400, detail="Seat already settled")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )

    if not trip:
        raise HTTPException(status_code=400, detail="No active trip")

    fare = trip.fare_amount
    change = amount - fare

    seat.status = "CASH"
    db.commit()

    existing = (
        db.query(Payment)
        .filter(Payment.trip_id == trip.id, Payment.seat_id == seat.id)
        .first()
    )

    if not existing:
        cash_payment = Payment(
            id=f"cash-{seat.id}-{trip.id}",
            trip_id=trip.id,
            seat_id=seat.id,
            amount=fare,
            status="SUCCESS_CASH",
        )
        db.add(cash_payment)
        db.commit()

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
        "seat_id": seat.id,
        "seat_number": seat.seat_number,
        "fare": fare,
        "amount_received": amount,
        "change": change,
        "status": seat.status
    }

@router.post("/seats/{seat_id}/cash-intent")
async def cash_intent(seat_id: str, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    trip = (
        db.query(Trip)
        .filter(Trip.taxi_id == seat.taxi_id, Trip.status == "ACTIVE")
        .first()
    )

    if trip:
        await manager.broadcast(
            trip.id,
            {
                "type": "cash_intent",
                "seat_id": seat.id,
                "seat_number": seat.seat_number,
                "message": f"Seat {seat.seat_number} wants to pay cash"
            }
        )

    return {"status": "notified", "seat_number": seat.seat_number}

import os
import httpx
from fastapi.responses import StreamingResponse

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "qxTFXDYbGcR8GaHSjczg"  # James

@router.post("/speak")
async def speak(text: str):
    if not ELEVENLABS_API_KEY:
        return {"error": "No API key"}
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            },
            timeout=10.0
        )
    
    if res.status_code != 200:
        return {"error": "TTS failed"}
    
    return StreamingResponse(
        iter([res.content]),
        media_type="audio/mpeg"
    )

from groq import Groq as _Groq

@router.post("/chat")
async def chat(request: Request):
    body = await request.json()
    question = body.get("question", "")
    route = body.get("route", "")
    fare = body.get("fare", "")

    import asyncio
    client = _Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    
    message = await asyncio.get_event_loop().run_in_executor(None, lambda: client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": f"""You are a helpful assistant for FareFlow, a digital taxi payment app in Cape Town, South Africa.
The rider is currently on a {route} taxi. The fare is R{fare}.
Answer questions about payments, the app, and the taxi ride.
Keep answers short, friendly and in simple English. Max 2-3 sentences.
If asked in Xhosa or Afrikaans, reply in that language."""
            },
            {"role": "user", "content": question}
        ]
    )
    
    return {"answer": message.choices[0].message.content}
