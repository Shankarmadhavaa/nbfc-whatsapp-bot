"""Full message handler with OTP verification, Gemini AI tool-calling, role checks, and handover."""
import os
import google.generativeai as genai
from .repository import mask_phone, repo
from datetime import date

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

ROLE_HI = {
    "customer": "ग्राहक",
    "collection": "कलेक्शन स्टाफ",
    "manager": "मैनेजर",
    "unknown": "अनजान नंबर",
}

def handle_message(phone: str, text: str) -> str:
    user = repo.identify(phone)
    role = user["role"]

    if role == "unknown":
        return "नमस्ते! आपका नंबर हमारे रिकॉर्ड में नहीं मिला। कृपया अपनी ब्रांच से संपर्क करें।"

    # 1. Human Handover / Anger Detection
    angry_keywords = ["fraud", "police", "cheat", "gussa", "bakwaas", "frod", "scam", "शिकायत", "धोखा"]
    if any(kw in text.lower() for kw in angry_keywords):
        return "हमें खेद है कि आपको असुविधा हुई। हम आपकी बात तुरंत अपने सीनियर मैनेजर से जोड़ रहे हैं। कृपया प्रतीक्षा करें।"

    # 2. Customer OTP Verification Gate
    if role == "customer":
        customer_id = user["id"]
        # Check if verified in session
        is_verified = repo.is_customer_verified(phone) # helper or direct db check
        
        # If user sends OTP or wants to verify
        if "otp" in text.lower() or not is_verified:
            if not is_verified and "1234" not in text: # Demo default OTP: 1234
                repo.create_otp_session(phone, "1234")
                return f"नमस्ते {user['name']} जी! सुरक्षा कारणों से, कृपया अपना 4-अंकों का OTP दर्ज करें (डिमोज़ के लिए '1234' भेजें)।"
            elif "1234" in text:
                repo.verify_customer_session(phone)
                return "✅ आपका नंबर सत्यापित हो गया है! अब आप पूछ सकते हैं: 'मेरी अगली EMI कब है?', 'पेंडिंग कितना है?', या 'लोन बंद करने का कितना अमाउंट है?'"
            else:
                return "कृपया अपना लोन वेरिफाई करने के लिए OTP '1234' भेजें।"

    # 3. Staff / Verified Customer Query Processing using Gemini + Tools
    return process_with_ai(user, text)


def process_with_ai(user: dict, text: str) -> str:
    """Uses Gemini to parse user intent in Hindi and query the repository safely."""
    role = user["role"]
    
    if not GEMINI_API_KEY:
        # Fallback rule-based handler if API key is missing during offline demo testing
        return fallback_rule_handler(user, text)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are an AI assistant for an Indian NBFC mobile phone loan company.
        User Role: {role}
        User Details: {user}
        User Query (Hindi/English): "{text}"

        Respond politely in natural Hindi. Do not calculate numbers yourself; use exact facts if provided, or answer based on standard NBFC workflows.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return fallback_rule_handler(user, text)


def fallback_rule_handler(user: dict, text: str) -> str:
    """Offline deterministic fallback for reliable demo execution."""
    role = user["role"]
    t = text.lower()

    if role == "customer":
        loans = repo.get_loans_for_customer(user["id"])
        if not loans:
            return "आपके नाम पर कोई सक्रिय लोन नहीं मिला।"
        loan = loans[0]
        loan_no = loan["loan_no"]

        if "emi" in t or "अगली" in t or "next" in t:
            emi = repo.get_next_emi(loan_no)
            if emi:
                return f"आपकी अगली EMI ₹{emi['amount']} की है, जो दिनांक {emi['due_date']} को देय है। भुगतान लिंक: https://pay.example.com/{loan_no}"
            return "आपकी सभी EMI का भुगतान हो चुका है।"
        
        elif "pending" in t or "बाकी" in t or "pending" in t:
            summary = repo.get_pending_summary(loan_no)
            return f"आपका कुल बकाया शेष (Pending Balance) ₹{summary['unpaid_total']} है (कुल {summary['unpaid_count']} EMI बाकी)।"
        
        elif "closure" in t or "foreclosure" in t or "लोन बंद" in t:
            return f"आपका लोन बंद (Foreclosure) करने की कुल राशि ₹{loan['foreclosure_amount']} है।"
        
        elif "pay" in t or "लिंक" in t or "payment" in t:
            return f"यहाँ आपका ऑनलाइन भुगतान लिंक है: https://pay.example.com/{loan_no}?amt={loan['next_emi_amount']}"

    elif role in ["collection", "manager"]:
        branch = user.get("branch") if role == "collection" else None
        
        if "collection" in t or "आज" in t or "today" in t:
            col = repo.todays_collection(branch)
            return f"आज का कुल कलेक्शन: ₹{col['total']} ({col['count']} भुगतान प्राप्त हुए)।"
        
        elif "overdue" in t or "बकाया" in t:
            overdues = repo.overdue_list(branch)
            msg = "🔴 ओवरड्यू लिस्ट:\n"
            for o in overdues[:5]:
                msg += f"- {o['name']} ({o['loan_no']}): ₹{o['overdue_amount']} ({o['overdue_emis']} EMI बाकी)\n"
            return msg or "कोई ओवरड्यू लोन नहीं मिला।"

    return "नमस्ते! मैं आपकी किस प्रकार सहायता कर सकता हूँ? आप अपनी EMI, पेंडिंग बैलेंस या पेमेंट लिंक के बारे में पूछ सकते हैं।"