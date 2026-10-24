
"""NBFC chatbot: OTP verification, role-based queries and handover."""

import re
import sqlite3
from datetime import date, datetime, timedelta

from .db import get_conn
from .repository import repo


DEMO_OTP = "1234"


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _requests_human(text: str) -> bool:
    t = _normalise(text)

    phrases = (
        "angry", "very angry", "furious", "speak to a human",
        "talk to a human", "human manager", "real person",
        "speak to manager", "talk to manager", "speak to an agent",
        "customer care", "human support", "supervisor",
        "file a complaint", "raise a complaint", "make a complaint",
        "complaint", "fraud", "scam", "cheat", "police",
        "gussa", "bakwaas", "shikayat", "dhokha",
        "शिकायत", "धोखा", "गुस्सा", "मैनेजर से बात",
        "इंसान से बात", "मानव सहायता", "कस्टमर केयर",
    )
    return any(phrase in t for phrase in phrases)


def _requests_otp_resend(text: str) -> bool:
    """Recognise explicit requests to start a fresh OTP challenge."""
    t = _normalise(text)

    phrases = (
        "resend otp",
        "send otp again",
        "new otp",
        "otp resend",
        "request otp",
        "otp expired",
        "नया ओटीपी",
        "ओटीपी दोबारा",
        "ओटीपी फिर से",
    )
    return any(phrase in t for phrase in phrases)


