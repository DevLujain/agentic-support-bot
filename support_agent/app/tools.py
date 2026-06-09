"""
tools.py
--------
These are the "tools" the AI agent is allowed to use. This is the part that
makes it an *agent* rather than just a chatbot: the model doesn't make up an
answer, it decides to CALL one of these functions, we run the real Python /
SQL, and hand the result back.

Two things live here:
  1. The actual Python functions that do the work (talk to the database).
  2. TOOL_SCHEMAS - a description of each tool in the format Claude expects,
     so the model knows what tools exist and what arguments they need.
"""

from .database import get_connection


# ---------------------------------------------------------------------------
# 1. The real functions (each returns a plain dict so it's easy to send back)
# ---------------------------------------------------------------------------

def lookup_order(order_id: str) -> dict:
    """Find one order by its ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id.strip().upper(),)
    ).fetchone()
    conn.close()
    if row is None:
        return {"found": False, "message": f"No order found with ID {order_id}."}
    return {"found": True, **dict(row)}


def check_stock(product_name: str) -> dict:
    """Check if a product is in stock. Uses LIKE so partial names work."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM products WHERE name LIKE ?", (f"%{product_name.strip()}%",)
    ).fetchone()
    conn.close()
    if row is None:
        return {"found": False, "message": f"No product matching '{product_name}'."}
    return {
        "found": True,
        "name": row["name"],
        "price": row["price"],
        "in_stock": bool(row["in_stock"]),
    }


def get_policy(topic: str) -> dict:
    """Return a canned FAQ answer for a known topic."""
    conn = get_connection()
    row = conn.execute(
        "SELECT answer FROM faqs WHERE topic = ?", (topic.strip().lower(),)
    ).fetchone()
    conn.close()
    if row is None:
        # tell the model which topics DO exist, so it can pick a valid one
        conn = get_connection()
        topics = [r["topic"] for r in conn.execute("SELECT topic FROM faqs")]
        conn.close()
        return {"found": False, "available_topics": topics}
    return {"found": True, "topic": topic, "answer": row["answer"]}


def create_ticket(summary: str, customer: str = "unknown") -> dict:
    """Escalate to a human by opening a support ticket."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tickets (customer, summary) VALUES (?, ?)",
        (customer, summary),
    )
    conn.commit()
    ticket_id = cur.lastrowid
    conn.close()
    return {"created": True, "ticket_id": ticket_id,
            "message": f"Ticket #{ticket_id} opened. A human agent will follow up."}


# A simple registry so the agent loop can call a tool by name.
TOOL_FUNCTIONS = {
    "lookup_order": lookup_order,
    "check_stock": check_stock,
    "get_policy": get_policy,
    "create_ticket": create_ticket,
}


# ---------------------------------------------------------------------------
# 2. The schemas Claude reads to know what tools it has
# ---------------------------------------------------------------------------
# Each schema follows Anthropic's tool format: name, description, and a JSON
# schema for the inputs. The descriptions matter a lot - the model uses them
# to decide WHEN to call each tool, so I tried to make them clear.

TOOL_SCHEMAS = [
    {
        "name": "lookup_order",
        "description": "Look up a customer's order by its order ID (e.g. ORD1001). "
                       "Returns status, tracking number and estimated delivery date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID, like ORD1001"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "check_stock",
        "description": "Check whether a product is in stock and its price. "
                       "Accepts a full or partial product name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product name, e.g. 'earbuds'"}
            },
            "required": ["product_name"],
        },
    },
    {
        "name": "get_policy",
        "description": "Get the company policy / FAQ answer for a topic. "
                       "Valid topics: returns, shipping, warranty, payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "One of: returns, shipping, warranty, payment"}
            },
            "required": ["topic"],
        },
    },
    {
        "name": "create_ticket",
        "description": "Open a support ticket to escalate to a human. Use this only when "
                       "you genuinely cannot resolve the request with the other tools, "
                       "e.g. complaints, refunds needing approval, or anything unusual.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Short summary of the issue"},
                "customer": {"type": "string", "description": "Customer name if known"},
            },
            "required": ["summary"],
        },
    },
]
