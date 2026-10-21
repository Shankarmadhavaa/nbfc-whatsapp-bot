"""WhatsApp Cloud API helpers: send a text message, verify Meta's webhook signature."""
import hashlib
import hmac
import logging

import httpx

from . import config

log = logging.getLogger("whatsapp")
GRAPH_URL = "https://graph.facebook.com/v21.0"


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Meta signs every webhook call with HMAC-SHA256 using the App Secret (header X-Hub-Signature-256).
    Rejecting bad signatures stops anyone on the internet from sending fake messages to our webhook.
    If no App Secret is configured (local testing only) the check is skipped."""
    if not config.WHATSAPP_APP_SECRET:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(config.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


def send_text(to: str, body: str) -> None:
    """Send a free-form text reply (allowed within 24h of the user's last message).
    In DRY_RUN mode (no token) the message is printed instead, so you can test without WhatsApp."""
    if config.DRY_RUN:
        print(f"\n[DRY-RUN -> {to}]\n{body}\n")
        return
    url = f"{GRAPH_URL}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}}
    headers = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code >= 400:
            log.error("WhatsApp send failed: %s %s", r.status_code, r.text)
    except httpx.HTTPError as exc:
        log.error("WhatsApp send error: %s", exc)
