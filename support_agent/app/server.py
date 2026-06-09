"""
server.py
---------
A small Flask backend that puts the agent behind an HTTP API. This is the
backend / API layer of the project.

Endpoints:
  GET  /health          -> quick check the server is alive
  POST /chat            -> send a message, get the agent's reply

I keep conversation history server-side in a dict keyed by session_id, so the
agent remembers the conversation across requests. In production you'd store
this in Redis instead of memory - I left a note in the README about that.
"""

from flask import Flask, request, jsonify

from .agent import build_agent
from .database import init_db

app = Flask(__name__)
agent = build_agent()

# Very simple in-memory session store: {session_id: [messages...]}
# Fine for a demo; swap for Redis in production.
SESSIONS = {}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"error": "message is required"}), 400

    history = SESSIONS.get(session_id, [])
    result = agent.run(message, history=history)

    # Save the updated history so the next message remembers this one.
    SESSIONS[session_id] = result["history"]

    return jsonify({
        "reply": result["reply"],
        "tools_used": result["tools_used"],
    })


if __name__ == "__main__":
    init_db()  # make sure the database exists before serving
    app.run(host="0.0.0.0", port=5000, debug=True)
