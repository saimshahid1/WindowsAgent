from core.agent import Agent


def main():
    agent = Agent()
    print("Windows Agent ready. Exit ke liye 'exit' likho.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        reply = agent.run(user_input)
        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()