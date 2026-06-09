"""
cli.py
------
A command-line way to talk to the agent. Two reasons it exists:
  1. Quick to test the agent without starting the web server.
  2. A clean terminal interface is a simple, dependency-free way to demo it.

Run it with:  python -m app.cli
Type 'quit' to exit.
"""

from .agent import build_agent
from .database import init_db


def main():
    init_db()  # ensure the database is set up
    agent = build_agent()
    history = []

    print("=" * 55)
    print("  Support Agent  (type 'quit' to exit)")
    print("=" * 55)
    print("Try: 'where is my order ORD1001?'  or  'do you have earbuds in stock?'\n")

    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            break

        if user.lower() in {"quit", "exit", "q"}:
            print("bye!")
            break
        if not user:
            continue

        result = agent.run(user, history=history)
        history = result["history"]  # keep the conversation going

        # Show which tools the agent used - nice for seeing it "think".
        if result["tools_used"]:
            for t in result["tools_used"]:
                print(f"   [tool] {t['tool']}({t['input']})")

        print(f"bot > {result['reply']}\n")


if __name__ == "__main__":
    main()
