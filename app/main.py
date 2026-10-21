"""FastAPI app: WhatsApp webhook + a local /simulate endpoint for testing without WhatsApp.

Run:  uvicorn app.main:app --reload --port 8000
"""
import json
import logging
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel

from . import config
from .bot import handle_message
from .db import init_db
from .repository import mask_phone
from .whatsapp import send_text, verify_signature

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")

app = FastAPI(title="NBFC WhatsApp Loan Bot (demo)")


@app.on_event("startup")
def startup() -> None:
    if not os.path.exists(config.DB_PATH):
        from .seed import seed
        seed()
    else:
        init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dry_run": config.DRY_RUN}


@app.get("/webhook")
def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    """Meta calls this once when you register the webhook URL. We must echo back the challenge."""
    if mode == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="verification failed")


def _process_and_reply(phone: str, text: str) -> None:
    try:
        reply = handle_message(phone, text)
    except Exception:  # never crash the webhook; give a safe reply
        log.exception("handler error")
        reply = "क्षमा करें, कुछ तकनीकी समस्या आ गई है। कृपया थोड़ी देर बाद प्रयास करें।"
    send_text(phone, reply)


@app.post("/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks) -> dict:
    """Meta sends every incoming WhatsApp message here. We must answer 200 fast, so work runs in the background."""
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="bad signature")

    data = json.loads(raw or b"{}")
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                phone = msg.get("from", "")
                if msg.get("type") == "text":
                    text = msg["text"]["body"]
                else:
                    text = "[non-text message]"
                log.info("incoming from %s: %s chars", mask_phone(phone), len(text))  # log metadata only, not content
                background.add_task(_process_and_reply, phone, text)
    return {"status": "received"}


class SimulateIn(BaseModel):
    phone: str
    text: str


@app.post("/simulate")
def simulate(body: SimulateIn) -> dict:
    """Local testing: pretend `phone` sent `text`, get the bot's reply back. Disable in production."""
    return {"reply": handle_message(body.phone, body.text)}
