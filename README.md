# NBFC WhatsApp Chatbot

A Python-based WhatsApp chatbot prototype for Non-Banking Financial Companies (NBFCs). It demonstrates customer loan queries, OTP verification, role-based collection reports, and human-support handover using a local demo database.

## Features

- **Customer verification:** Demo OTP workflow with expiry and attempt limits.
- **Loan information:** Retrieve the next EMI, outstanding balance, and demo loan-closure amount.
- **Payment guidance:** Respond to payment-related questions without initiating real payments.
- **Staff reports:** Demonstrate collection summaries, overdue EMI lists, and upcoming dues.
- **Human-support handover:** Record requests for human assistance in the demo database.
- **WhatsApp integration:** Webhook endpoints for Twilio Sandbox and Meta-style JSON messages.
- **Local testing:** Simulate chatbot conversations without consuming WhatsApp messages.

## Technology Stack

- Python, FastAPI, SQLite, Uvicorn, and Pytest
- Twilio WhatsApp Sandbox
- ngrok for temporary webhook exposure

## Project Setup

### 1. Activate your virtual environment

If your virtual environment is already active, skip this step.

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Configure environment variables

Review `.env.example` and configure the application as required. Never commit real API keys, access tokens, or credentials.

### 3. Start the application

From the project directory, run:

```powershell
$env:PYTHONPATH="."
python -m uvicorn app.main:app --reload
```

### 4. Open the API documentation

- Health endpoint: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

## Local Demo

The project includes seeded dummy customer and staff records. The local demo OTP is `1234`.

Use the local `/simulate` endpoint to test conversations without sending WhatsApp messages. Only use dummy data.

Example customer questions:
- What is my next EMI?
- What is my outstanding balance?
- How much is the demo loan-closure amount?
- How can I make a payment?

Example staff questions:
- What is today's collection?
- Show the overdue list.
- Which EMIs are due tomorrow?

## Run Tests

```powershell
python -m pytest -q
```

The latest test run completed with 6 tests passed. A dependency deprecation warning was reported but did not cause test failures.

## Security Considerations

- Use dummy data for demonstrations.
- Keep `.env`, local database files, and credentials out of version control.
- OTP `1234` is a demo value and must not be used for production authentication.
- Production deployments require secure OTP delivery, rate limiting, access controls, audit logging, privacy safeguards, and secure secret management.
- Customer and staff access must be validated against appropriate records and branch permissions.

## Current Limitations

This is a prototype, not a production-ready NBFC system.

- Chat responses currently use deterministic rule-based handling; live Gemini AI processing is not active.
- The demo OTP is not delivered through a real OTP provider.
- Payment responses provide guidance only; no actual payment is initiated.
- Human handover records a request but does not guarantee a live agent notification.
- The seeded SQLite database is for demonstration and is not connected to a live NBFC loan-management system.
- WhatsApp delivery requires provider configuration and an active webhook tunnel.

## Future Enhancements

- Integrate a secure OTP provider.
- Connect to an authorized loan-management system.
- Add a real payment gateway with appropriate safeguards.
- Implement agent notifications and handover tracking.
- Improve monitoring, audit logging, and role-based access testing.
- Add multilingual intent handling and optional AI-assisted responses with privacy controls.

## Disclaimer

This project is an educational and demonstration prototype. All customer records and financial figures used in the demo should be dummy data. It does not provide live financial services or process real payments.