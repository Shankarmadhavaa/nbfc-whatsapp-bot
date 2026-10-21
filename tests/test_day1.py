"""Day 1 tests. Run:  pytest -q   (uses a temporary database, your real demo DB is untouched)"""
import hashlib
import hmac
import json
import os

import pytest
from fastapi.testclient import TestClient

os.environ["DB_PATH"] = "test_nbfc.db"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-token"
os.environ["WHATSAPP_APP_SECRET"] = "test-secret"
os.environ["DEMO_CUSTOMER_PHONE"] = "919000000001"
os.environ["DEMO_COLLECTION_PHONE"] = "919000000002"
os.environ["DEMO_MANAGER_PHONE"] = "919000000003"

from app.main import app  # noqa: E402
from app.repository import repo  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _db():
    seed()
    yield
    if os.path.exists("test_nbfc.db"):
        os.remove("test_nbfc.db")


client = TestClient(app)


def test_roles_detected():
    assert repo.identify("919000000001")["role"] == "customer"
    assert repo.identify("919000000002")["role"] == "collection"
    assert repo.identify("919000000003")["role"] == "manager"
    assert repo.identify("910000000000")["role"] == "unknown"


def test_dummy_data_scenarios():
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert any(r["loan_no"] == "LN1001" for r in repo.emis_due_on(tomorrow))
    overdue = {r["loan_no"]: r for r in repo.overdue_list()}
    assert overdue["LN1003"]["overdue_emis"] == 1   # missed yesterday
    assert overdue["LN1004"]["overdue_emis"] == 2   # two overdue
    assert repo.todays_collection()["count"] == 3   # three customers paid today
    assert all(r["branch_id"] == "A" for r in repo.overdue_list("A"))


def test_webhook_verification():
    ok = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "test-token", "hub.challenge": "1234"})
    assert ok.status_code == 200 and ok.text == "1234"
    bad = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1234"})
    assert bad.status_code == 403


def _payload(phone, text):
    return {"entry": [{"changes": [{"value": {"messages": [{"from": phone, "type": "text", "text": {"body": text}}]}}]}]}


def test_webhook_rejects_bad_signature():
    body = json.dumps(_payload("919000000001", "hi")).encode()
    r = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=deadbeef"})
    assert r.status_code == 403


def test_webhook_accepts_good_signature():
    body = json.dumps(_payload("919000000001", "hi")).encode()
    sig = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    r = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": sig})
    assert r.status_code == 200


def test_customer_otp_and_hindi_flow():
    # 1. Unverified customer asks a question -> should demand OTP verification
    r = client.post("/simulate", json={"phone": "919000000001", "text": "mera emi kitna hai"})
    assert "OTP" in r.json()["reply"]

    # 2. Customer submits correct OTP (1234) -> should succeed verification
    r2 = client.post("/simulate", json={"phone": "919000000001", "text": "1234"})
    assert "सत्यापित" in r2.json()["reply"]

    # 3. Unknown number -> should reject cleanly in Hindi
    unknown = client.post("/simulate", json={"phone": "910000000000", "text": "hello"}).json()["reply"]
    assert "रिकॉर्ड में नहीं" in unknown