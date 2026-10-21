"""SQLite connection + schema. SQLite is used for the demo; production would use PostgreSQL or the loan software's API."""
import sqlite3
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS branches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('collection', 'manager')),
    branch_id TEXT REFERENCES branches(id)   -- NULL for managers (all branches)
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    branch_id TEXT NOT NULL REFERENCES branches(id)
);

CREATE TABLE IF NOT EXISTS loans (
    loan_no TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    branch_id TEXT NOT NULL REFERENCES branches(id),
    handset TEXT NOT NULL,
    handset_price INTEGER NOT NULL,
    emi_amount INTEGER NOT NULL,
    tenure INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS emi_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_no TEXT NOT NULL REFERENCES loans(loan_no),
    emi_no INTEGER NOT NULL,
    due_date TEXT NOT NULL,          -- ISO date YYYY-MM-DD
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'UNPAID' CHECK (status IN ('PAID', 'UNPAID')),
    UNIQUE (loan_no, emi_no)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_no TEXT NOT NULL REFERENCES loans(loan_no),
    emi_no INTEGER,
    amount INTEGER NOT NULL,
    paid_on TEXT NOT NULL,           -- ISO date
    mode TEXT NOT NULL DEFAULT 'UPI'
);

-- Used from Day 2 onwards (Updated to match repository checks)
CREATE TABLE IF NOT EXISTS otp_sessions (
    phone TEXT PRIMARY KEY,
    otp TEXT,
    otp_hash TEXT,
    expires_at TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    is_verified INTEGER DEFAULT 0,
    verified_until TEXT              -- session valid until this time after successful OTP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    phone TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS handover (
    phone TEXT PRIMARY KEY,
    reason TEXT,
    started_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)