
"""WhatsApp Cloud API helpers for sending messages and verifying webhooks."""

import hashlib
import hmac
import logging

import httpx

from . import config

log = logging.getLogger("whatsapp")

GRAPH_URL = "https://graph.facebook.com/v21.0"


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Validate Meta's HMAC-SHA256 signature.

    Local development may skip validation when no app secret is configured.
    Production must set WHATSAPP_APP_SECRET and enable production mode.
    """
    app_secret = config.WHATSAPP_APP_SECRET

    if not app_secret:
        if getattr(config, "PRODUCTION", False):
            log.error("Webhook rejected: WHATSAPP_APP_SECRET is missing")
            return False

        log.warning("Webhook signature validation skipped in local development")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=").strip()

    return hmac.compare_digest(expected, received)


def send_text(to: str, body: str) -> bool:
    """Send a WhatsApp text reply, or print it in dry-run mode.

    Returns True when a message was sent successfully or printed in dry-run.
    Returns False when sending fails.
    """
    if config.DRY_RUN:
        print(f"\n[DRY-RUN -> {to}]\n{body}\n")
        return True

    if not config.WHATSAPP_TOKEN or not config.WHATSAPP_PHONE_NUMBER_ID:
        log.error("Cannot send WhatsApp message: configuration is incomplete")
        return False

    url = f"{GRAPH_URL}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }

    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=15,
        )

        if response.is_success:
            log.info("WhatsApp reply accepted by API for recipient %s", _mask_phone(to))
            return True

        # Avoid logging full response bodies that may contain sensitive data.
        log.error(
            "WhatsApp send failed: HTTP %s",
            response.status_code,
        )
        return False

    except httpx.HTTPError as exc:
        log.error("WhatsApp HTTP request failed: %s", type(exc).__name__)
        return False


def _mask_phone(phone: str) -> str:
    """Return a masked phone number for logs."""
    if len(phone) <= 4:
        return "****"
    return "*" * (len(phone) - 4) + phone[-4:]