def _create_handover(phone: str, role: str, message: str) -> bool:
    """Create or refresh a human-handover record."""
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO handover (phone, reason, started_at, active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(phone) DO UPDATE SET
                    reason = excluded.reason,
                    started_at = excluded.started_at,
                    active = 1
                """,
                (
                    phone,
                    f"Role: {role}. Request: {message[:1000]}",
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        return True
    except sqlite3.Error:
        print("Handover database operation failed.")
        return False


def _customer_otp_gate(phone: str, text: str) -> str | None:
    """Return a response if OTP processing is needed; otherwise None."""
    try:
        if repo.is_customer_verified(phone):
            return None

        state = repo.otp_challenge_state(phone)

        if re.fullmatch(r"\d{4}", text):
            success = repo.verify_customer_session(phone, text)

            if success:
                return (
                    "आपका डेमो नंबर सत्यापित हो गया है। अब आप "
                    "अगली EMI, बकाया राशि, लोन क्लोजर या "
                    "भुगतान जानकारी पूछ सकते हैं।"
                )

            new_state = repo.otp_challenge_state(phone)

            if new_state == "locked":
                return (
                    "OTP सत्यापन की अधिकतम कोशिशें पूरी हो गई हैं। "
                    "नया डेमो OTP शुरू करने के लिए RESEND OTP भेजें।"
                )

            if new_state == "none":
                return (
                    "पहले OTP अनुरोध शुरू करें। OTP प्राप्त करने के "
                    "लिए कोई सामान्य संदेश भेजें।"
                )

            return (
                "OTP गलत है या समाप्त हो गया है। कृपया जाँचकर "
                "दोबारा भेजें। यदि OTP समाप्त हो गया है या कोशिशें "
                "पूरी हो गई हैं, तो RESEND OTP भेजें।"
            )

        if _requests_otp_resend(text):
            repo.create_otp_session(phone, DEMO_OTP)
            return (
                "नया स्थानीय डेमो OTP सत्र शुरू हो गया है। "
                "इस डेमो का OTP 1234 है। यह वास्तविक OTP संदेश नहीं है।"
            )

        if state == "active":
            return (
                "आपका OTP सत्र सक्रिय है। कृपया 4-अंकों का OTP भेजें। "
                "इस स्थानीय डेमो में OTP 1234 है।"
            )

        if state in ("expired", "locked"):
            return (
                "आपका OTP सत्र समाप्त हो गया है या कोशिशों की सीमा "
                "पूरी हो गई है। नया डेमो सत्र शुरू करने के लिए "
                "RESEND OTP भेजें।"
            )

        # No challenge exists. Start the first local demo challenge.
        repo.create_otp_session(phone, DEMO_OTP)
        return (
            "सुरक्षा के लिए OTP सत्यापन आवश्यक है। इस स्थानीय डेमो "
            "में OTP 1234 है। वास्तविक OTP संदेश नहीं भेजा गया है।"
        )

    except Exception:
        print("Customer OTP processing failed.")
        return (
            "अभी सुरक्षा सत्यापन नहीं हो पा रहा है। कृपया कुछ देर "
            "बाद दोबारा प्रयास करें या अपनी ब्रांच से संपर्क करें।"
        )


def handle_message(phone: str, text: str) -> str:
    """Main entry point used by the local simulator and WhatsApp webhook."""
    if not isinstance(text, str) or not text.strip():
        return "कृपया अपना सवाल लिखकर भेजें।"

    if not isinstance(phone, str) or not phone.strip():
        return "कृपया मान्य फोन नंबर से संपर्क करें।"

    phone = phone.strip()
    text = text.strip()

    try:
        user = repo.identify(phone)
    except Exception:
        print("User identification failed.")
        return (
            "अभी आपकी जानकारी प्राप्त नहीं हो पा रही है। "
            "कृपया कुछ देर बाद दोबारा प्रयास करें।"
        )

    if not user or user.get("role") == "unknown":
        return (
            "नमस्ते! आपका नंबर हमारे रिकॉर्ड में नहीं मिला। "
            "कृपया अपनी ब्रांच से संपर्क करें।"
        )

    role = user.get("role", "unknown")

    # Handover requests take priority over normal questions.
    if _requests_human(text):
        if _create_handover(phone, role, text):
            return (
                "हमें खेद है कि आपको परेशानी हुई। आपका मानव सहायता "
                "अनुरोध दर्ज कर दिया गया है। हमारी टीम उपलब्ध होने पर "
                "आपसे संपर्क कर सकती है। यह डेमो है; कोई वास्तविक "
                "सूचना या कॉल नहीं भेजी गई है।"
            )

        return (
            "हम आपका मानव सहायता अनुरोध दर्ज नहीं कर पाए। "
            "कृपया अपनी ब्रांच या आधिकारिक ग्राहक सहायता से संपर्क करें।"
        )

    if role == "customer":
        otp_response = _customer_otp_gate(phone, text)
        if otp_response is not None:
            return otp_response

    return process_with_ai(user, text)


def process_with_ai(user: dict, text: str) -> str:
    """Route to deterministic handlers; this function calls no AI model."""
    return fallback_rule_handler(user, text)


def _matches(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _handle_customer(user: dict, text: str) -> str:
    """Handle verified customer loan questions."""
    loans = repo.get_loans_for_customer(user["id"])

    if not loans:
        return (
            "आपके नाम पर कोई सक्रिय लोन नहीं मिला। "
            "कृपया अपनी ब्रांच से संपर्क करें।"
        )

    loan = loans[0]
    loan_no = loan["loan_no"]

    if _matches(
        text,
        (
            "foreclosure", "loan band", "loan close", "close my loan",
            "close the loan", "loan closure", "loan closing",
            "settle my loan", "full settlement", "loan khatam",
            "लोन बंद", "लोन क्लोज", "लोन समाप्त", "फोरक्लोजर",
        ),
    ):
        amount = loan.get("foreclosure_amount")

        if amount is not None:
            return (
                f"डेमो लोन क्लोजर राशि ₹{amount} है। "
                "भुगतान करने से पहले अपनी ब्रांच से अंतिम राशि की पुष्टि करें।"
            )

        return (
            "लोन क्लोजर की अंतिम राशि उपलब्ध डेटा में नहीं है। "
            "कृपया अपनी ब्रांच से आधिकारिक फोरक्लोजर कोटेशन लें।"
        )

    if _matches(
        text,
        (
            "pending", "balance", "baki", "baaki", "outstanding",
            "how much do i owe", "how much is due",
            "loan amount remaining", "remaining balance",
            "kitna baki", "बकाया", "बाकी राशि", "बैलेंस", "कितना बाकी",
        ),
    ):
        summary = repo.get_pending_summary(loan_no)
        return (
            f"आपकी डेमो बकाया राशि ₹{summary['unpaid_total']} है। "
            f"बकाया EMI की संख्या: {summary['unpaid_count']}।"
        )

    if _matches(
        text,
        (
            "payment", "pay", "make my emi payment", "how can i pay",
            "how do i pay", "payment method", "payment link",
            "pay online", "bhugtan", "paisa kaise", "payment kaise",
            "भुगतान", "पेमेंट", "पैसे कैसे",
        ),
    ):
        emi = repo.get_next_emi(loan_no)

        if not emi:
            return (
                "अभी कोई आगामी EMI नहीं मिली। भुगतान की जानकारी के "
                "लिए कृपया अपनी ब्रांच से संपर्क करें।"
            )

        return (
            f"आपकी अगली EMI ₹{emi['amount']} है और इसकी तारीख "
            f"{emi['due_date']} है। यह डेमो है; वास्तविक भुगतान लिंक "
            "कॉन्फ़िगर नहीं है। कृपया आधिकारिक भुगतान विवरण लें।"
        )

    if _matches(
        text,
        (
            "next emi", "upcoming emi", "emi due", "emi date",
            "when is my emi", "when is the next emi",
            "next installment", "agli emi", "emi kab", "emi kitni",
            "अगली किस्त", "अगली ईएमआई", "ईएमआई", "किस्त कब",
        ),
    ):
        emi = repo.get_next_emi(loan_no)

        if emi:
            return (
                f"आपकी अगली EMI ₹{emi['amount']} है, जिसकी देय "
                f"तारीख {emi['due_date']} है।"
            )

        return "आपकी कोई आगामी EMI नहीं मिली। कृपया अपनी ब्रांच से संपर्क करें।"

    return (
        "नमस्ते! मैं इन विषयों में सहायता कर सकता हूँ: अगली EMI, "
        "बकाया राशि, लोन क्लोजर और भुगतान जानकारी। कृपया इनमें से "
        "किसी विषय के बारे में पूछें।"
    )


def _handle_staff(user: dict, text: str) -> str:
    """Handle branch-scoped collection reports and manager reports."""
    role = user["role"]
    branch = user.get("branch_id") if role == "collection" else None

    if _matches(
        text,
        (
            "due tomorrow", "emis due tomorrow", "emi due tomorrow",
            "emi tomorrow", "tomorrow emi", "kal ki emi", "kal due",
            "कल की ईएमआई", "कल की किस्त",
        ),
    ):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        emis = repo.emis_due_on(tomorrow, branch)

        if not emis:
            return f"{tomorrow} के लिए कोई बकाया EMI देय नहीं है।"

        lines = [f"{tomorrow} को देय EMIs:"]
        for item in emis[:10]:
            lines.append(
                f"- {item['name']} ({item['loan_no']}), "
                f"EMI #{item['emi_no']}: ₹{item['amount']}"
            )

        if len(emis) > 10:
            lines.append(f"और {len(emis) - 10} रिकॉर्ड हैं।")

        return "\n".join(lines)

    if _matches(
        text,
        (
            "overdue", "overdue list", "overdue loans", "show overdue",
            "overdue accounts", "बकाया सूची", "ओवरड्यू",
        ),
    ):
        overdues = repo.overdue_list(branch)

        if not overdues:
            return "कोई ओवरड्यू लोन नहीं मिला।"

        lines = ["ओवरड्यू डेमो सूची:"]
        for item in overdues[:10]:
            lines.append(
                f"- {item['name']} ({item['loan_no']}): "
                f"₹{item['overdue_amount']}, "
                f"{item['overdue_emis']} EMI बकाया"
            )

        if len(overdues) > 10:
            lines.append(f"और {len(overdues) - 10} रिकॉर्ड हैं。")

        return "\n".join(lines)

    if _matches(
        text,
        (
            "collection", "today", "today collection",
            "today's collection", "daily collection",
            "collection report", "aaj", "aaj ka collection",
            "आज का कलेक्शन", "आज की वसूली", "कलेक्शन",
        ),
    ):
        collection = repo.todays_collection(branch)
        return (
            f"आज का डेमो कलेक्शन ₹{collection['total']} है। "
            f"कुल भुगतान: {collection['count']}।"
        )

    return (
        "नमस्ते! आप इन रिपोर्टों के बारे में पूछ सकते हैं: "
        "कल देय EMI, ओवरड्यू सूची या आज का कलेक्शन।"
    )


def fallback_rule_handler(user: dict, text: str) -> str:
    """Route messages according to the identified role."""
    role = user.get("role", "unknown")
    normalised_text = _normalise(text)

    try:
        if role == "customer":
            return _handle_customer(user, normalised_text)

        if role in ("collection", "manager"):
            return _handle_staff(user, normalised_text)

        return (
            "नमस्ते! आपका नंबर हमारे रिकॉर्ड में नहीं मिला। "
            "कृपया अपनी ब्रांच से संपर्क करें।"
        )

    except (sqlite3.Error, KeyError, TypeError, ValueError):
        print(f"Message handling failed for role {role}.")
        return (
            "आपकी जानकारी प्राप्त करते समय एक समस्या हुई। "
            "कृपया कुछ देर बाद दोबारा प्रयास करें या अपनी ब्रांच से संपर्क करें।"
        )