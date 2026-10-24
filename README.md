# NBFC WhatsApp Chatbot

A Python-based WhatsApp chatbot prototype for Non-Banking Financial Companies (NBFCs). It demonstrates customer loan enquiries, OTP verification, staff collection reports, and human-support handover using a local SQLite database.

## Features

- **Customer verification:** Demo OTP workflow with expiry and attempt limits.
- **Loan information:** Retrieve the next EMI and outstanding balance, and provide guidance for loan-closure enquiries.
- **Payment guidance:** Answer payment-related questions without initiating real payments.
- **Staff reports:** Demonstrate collection summaries, overdue EMI lists, and upcoming dues.
- **Human-support handover:** Record requests for human assistance in the local demo database.
- **WhatsApp integration:** Webhook endpoints for the Twilio WhatsApp Sandbox and Meta-style JSON messages.
- **Local simulation:** Test chatbot conversations without consuming WhatsApp messages.
- **Automated testing:** Validate core chatbot functionality using Pytest.

## Technology Stack

- **Language:** Python
- **Backend framework:** FastAPI
- **Database:** SQLite
- **ASGI server:** Uvicorn
- **Testing:** Pytest
- **WhatsApp integration:** Twilio WhatsApp Sandbox
- **Webhook tunnelling:** ngrok

## Project Setup

### 1. Open the project directory

Open PowerShell and navigate to the project directory:

```powershell
cd "C:\Users\SHANKAR MADHAVA\Downloads\nbfc-whatsapp-bot-day1\nbfc-whatsapp-bot"
```

Adjust the path if you have moved the project to another location.

### 2. Activate the virtual environment

The virtual environment is located in the parent directory of the project.

```powershell
..\.venv\Scripts\Activate.ps1
```

If the virtual environment is already active, you can skip this step.

### 3. Configure environment variables

Review `.env.example` and configure the environment variables required by the application.

Never commit real API keys, access tokens, passwords, or other credentials to version control.

### 4. Start the application

Run the following commands from the project directory:

```powershell
$env:PYTHONPATH="."
python -m uvicorn app.main:app --reload
```

Keep the terminal running while using the application. Stop the development server with `Ctrl + C` when finished.

### 5. Open the API documentation

Once the application is running, open these addresses in your browser:

- **Health check:** http://127.0.0.1:8000/health
- **Interactive API documentation:** http://127.0.0.1:8000/docs

## Local Demo

The project includes seeded fictional customer and staff records for demonstration purposes.

The local demo OTP is `1234`. This is a fixed demonstration value, not a real OTP delivery or production authentication mechanism.

Use the local `/simulate` endpoint to test conversations without sending WhatsApp messages. Use only fictional data during demonstrations.

### Example customer queries

- What is my next EMI?
- What is my outstanding balance?
- How can I make a payment?
- I need help with loan closure.
- I want to speak to a support agent.

The chatbot can provide available loan information and payment guidance. It does not initiate payments or calculate an official foreclosure quotation.

### Example staff queries

- What is today's collection?
- Show the overdue list.
- Which EMIs are due tomorrow?

Staff reports and access permissions should be tested only with the supplied fictional records.

## Run Automated Tests

From the project directory, run:

```powershell
python -m pytest -q
```

The latest recorded test run completed with **6 tests passed**. A dependency deprecation warning was reported, but it did not cause the tests to fail.

Run the command again after making code changes to verify the current test results.

## Security and Privacy Considerations

- Use fictional customer and financial data for demonstrations.
- Keep `.env`, local database files, credentials, and other sensitive information out of version control.
- Never use the fixed demo OTP `1234` for real customer authentication.
- Validate customer identity before disclosing account or loan information.
- Enforce staff authorization and appropriate branch-level access restrictions.
- Protect webhook endpoints with provider signature verification and suitable request validation.
- Use rate limiting, audit logging, secure secret management, and appropriate error handling.
- Protect customer information according to applicable privacy requirements and organizational policies.

A production deployment requires a security review, authorized integrations, and appropriate operational controls.

## Current Limitations

This project is an educational prototype and is **not production-ready**.

- **Rule-based responses:** The current implementation uses deterministic rule-based handling. Live Gemini AI processing is not active.
- **Demo OTP:** The OTP is fixed for demonstration and is not delivered through a real OTP provider.
- **Payment processing:** The chatbot provides payment guidance only. It does not initiate or process payments.
- **Loan foreclosure:** The chatbot does not calculate the official foreclosure amount. Customers must obtain an official quotation from their branch or authorized loan provider.
- **Human support:** A handover request is recorded locally, but a live-agent notification or assignment is not implemented.
- **Demo database:** The seeded SQLite database is not connected to a live NBFC loan-management system.
- **WhatsApp delivery:** Live WhatsApp demonstrations require appropriate provider configuration and an active webhook tunnel.
- **Production security:** Additional authentication, authorization, monitoring, and security controls are required before handling real customer data.

## Future Enhancements

- Integrate a secure OTP delivery and verification provider.
- Connect to an authorized loan-management system through secure APIs.
- Integrate a payment gateway with appropriate safeguards and transaction verification.
- Implement live-agent notifications and handover tracking.
- Strengthen role-based authorization and branch-level access controls.
- Add webhook signature verification, monitoring, and audit logging.
- Expand automated tests for security, authorization, and integration scenarios.
- Improve multilingual intent handling and optionally add AI-assisted responses with suitable privacy controls.

## Disclaimer

This project is an educational and demonstration prototype. All customer records and financial figures used in the demo must be fictional. The application does not provide live financial services, process real payments, or replace an authorized NBFC's loan-management system. It must not be used to handle real customer data or production financial transactions without appropriate implementation, authorization, and security review.