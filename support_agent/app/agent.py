"""
agent.py
--------
This is the brain. It runs the *agentic loop*:

    1. Send the conversation + the list of tools to Claude.
    2. Claude either replies with text (done) OR asks to use a tool.
    3. If it asks for a tool, we run the real Python function and send the
       result back.
    4. Repeat until Claude gives a final text answer.

This loop is the whole idea of an "AI agent": the model plans, acts (via
tools), sees the result, and decides what to do next - instead of answering
blindly in one shot.
"""

import os
import json
import anthropic

from .tools import TOOL_SCHEMAS, TOOL_FUNCTIONS
from .mock_agent import MockAgent

# Model name - Sonnet is a good balance of smart + cheap for an agent like this.
MODEL = "claude-sonnet-4-5-20250929"

# The system prompt sets the agent's personality and rules. Keeping the rules
# tight here is what stops it from, say, escalating everything to a human.
SYSTEM_PROMPT = (
    "You are a helpful customer support agent for an online electronics store. "
    "Use the tools to look up real information before answering - never guess "
    "order details, stock, or policy. Be concise and friendly. "
    "Only open a ticket (escalate) if you truly cannot help with the tools you have."
)

# How many tool-use rounds we allow before giving up. A safety limit so a
# confused model can't loop forever and burn API credits.
MAX_TURNS = 6


class SupportAgent:
    def __init__(self, api_key: str | None = None):
        # If no key is passed, the SDK reads ANTHROPIC_API_KEY from the env.
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def run(self, user_message: str, history: list | None = None) -> dict:
        """
        Handle one user message. `history` is the prior messages (list of
        {"role","content"}) so the agent remembers the conversation.

        Returns a dict with the final reply and a log of which tools ran -
        the tool log is useful for a backend/dashboard to show what happened.
        """
        messages = list(history or [])
        messages.append({"role": "user", "content": user_message})

        tool_log = []  # record of tools used this turn, for transparency

        for _ in range(MAX_TURNS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )

            # Add the model's turn to the history exactly as it came back.
            messages.append({"role": "assistant", "content": response.content})

            # If the model didn't ask for a tool, it's finished talking.
            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                return {"reply": final_text, "tools_used": tool_log, "history": messages}

            # Otherwise, run every tool it asked for and collect the results.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                fn = TOOL_FUNCTIONS.get(block.name)
                if fn is None:
                    result = {"error": f"Unknown tool {block.name}"}
                else:
                    # block.input is the dict of arguments the model chose.
                    result = fn(**block.input)

                tool_log.append({"tool": block.name, "input": block.input, "result": result})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            # Feed all the tool results back as a single user turn, then loop.
            messages.append({"role": "user", "content": tool_results})

        # If we somehow hit the turn limit, fail gracefully.
        return {
            "reply": "Sorry, I'm having trouble completing that right now. "
                     "Let me open a ticket so a human can help.",
            "tools_used": tool_log,
            "history": messages,
        }


def build_agent():
    """
    Decide which agent to use.

    - If an ANTHROPIC_API_KEY is set, use the REAL Claude agent (smart, the
      real deal).
    - If not, fall back to the MockAgent so the project still runs with zero
      setup and zero cost. This is what lets anyone try it instantly.

    Everything else in the project calls build_agent() instead of creating an
    agent directly, so neither the server nor the CLI has to care which one
    they got - both return the same shape.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("[agent] ANTHROPIC_API_KEY found - using the real Claude agent.")
        return SupportAgent()
    print("[agent] No API key set - running in DEMO MODE with the mock agent. "
          "Set ANTHROPIC_API_KEY to use the real Claude model.")
    return MockAgent()
