
import os
from typing import Dict
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
from twilio.rest import Client
import openai
import re

app = FastAPI()

# Variables d'environnement
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM")  # Format : whatsapp:+14155238886
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
openai.api_key = OPENAI_API_KEY

# Mémoire temporaire des sessions utilisateur
session_memory: Dict[str, Dict[str, str]] = {}

@app.get("/")
def read_root():
    return {"message": "Askley backend with GPT-4.0 Nano is live ✅"}

@app.post("/whatsapp-webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...)
):
    print(f"📥 Message reçu de {From} : {Body}")

    body_lower = Body.lower()
    message_texte = ""

    if From not in session_memory:
        session_memory[From] = {}

    if "hôtel" in body_lower:
        session_memory[From]["last_intent"] = "hotel"
        message_texte = "🏨 Très bien ! Pour quelle ville souhaitez-vous réserver un hôtel ?"
    elif "restaurant" in body_lower:
        session_memory[From]["last_intent"] = "restaurant"
        message_texte = "🍽️ Dans quelle ville souhaitez-vous réserver un restaurant ?"
    elif "plat" in body_lower or "commander" in body_lower:
        session_memory[From]["last_intent"] = "plat"
        message_texte = "🥘 Quels plats souhaitez-vous commander ?"
    elif "artisan" in body_lower:
        session_memory[From]["last_intent"] = "artisan"
        message_texte = "🧵 Quels produits artisanaux cherchez-vous ?"
    elif "maison" in body_lower:
        session_memory[From]["last_intent"] = "maison"
        message_texte = "🏡 Quels plats faits maison souhaitez-vous ?"
    elif "duty free" in body_lower or "offre" in body_lower:
        session_memory[From]["last_intent"] = "duty"
        message_texte = "🛍️ Quelle est votre destination pour les offres hors taxes ?"
    elif body_lower in ["1", "2", "3", "4", "5", "6"]:
        message_texte = "✳️ Merci pour votre choix. Veuillez préciser les détails."

    elif session_memory[From].get("last_intent") == "hotel":
        if "ville" not in session_memory[From]:
            session_memory[From]["ville"] = Body
            message_texte = f"📍 Merci ! Pour {Body}, quelles sont vos dates de séjour ?"
        elif "dates" not in session_memory[From]:
            if re.search(r"\d{1,2}.*\d{1,2}", Body):
                session_memory[From]["dates"] = Body
                ville = session_memory[From]["ville"]
                dates = session_memory[From]["dates"]
                message_texte = f"✅ Merci ! Nous recherchons un hôtel à {ville} pour les dates : {dates}."
            else:
                message_texte = "📅 Veuillez préciser les dates de séjour (ex. : du 10 au 12 juin)."
        else:
            message_texte = "✳️ Nous avons toutes les infos. Souhaitez-vous faire une nouvelle réservation ?"

    else:
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4-0125-preview",  # Remplacez par "gpt-4.0-nano" quand disponible
                messages=[
                    {"role": "system", "content": "Tu es un assistant conciergerie intelligent pour voyageurs."},
                    {"role": "user", "content": Body}
                ]
            )
            message_texte = completion.choices[0].message.content
        except Exception as e:
            message_texte = "🤖 Erreur GPT. Veuillez reformuler votre question."

    try:
        if not From.startswith("whatsapp:"):
            From = "whatsapp:" + From
        client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            body=message_texte,
            to=From
        )
        print(f"📤 Réponse : {message_texte}")
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)

    return {"status": "ok"}
