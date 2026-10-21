"""Data layer. ALL database access goes through this class.

Today it reads the dummy SQLite database. When the NBFC gives access to its real loan software,
only this file changes (call their API or a read-only DB replica) - the bot, tools and
WhatsApp code stay exactly the same.
"""
from datetime import date
from typing import Optional

from .db import get_conn


def mask_phone(phone: str) -> str:
    """98XXXXXX10 style masking so full numbers never appear in logs or AI prompts."""
    return phone[:2] + "X" * max(len(phone) - 4, 0) + phone[-2:] if len(phone) > 4 else "XXXX"


class LoanRepository:
    # ---------- identity ----------
    def find_staff_by_phone(self, phone: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM staff WHERE phone = ?", (phone,)).fetchone()
        return dict(row) if row else None

    def find_customer_by_phone(self, phone: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM customers WHERE phone = ?", (phone,)).fetchone()
        return dict(row) if row else None

    def identify(self, phone: str) -> dict:
        """Returns {'role': 'manager'|'collection'|'customer'|'unknown', ...profile}.
        Staff are checked first, so a staff number is never treated as a customer."""
        staff = self.find_staff_by_phone(phone)
        if staff:
            return {"role": staff["role"], **staff}
        customer = self.find_customer_by_phone(phone)
        if customer:
            return {"role": "customer", **customer}
        return {"role": "unknown"}

    # ---------- OTP Verification Session Helpers ----------
    def is_customer_verified(self, phone: str) -> bool:
        with get_conn() as conn:
            row = conn.execute("SELECT is_verified FROM otp_sessions WHERE phone = ?", (phone,)).fetchone()
        return bool(row and row["is_verified"] == 1)

    def create_otp_session(self, phone: str, otp: str):
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO otp_sessions (phone, otp, is_verified) VALUES (?, ?, 0)",
                (phone, otp)
            )
            conn.commit()

    def verify_customer_session(self, phone: str):
        with get_conn() as conn:
            conn.execute(
                "UPDATE otp_sessions SET is_verified = 1 WHERE phone = ?",
                (phone,)
            )
            conn.commit()

    # ---------- customer data ----------
    def get_loans_for_customer(self, customer_id: int) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM loans WHERE customer_id = ?", (customer_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_next_emi(self, loan_no: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM emi_schedule WHERE loan_no = ? AND status = 'UNPAID' ORDER BY emi_no LIMIT 1",
                (loan_no,),
            ).fetchone()
        return dict(row) if row else None

    def get_pending_summary(self, loan_no: str) -> dict:
        """Total unpaid EMIs, and how much of that is already overdue."""
        today = date.today().isoformat()
        with get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS unpaid_count, COALESCE(SUM(amount), 0) AS unpaid_total, "
                "COALESCE(SUM(CASE WHEN due_date < ? THEN amount END), 0) AS overdue_amount, "
                "COALESCE(SUM(CASE WHEN due_date < ? THEN 1 END), 0) AS overdue_count "
                "FROM emi_schedule WHERE loan_no = ? AND status = 'UNPAID'",
                (today, today, loan_no),
            ).fetchone()
        return dict(row)

    # ---------- staff data ----------
    def todays_collection(self, branch_id: Optional[str] = None) -> dict:
        today = date.today().isoformat()
        sql = (
            "SELECT COUNT(*) AS count, COALESCE(SUM(p.amount), 0) AS total FROM payments p "
            "JOIN loans l ON l.loan_no = p.loan_no WHERE p.paid_on = ?"
        )
        params: list = [today]
        if branch_id:
            sql += " AND l.branch_id = ?"
            params.append(branch_id)
        with get_conn() as conn:
            return dict(conn.execute(sql, params).fetchone())

    def overdue_list(self, branch_id: Optional[str] = None) -> list[dict]:
        today = date.today().isoformat()
        sql = (
            "SELECT c.name, l.loan_no, l.branch_id, COUNT(e.id) AS overdue_emis, SUM(e.amount) AS overdue_amount, "
            "MIN(e.due_date) AS oldest_due FROM emi_schedule e "
            "JOIN loans l ON l.loan_no = e.loan_no JOIN customers c ON c.id = l.customer_id "
            "WHERE e.status = 'UNPAID' AND e.due_date < ?"
        )
        params: list = [today]
        if branch_id:
            sql += " AND l.branch_id = ?"
            params.append(branch_id)
        sql += " GROUP BY l.loan_no ORDER BY oldest_due"
        with get_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def emis_due_on(self, due_date: str, branch_id: Optional[str] = None) -> list[dict]:
        sql = (
            "SELECT c.name, c.phone, l.loan_no, l.branch_id, e.emi_no, e.amount, e.due_date FROM emi_schedule e "
            "JOIN loans l ON l.loan_no = e.loan_no JOIN customers c ON c.id = l.customer_id "
            "WHERE e.status = 'UNPAID' AND e.due_date = ?"
        )
        params: list = [due_date]
        if branch_id:
            sql += " AND l.branch_id = ?"
            params.append(branch_id)
        sql += " ORDER BY l.loan_no"
        with get_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]


repo = LoanRepository()