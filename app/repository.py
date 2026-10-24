
"""Data layer for the NBFC chatbot demo.

All database access goes through this repository.
Uses SQLite and dummy data for local development.
"""

import hashlib
import hmac
from datetime import date, datetime, timedelta
from typing import Optional

from .db import get_conn


OTP_EXPIRY_MINUTES = 5
VERIFIED_SESSION_MINUTES = 30
OTP_MAX_ATTEMPTS = 3


def mask_phone(phone: str) -> str:
    """Mask phone numbers before displaying them in logs."""
    if len(phone) <= 4:
        return "XXXX"
    return phone[:2] + "X" * (len(phone) - 4) + phone[-2:]


class LoanRepository:
    # ---------- Identity ----------

    def find_staff_by_phone(self, phone: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM staff WHERE phone = ?",
                (phone,),
            ).fetchone()
        return dict(row) if row else None

    def find_customer_by_phone(self, phone: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE phone = ?",
                (phone,),
            ).fetchone()
        return dict(row) if row else None

    def identify(self, phone: str) -> dict:
        """Identify staff first, then registered customers."""
        staff = self.find_staff_by_phone(phone)
        if staff:
            return {"role": staff["role"], **staff}

        customer = self.find_customer_by_phone(phone)
        if customer:
            return {"role": "customer", **customer}

        return {"role": "unknown"}

    # ---------- OTP Session Helpers ----------

    def otp_challenge_state(self, phone: str) -> str:
        """Return none, active, expired, locked, or verified."""
        now = datetime.now()

        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT otp_hash, expires_at, attempts,
                       is_verified, verified_until
                FROM otp_sessions
                WHERE phone = ?
                """,
                (phone,),
            ).fetchone()

        if not row:
            return "none"

        if row["is_verified"] == 1:
            verified_until = row["verified_until"]
            if verified_until:
                try:
                    if datetime.fromisoformat(verified_until) > now:
                        return "verified"
                except ValueError:
                    pass
            return "expired"

        if row["attempts"] >= OTP_MAX_ATTEMPTS:
            return "locked"

        if not row["otp_hash"] or not row["expires_at"]:
            return "expired"

        try:
            expiry = datetime.fromisoformat(row["expires_at"])
        except ValueError:
            return "expired"

        if expiry <= now:
            return "expired"

        return "active"

    def is_customer_verified(self, phone: str) -> bool:
        """True only when the customer has a valid, unexpired session."""
        return self.otp_challenge_state(phone) == "verified"

    def create_otp_session(self, phone: str, otp: str) -> None:
        """Create or replace a short-lived OTP challenge.

        The OTP is stored as a SHA-256 hash, not in plain text.
        This is for the local demo; real OTP delivery is not implemented.
        """
        now = datetime.now()
        expires_at = (
            now + timedelta(minutes=OTP_EXPIRY_MINUTES)
        ).isoformat(timespec="seconds")

        otp_hash = hashlib.sha256(
            otp.encode("utf-8")
        ).hexdigest()

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO otp_sessions
                    (phone, otp, otp_hash, expires_at, attempts,
                     is_verified, verified_until)
                VALUES (?, NULL, ?, ?, 0, 0, NULL)
                ON CONFLICT(phone) DO UPDATE SET
                    otp = NULL,
                    otp_hash = excluded.otp_hash,
                    expires_at = excluded.expires_at,
                    attempts = 0,
                    is_verified = 0,
                    verified_until = NULL
                """,
                (phone, otp_hash, expires_at),
            )

    def verify_customer_session(
        self,
        phone: str,
        entered_otp: str,
    ) -> bool:
        """Verify a matching OTP before expiry and within the attempt limit."""
        if not isinstance(entered_otp, str):
            return False

        if not entered_otp.isdigit() or len(entered_otp) != 4:
            return False

        now = datetime.now()
        now_text = now.isoformat(timespec="seconds")

        entered_hash = hashlib.sha256(
            entered_otp.encode("utf-8")
        ).hexdigest()

        with get_conn() as conn:
            # Serialise verification attempts to reduce concurrent
            # attempts exceeding the configured limit.
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT otp_hash, expires_at, attempts
                FROM otp_sessions
                WHERE phone = ? AND is_verified = 0
                """,
                (phone,),
            ).fetchone()

            if (
                not row
                or not row["otp_hash"]
                or not row["expires_at"]
            ):
                return False

            try:
                expiry = datetime.fromisoformat(row["expires_at"])
            except ValueError:
                return False

            attempts = row["attempts"] or 0

            if expiry <= now or attempts >= OTP_MAX_ATTEMPTS:
                return False

            if not hmac.compare_digest(
                row["otp_hash"],
                entered_hash,
            ):
                conn.execute(
                    """
                    UPDATE otp_sessions
                    SET attempts = attempts + 1
                    WHERE phone = ? AND is_verified = 0
                    """,
                    (phone,),
                )
                return False

            verified_until = (
                now + timedelta(minutes=VERIFIED_SESSION_MINUTES)
            ).isoformat(timespec="seconds")

            result = conn.execute(
                """
                UPDATE otp_sessions
                SET is_verified = 1,
                    verified_until = ?
                WHERE phone = ?
                  AND is_verified = 0
                  AND expires_at > ?
                  AND attempts < ?
                """,
                (
                    verified_until,
                    phone,
                    now_text,
                    OTP_MAX_ATTEMPTS,
                ),
            )

            return result.rowcount == 1

    # ---------- Customer Loan Data ----------

    def get_loans_for_customer(self, customer_id: int) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM loans WHERE customer_id = ?",
                (customer_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_next_emi(self, loan_no: str) -> Optional[dict]:
        today = date.today().isoformat()

        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM emi_schedule
                WHERE loan_no = ?
                  AND status = 'UNPAID'
                  AND due_date >= ?
                ORDER BY due_date, emi_no
                LIMIT 1
                """,
                (loan_no, today),
            ).fetchone()

        return dict(row) if row else None

    def get_pending_summary(self, loan_no: str) -> dict:
        """Return unpaid EMI totals and overdue totals."""
        today = date.today().isoformat()

        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS unpaid_count,
                    COALESCE(SUM(amount), 0) AS unpaid_total,
                    COALESCE(
                        SUM(
                            CASE WHEN due_date < ?
                            THEN amount ELSE 0 END
                        ), 0
                    ) AS overdue_amount,
                    COALESCE(
                        SUM(
                            CASE WHEN due_date < ?
                            THEN 1 ELSE 0 END
                        ), 0
                    ) AS overdue_count
                FROM emi_schedule
                WHERE loan_no = ? AND status = 'UNPAID'
                """,
                (today, today, loan_no),
            ).fetchone()

        return dict(row)

    # ---------- Staff Reports ----------

    def todays_collection(
        self,
        branch_id: Optional[str] = None,
    ) -> dict:
        today = date.today().isoformat()

        sql = """
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(p.amount), 0) AS total
            FROM payments p
            JOIN loans l ON l.loan_no = p.loan_no
            WHERE p.paid_on = ?
        """
        params = [today]

        if branch_id:
            sql += " AND l.branch_id = ?"
            params.append(branch_id)

        with get_conn() as conn:
            row = conn.execute(sql, params).fetchone()

        return dict(row)

    def overdue_list(
        self,
        branch_id: Optional[str] = None,
    ) -> list[dict]:
        today = date.today().isoformat()

        sql = """
            SELECT
                c.name,
                l.loan_no,
                l.branch_id,
                COUNT(e.id) AS overdue_emis,
                COALESCE(SUM(e.amount), 0) AS overdue_amount,
                MIN(e.due_date) AS oldest_due
            FROM emi_schedule e
            JOIN loans l ON l.loan_no = e.loan_no
            JOIN customers c ON c.id = l.customer_id
            WHERE e.status = 'UNPAID'
              AND e.due_date < ?
        """
        params = [today]

        if branch_id:
            sql += " AND l.branch_id = ?"
            params.append(branch_id)

        sql += """
            GROUP BY c.name, l.loan_no, l.branch_id
            ORDER BY oldest_due
        """

        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    def emis_due_on(
        self,
        due_date: str,
        branch_id: Optional[str] = None,
    ) -> list[dict]:
        sql = """
            SELECT
                c.name,
                c.phone,
                l.loan_no,
                l.branch_id,
                e.emi_no,
                e.amount,
                e.due_date
            FROM emi_schedule e
            JOIN loans l ON l.loan_no = e.loan_no
            JOIN customers c ON c.id = l.customer_id
            WHERE e.status = 'UNPAID'
              AND e.due_date = ?
        """
        params = [due_date]

        if branch_id:
            sql += " AND l.branch_id = ?"
            params.append(branch_id)

        sql += " ORDER BY l.loan_no, e.emi_no"

        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]


repo = LoanRepository()