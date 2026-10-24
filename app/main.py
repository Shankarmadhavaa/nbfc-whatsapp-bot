
"""FastAPI app: Meta and Twilio WhatsApp webhooks plus local simulator."""

import json
import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel

from . import config
from .bot import handle_message
from .db import init_db
from .repository import mask_phone
from .whatsapp import send_text, verify_signature

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the demo database when the application starts."""
    if not os.path.exists(config.DB_PATH):
        from .seed import seed
        seed()
    else:
        init_db()
    yield


app = FastAPI(
    title="NBFC WhatsApp Loan Bot (demo)",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dry_run": config.DRY_RUN}


@app.get("/webhook")
def verify_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    """Verify the webhook subscription with Meta."""
    if mode == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="verification failed")


def _process_and_reply(phone: str, text: str) -> None:
    """Process a Meta message and send its reply through the Meta API."""
    try:
        reply = handle_message(phone, text)
        send_text(phone, reply)
    except Exception:
        log.exception("Message processing failed for %s", mask_phone(phone))
        if config.DRY_RUN:
            print("\n[DRY-RUN] Message processing failed. Check application logs.\n")


def _twiml_message(message: str) -> Response:
    """Return a Twilio-compatible XML message response."""
    safe_message = escape(str(message))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Message>"
        f"{safe_message}"
        "</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
):
    """Receive Twilio form posts or Meta JSON webhook events."""
    content_type = request.headers.get("content-type", "").lower()

    # Twilio sends WhatsApp messages as application/x-www-form-urlencoded.
    if "application/x-www-form-urlencoded" in content_type:
        raw = await request.body()
        form = parse_qs(raw.decode("utf-8", errors="replace"))

        sender = form.get("From", [""])[0]
        message_text = form.get("Body", [""])[0]

        if not sender.startswith("whatsapp:"):
            log.warning("Twilio webhook received a non-WhatsApp sender")
            return _twiml_message(
                "மன்னிக்கவும், இது WhatsApp செய்தியாக இல்லை. / Sorry, this is not a WhatsApp message."
            )

        # Convert "whatsapp:+919000000001" to "919000000001",
        # which is the phone format used by the demo database.
        phone = sender.removeprefix("whatsapp:").strip()
        phone = phone.replace("+", "").replace(" ", "")

        if not phone or not message_text.strip():
            return _twiml_message(
                "வணக்கம்! உங்கள் கேள்வியை அனுப்புங்கள். / Hello! Please send your question."
            )

        log.info(
            "Twilio WhatsApp message received from %s (%s chars)",
            mask_phone(phone),
            len(message_text),
        )

        try:
            # Twilio expects a reply in TwiML for this webhook response.
            reply = handle_message(phone, message_text.strip())
            return _twiml_message(reply)
        except Exception:
            log.exception(
                "Twilio message processing failed for %s",
                mask_phone(phone),
            )
            return _twiml_message(
                "மன்னிக்கவும், தற்போது உங்கள் செய்தியைச் செயல்படுத்த முடியவில்லை. "
                "தயவுசெய்து மீண்டும் முயற்சிக்கவும். / Sorry, I could not process "
                "your message right now. Please try again."
            )

    # Preserve the existing Meta Cloud API JSON webhook.
    raw = await request.body()

    if not verify_signature(
        raw,
        request.headers.get("X-Hub-Signature-256"),
    ):
        raise HTTPException(status_code=403, detail="bad signature")

    try:
        data = json.loads(raw or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="invalid JSON")

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            for msg in value.get("messages", []):
                phone = msg.get("from", "")
                if not phone:
                    continue

                if msg.get("type") == "text":
                    text = msg.get("text", {}).get("body", "")
                else:
                    text = "[non-text message]"

                if not text:
                    continue

                log.info(
                    "Meta message received from %s (%s chars)",
                    mask_phone(phone),
                    len(text),
                )
                background.add_task(_process_and_reply, phone, text)

    return {"status": "received"}


class SimulateIn(BaseModel):
    phone: str
    text: str


@app.post("/simulate")
def simulate(body: SimulateIn) -> dict:
    """Local-only test endpoint; disabled in production."""
    if getattr(config, "PRODUCTION", False):
        raise HTTPException(status_code=404, detail="Not found")

    return {"reply": handle_message(body.phone, body.text)}