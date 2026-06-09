"""
mock_agent.py
-------------
A tiny "fake brain" so the project RUNS WITH NO API KEY.

Why this exists:
When someone clones the repo, I don't want them to have to sign up for an API
key just to see it work. So if there's no key set, the project quietly uses
this mock instead of the real Claude model.

Important: this is NOT the clever part. It does *not* understand language the
way Claude does - it just matches keywords to decide which tool to call. But
it uses the EXACT SAME tools and database as the real agent, so the agentic
flow (pick a tool -> run real SQL -> answer from real data) is genuinely
demonstrated. When a real key is present, the real Claude model takes over and
the keyword guessing is gone.

Think of it as a stand-in for the demo.
"""

import re

from .tools import lookup_order, check_stock, get_policy, create_ticket


class MockAgent:
    """Keyword-based stand-in for the real Claude agent (used when no key)."""

    def run(self, user_message: str, history=None) -> dict:
        text = user_message.lower()
        tool_log = []

        # 1. Order lookup - if the message contains something like "ORD1001".
        order_match = re.search(r"ord\s?\d+", text)
        if order_match:
            order_id = order_match.group().replace(" ", "").upper()

            # If they also sound upset / want a refund, escalate instead.
            if any(w in text for w in ["refund", "broken", "damaged", "complaint", "angry"]):
                result = create_ticket(f"Customer issue about order {order_id}: {user_message}")
                tool_log.append({"tool": "create_ticket", "input": {}, "result": result})
                reply = (f"I'm sorry about that. I've opened {result['message']} "
                         f"regarding order {order_id}.")
                return self._wrap(reply, tool_log, history, user_message)

            result = lookup_order(order_id)
            tool_log.append({"tool": "lookup_order", "input": {"order_id": order_id}, "result": result})
            if result.get("found"):
                reply = (f"Order {result['order_id']} ({result['product']}) is currently "
                         f"'{result['status']}'.")
                if result.get("tracking"):
                    reply += f" Tracking: {result['tracking']}, ETA {result['eta']}."
            else:
                reply = result["message"]
            return self._wrap(reply, tool_log, history, user_message)

        # 2. Stock check.
        if any(w in text for w in ["stock", "available", "in stock", "have any", "buy"]):
            # crude product-name guess: longest word over 3 letters
            words = [w for w in re.findall(r"[a-z\-]+", text) if len(w) > 3]
            guess = max(words, key=len) if words else ""
            result = check_stock(guess)
            tool_log.append({"tool": "check_stock", "input": {"product_name": guess}, "result": result})
            if result.get("found"):
                state = "in stock" if result["in_stock"] else "out of stock"
                reply = f"The {result['name']} is {state} at RM{result['price']:.2f}."
            else:
                reply = "I couldn't find that product. Could you give me the exact name?"
            return self._wrap(reply, tool_log, history, user_message)

        # 3. Policy / FAQ.
        for topic in ["returns", "shipping", "warranty", "payment"]:
            # match 'return'/'returns', 'ship'/'shipping', etc.
            if topic[:5] in text or topic in text:
                result = get_policy(topic)
                tool_log.append({"tool": "get_policy", "input": {"topic": topic}, "result": result})
                reply = result["answer"] if result.get("found") else "Let me check on that."
                return self._wrap(reply, tool_log, history, user_message)

        # 4. Nothing matched -> escalate to a human.
        result = create_ticket(f"Unclassified request: {user_message}")
        tool_log.append({"tool": "create_ticket", "input": {}, "result": result})
        reply = (f"I'm not sure how to help with that directly, so {result['message']}")
        return self._wrap(reply, tool_log, history, user_message)

    def _wrap(self, reply, tool_log, history, user_message):
        """Match the real agent's return shape so server/cli don't care which ran."""
        new_history = list(history or [])
        new_history.append({"role": "user", "content": user_message})
        new_history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "tools_used": tool_log, "history": new_history}
