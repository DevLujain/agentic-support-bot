# Support Agent — an agentic AI customer service backend

A small project that shows how an **AI agent** works under the hood: a customer-support
agent with a Python/Flask backend, a SQLite database, and real Claude API tool-calling.

I kept it deliberately simple. The goal is to demonstrate the core idea of an agent clearly,
not to pile on features.

> **Try it with zero setup — no API key needed.**
> The project has a **demo mode**: if no API key is set, it runs a small built-in stand-in
> agent that still does real tool-calling against the real database. So you can clone it and
> watch it work in seconds, for free. The moment you add a Claude API key, the real Claude
> model takes over automatically. (More on this below.)

---

## What makes it an "agent" and not just a chatbot

A normal chatbot takes your message and replies with whatever the model makes up. That's
risky for customer support — it might invent an order status or a wrong return policy.

This is an **agent**: the model is given a set of *tools* (real Python functions that read
the database), and it decides which tool to call. The flow each turn is:

1. User asks something ("where is my order ORD1001?").
2. The model decides it needs the `lookup_order` tool and asks to call it.
3. The code runs the real SQL query and hands the result back.
4. The model reads the real data and writes the final answer.

So the answer is always grounded in real database data, not guessed. That loop (think →
use a tool → see the result → decide again) is the whole idea of an agent. It lives in
`app/agent.py`.

---

## The tools the agent has

| Tool | What it does |
|------|--------------|
| `lookup_order` | Finds an order by ID and returns status, tracking, ETA |
| `check_stock` | Checks if a product is in stock + its price |
| `get_policy` | Returns the FAQ answer for returns / shipping / warranty / payment |
| `create_ticket` | Escalates to a human by opening a support ticket |

The model is told (in the system prompt) to only escalate when it genuinely can't help, so
it doesn't dump everything on a human.

---

## Project structure

```
.
├── app/
│   ├── database.py    # SQLite setup + seed data (orders, products, FAQs)
│   ├── tools.py       # the 4 tools + their schemas for Claude
│   ├── agent.py       # the agentic loop (the real brain, uses Claude)
│   ├── mock_agent.py  # demo-mode stand-in so it runs with no API key
│   ├── server.py      # Flask API  (POST /chat, GET /health)
│   └── cli.py         # terminal chat client
├── test_agent.py      # end-to-end test that calls the real API
├── requirements.txt
├── .env.example       # copy to .env and add your key
└── README.md
```

Files are split **by concern** on purpose — database in one file, tools in another, the
loop in another — so each piece can be tested and debugged on its own.

---

## How to run it

### 1. Install the dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Add a Claude API key
**You can skip this and it still runs** — see "Demo mode" below.
If you want the real Claude model, set your own key:
```bash
export ANTHROPIC_API_KEY="sk-ant-...your key..."
```
Or copy `.env.example` to `.env` and paste your key there.

### 3a. Run it in the terminal (easiest)
```bash
python -m app.cli
```
It prints whether it's in demo mode or using the real model, then you can type things like:
- `where is my order ORD1001?`
- `do you have earbuds in stock?`
- `what is your return policy?`
- `I got a damaged keyboard on order ORD1004, I want a refund`  ← this should escalate

### 3b. Or run it as a backend API
```bash
python -m app.server
```
Then in another terminal:
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "where is order ORD1001?", "session_id": "abc"}'
```
The response includes both the reply **and** a `tools_used` list, so you can see exactly
what the agent did (useful for a dashboard or for debugging).

### 4. Run the test
```bash
python test_agent.py
```
This runs three realistic questions and prints which tools the agent chose for each.
(Needs a real key, since it tests the real Claude agent.)

---

## Demo mode vs real mode

- **No API key set → demo mode.** A small keyword-based stand-in agent (`app/mock_agent.py`)
  handles the conversation. It is *not* smart — it just matches keywords to pick a tool —
  but it calls the **exact same tools and the same database** as the real agent. So the
  agentic flow (pick a tool → run real SQL → answer from real data) is genuinely shown, and
  anyone can try the project instantly with no signup and no cost.
- **API key set → real mode.** The real Claude model (`app/agent.py`) takes over. Now the
  language understanding and tool decisions are actually intelligent, and the keyword
  guessing is gone entirely.

The switch happens automatically in `build_agent()`. The server and CLI don't know or care
which one they got, because both return the same shape.

> ⚠️ No API key is hardcoded into the project, and you shouldn't add one to the code either.
> Any real key pushed to a public repo gets scraped and charged to whoever owns it. Demo mode
> is the safe way to let people try it without a key.

---

## Design choices (and what I'd change for production)

I picked things that work now but noted where they'd grow:

- **SQLite** → easy, zero-setup, same SQL shape as MySQL. For production I'd move to
  **MySQL**. All DB access is in `database.py`, so swapping it is a one-file change.
- **In-memory session store** in `server.py` → fine for a demo, but it's lost on restart and
  won't work across multiple servers. In production I'd store sessions in **Redis** so the
  agent's memory survives and scales horizontally.
- **A turn limit (`MAX_TURNS`)** in the loop → stops a confused model from looping forever
  and burning credits. Small thing, but it's the kind of safety rail a real product needs.
- **Tool results returned to the API as JSON** → keeps the data structured so the model
  reads it reliably.

---

## Tech used

Python · Flask · SQLite · Anthropic Claude API (tool-calling) · a CLI and an HTTP API.
