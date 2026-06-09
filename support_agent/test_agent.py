"""
test_agent.py
-------------
A quick end-to-end check. This actually calls the Claude API, so you need
your key set first. It runs three realistic questions and prints what tools
the agent decided to use - which is the clearest proof it's behaving like a
real agent and not just a chatbot.

Run with:  python test_agent.py
"""

from app.agent import SupportAgent
from app.database import init_db


def main():
    init_db()
    agent = SupportAgent()

    questions = [
        "Hi, where is my order ORD1001?",
        "Do you have the USB-C hub in stock?",
        "I want a refund on a damaged item, order ORD1002.",
    ]

    for q in questions:
        print("\n" + "=" * 60)
        print("USER:", q)
        result = agent.run(q)
        for t in result["tools_used"]:
            print(f"  -> used tool: {t['tool']}  args={t['input']}")
        print("AGENT:", result["reply"])


if __name__ == "__main__":
    main()
