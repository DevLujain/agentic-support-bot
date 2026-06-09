"""
database.py
-----------
Sets up a small SQLite database for the support agent to work with.

I went with SQLite because it needs zero setup (no server to run), but the
SQL and the table design are the same shape you'd use in MySQL/MongoDB-style
backends, so it scales to a real database later. I kept all data access in one
place (this file) to make swapping the backend easy.
"""

import sqlite3
import os

# Keep the db file next to this script so paths don't break when you run
# from a different folder.
DB_PATH = os.path.join(os.path.dirname(__file__), "support.db")


def get_connection():
    """One helper so every other file gets connections the same way."""
    conn = sqlite3.connect(DB_PATH)
    # row_factory lets me read columns by name (row["status"]) instead of by
    # index (row[2]) which is much easier to read.
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and put some fake data in, but only if it's empty."""
    conn = get_connection()
    cur = conn.cursor()

    # --- orders: what a customer bought and where it is ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id     TEXT PRIMARY KEY,
            customer     TEXT NOT NULL,
            product      TEXT NOT NULL,
            status       TEXT NOT NULL,
            tracking     TEXT,
            eta          TEXT
        )
    """)

    # --- products: simple catalogue the agent can look things up in ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            sku          TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            price        REAL NOT NULL,
            in_stock     INTEGER NOT NULL
        )
    """)

    # --- faqs: canned answers for common policy questions ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            topic        TEXT PRIMARY KEY,
            answer       TEXT NOT NULL
        )
    """)

    # --- tickets: where the agent escalates things it can't handle ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            customer     TEXT,
            summary      TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'open'
        )
    """)

    # Only seed if orders table is empty, so re-running doesn't duplicate data.
    cur.execute("SELECT COUNT(*) AS n FROM orders")
    if cur.fetchone()["n"] == 0:
        cur.executemany(
            "INSERT INTO orders VALUES (?,?,?,?,?,?)",
            [
                ("ORD1001", "Lujain",  "Wireless Earbuds",  "shipped",    "TRK55512", "2026-06-12"),
                ("ORD1002", "Ahmed",   "Laptop Stand",      "processing", None,        "2026-06-15"),
                ("ORD1003", "Mei Ling","USB-C Hub",         "delivered",  "TRK55290", "2026-06-05"),
                ("ORD1004", "Lujain",  "Mechanical Keyboard","cancelled", None,       None),
            ],
        )
        cur.executemany(
            "INSERT INTO products VALUES (?,?,?,?)",
            [
                ("SKU-EAR", "Wireless Earbuds",    199.00, 1),
                ("SKU-STD", "Laptop Stand",         89.00, 1),
                ("SKU-HUB", "USB-C Hub",           120.00, 0),
                ("SKU-KEY", "Mechanical Keyboard", 320.00, 1),
            ],
        )
        cur.executemany(
            "INSERT INTO faqs VALUES (?,?)",
            [
                ("returns",  "Items can be returned within 30 days with the original receipt for a full refund."),
                ("shipping", "Standard shipping takes 3-5 business days. Express shipping is 1-2 business days."),
                ("warranty", "All electronics come with a 12-month manufacturer warranty."),
                ("payment",  "We accept cards, online banking, and major e-wallets."),
            ],
        )
        conn.commit()

    conn.close()


if __name__ == "__main__":
    # Lets you build the db by hand: `python -m app.database`
    init_db()
    print("Database ready at", DB_PATH)
