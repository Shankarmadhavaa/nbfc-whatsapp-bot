Markdown
# NBFC WhatsApp Loan Chatbot (Prototype)

A secure, role-based WhatsApp AI chatbot built with FastAPI, SQLite, Google Gemini API, and Meta WhatsApp Cloud API for mobile phone loan EMIs.

## Features
- **Customer Verification:** Secure OTP gate (`1234` for demo) before showing any private loan details.
- **Hindi AI Queries:** Natural language understanding in Hindi for EMI dates, pending balances, and foreclosure amounts.
- **Role-Based Access Control (RBAC):** Separate permissions for Customers, Collection Staff (branch-restricted), and Managers.
- **Automated Operations:** Background scheduling for payment reminders and daily collection summaries.
- **Security:** Meta webhook signature verification (`X-Hub-Signature-256`), phone masking (`98XXXXXX10`), and audit logging.

## Local Setup & Testing
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
2. Run the test suite:
    Bash
    $env:PYTHONPATH="."; pytest -v
3. Start the server:
   Bash
   uvicorn app.main:app --reload
   
## Documentation
Detailed technical architecture, data security, and Core Loan Management System (LMS) integration notes can be found in docs/technical_note.md.


If you update this file locally in VS Code, just run these quick commands in your terminal to push the update to GitHub:
```bash
git add README.md
git commit -m "Update README.md"
git push origin main
