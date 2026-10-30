import warnings

warnings.filterwarnings("ignore", module="pycaw")

from core.agent import Agent


def main():
    agent = Agent()

    mode = input("Choose mode, t for text or v for voice: ").strip().lower()
    stt = None
    if mode == "v":
        from core.voice import SpeechToText
        stt = SpeechToText()

    print("Windows Agent ready. Type or say 'exit' to quit.\n")

    while True:
        if stt:
            user_input = stt.listen()
            print(f"You (voice): {user_input}")
        else:
            user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower().strip(" .!") in ("exit", "quit"):
            break

        reply = agent.run(user_input)
        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()