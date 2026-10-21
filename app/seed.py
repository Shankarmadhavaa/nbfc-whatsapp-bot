"""Creates the demo database with DUMMY data only. Run:  python -m app.seed

All dates are relative to today, so the demo always has EMIs due tomorrow, missed yesterday, paid today, etc.
Replace the DEMO_*_PHONE values in .env with your own test numbers so WhatsApp messages reach you.
"""
import os
from datetime import date, timedelta

from . import config
from .db import get_conn, init_db

TODAY = date.today()

BRANCHES = [("A", "Branch A - Kottayam"), ("B", "Branch B - Ernakulam")]

# (name, branch, handset, price, emi, tenure, emis_already_paid, next_unpaid_due_offset_days, paid_today)
# next_unpaid_due_offset_days: days from today to the next unpaid EMI (negative = already overdue)
CUSTOMERS = [
    ("Ramesh Kumar",     "A", "Samsung Galaxy M14",  14999, 1500, 10, 4,   1, False),  # EMI due tomorrow (demo customer)
    ("Sunita Devi",      "A", "Redmi Note 12",       16999, 1700, 10, 3,   3, False),  # due in 3 days -> reminder
    ("Mohammed Irfan",   "A", "Vivo Y27",            15499, 1550, 10, 5,  -1, False),  # missed yesterday -> follow-up
    ("Anita Sharma",     "B", "Realme C55",          12999, 1300, 10, 2, -35, False),  # 2 EMIs overdue
    ("Vijay Singh",      "B", "Oppo A58",            13999, 1400, 10, 6,  12, False),
    ("Pooja Verma",      "A", "Apple iPhone 13",     45999, 4600, 10, 4,  30, True),   # paid today
    ("Deepak Yadav",     "B", "Samsung Galaxy A34",  25999, 2600, 10, 7,  30, True),   # paid today
    ("Kavita Joshi",     "B", "Poco X5",             17999, 1800, 10, 1,   8, False),
    ("Suresh Patel",     "A", "Realme Narzo 60",     18999, 1900, 10, 8,  30, True),   # paid today
    ("Farhan Ali",       "B", "Redmi 12",            10999, 1100, 10, 3, -10, False),  # 1 EMI overdue
]


def _phone(i: int) -> str:
    """Customer 0 gets the DEMO_CUSTOMER_PHONE; the rest get fake numbers."""
    if i == 0:
        return config.DEMO_CUSTOMER_PHONE
    return f"9190000100{i:02d}"


def seed() -> None:
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()

    with get_conn() as conn:
        conn.executemany("INSERT INTO branches (id, name) VALUES (?, ?)", BRANCHES)

        conn.executemany(
            "INSERT INTO staff (name, phone, role, branch_id) VALUES (?, ?, ?, ?)",
            [
                ("Amit Singh (Collection, Branch A)", config.DEMO_COLLECTION_PHONE, "collection", "A"),
                ("Neha Gupta (Collection, Branch B)", "919000000012", "collection", "B"),
                ("Rajesh Mehta (Manager)", config.DEMO_MANAGER_PHONE, "manager", None),
            ],
        )

        for i, (name, branch, handset, price, emi, tenure, paid_count, offset, paid_today) in enumerate(CUSTOMERS):
            cur = conn.execute(
                "INSERT INTO customers (name, phone, branch_id) VALUES (?, ?, ?)",
                (name, _phone(i), branch),
            )
            customer_id = cur.lastrowid
            loan_no = f"LN{1001 + i}"
            conn.execute(
                "INSERT INTO loans (loan_no, customer_id, branch_id, handset, handset_price, emi_amount, tenure) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (loan_no, customer_id, branch, handset, price, emi, tenure),
            )

            next_due = TODAY + timedelta(days=offset)
            for k in range(1, tenure + 1):
                due = next_due + timedelta(days=30 * (k - (paid_count + 1)))
                paid = k <= paid_count
                conn.execute(
                    "INSERT INTO emi_schedule (loan_no, emi_no, due_date, amount, status) VALUES (?, ?, ?, ?, ?)",
                    (loan_no, k, due.isoformat(), emi, "PAID" if paid else "UNPAID"),
                )
                if paid:
                    # the last paid EMI is paid today for the "paid_today" customers, others paid on the due date
                    paid_on = TODAY if (paid_today and k == paid_count) else due
                    conn.execute(
                        "INSERT INTO payments (loan_no, emi_no, amount, paid_on, mode) VALUES (?, ?, ?, ?, ?)",
                        (loan_no, k, emi, paid_on.isoformat(), "UPI" if k % 2 else "CASH"),
                    )

    print(f"Seeded {len(CUSTOMERS)} customers into {config.DB_PATH} (today = {TODAY})")


if __name__ == "__main__":
    seed()
