"""Central configuration. All secrets come from environment variables (.env), never from code."""
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").split("#")[0].strip()
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").split("#")[0].strip()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "nbfc-demo-verify").split("#")[0].strip()
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "").split("#")[0].strip()

DEMO_CUSTOMER_PHONE = os.getenv("DEMO_CUSTOMER_PHONE", "919000000001").split("#")[0].strip()
DEMO_COLLECTION_PHONE = os.getenv("DEMO_COLLECTION_PHONE", "919000000002").split("#")[0].strip()
DEMO_MANAGER_PHONE = os.getenv("DEMO_MANAGER_PHONE", "919000000003").split("#")[0].strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").split("#")[0].strip()
DB_PATH = os.getenv("DB_PATH", "nbfc_demo.db").split("#")[0].strip()

# If no WhatsApp token is set, messages are printed to the console instead of being sent (dry-run).
DRY_RUN = not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID)
