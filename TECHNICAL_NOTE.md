\# NBFC WhatsApp Chatbot — Technical Note



\## 1. Overview

A Python-based prototype demonstrating WhatsApp-style customer support for an NBFC. It supports demo loan enquiries, OTP verification, staff collection queries, and human-support handover using a local SQLite database.



\## 2. Architecture

\*\*Message source → FastAPI webhook → Message and role handling → OTP verification (customers) → Rule-based intent handling → SQLite repository → Response\*\*



\- \*\*FastAPI:\*\* Exposes health, webhook, and local simulation endpoints.

\- \*\*Business logic:\*\* Handles customer enquiries, staff queries, verification, and handover requests.

\- \*\*SQLite:\*\* Stores demonstration customers, loan information, EMI records, OTP sessions, and handover records.

\- \*\*Twilio Sandbox / ngrok:\*\* Used for optional WhatsApp demonstration and temporary webhook access.



\## 3. API Endpoints



| Method | Endpoint | Purpose |

|---|---|---|

| GET | `/health` | Health check |

| GET | `/webhook` | Webhook verification |

| POST | `/webhook` | Receive incoming messages |

| POST | `/simulate` | Local chatbot testing |



Interactive API documentation is available at `/docs` while the local server is running.



\## 4. Features

\- Demo OTP verification with expiry and attempt limits.

\- Customer queries for next EMI, outstanding balance, loan closure, and payment guidance.

\- Staff reports for collection summaries, overdue EMIs, and upcoming dues.

\- Human-support handover request recording.

\- Local testing without consuming WhatsApp messages.



\## 5. Security and Privacy

\- Uses dummy demonstration records rather than live NBFC data.

\- Local `.env` and SQLite database files should remain outside version control.

\- OTP `1234` is a demo-only value, not production authentication.

\- Production deployment requires secure OTP delivery, webhook signature verification, rate limiting, authorization and branch-scope enforcement, audit logging, and secure secret management.

\- Financial and customer data must be protected according to applicable privacy and regulatory requirements.



\## 6. Cost and Current Limitations

Local simulation uses the local application and database and does not send WhatsApp messages. WhatsApp Sandbox usage, hosting, AI services, and external integrations may incur costs depending on provider and configuration.



The current implementation uses deterministic rule-based handling; live Gemini processing is not active. OTP delivery, payment processing, and live-agent notifications are not implemented. No live NBFC core system is connected.



\## 7. Testing and Future Work

The latest automated test run passed \*\*6 tests\*\*. Future work includes integration with an authorized loan-management system, secure OTP provider, payment gateway, agent notification workflow, and additional authorization and webhook-security tests.



\*\*Status:\*\* Demonstration prototype only. Not approved for production financial transactions or live customer data.
