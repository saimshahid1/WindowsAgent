import re
import warnings

warnings.filterwarnings("ignore", module="pycaw")

import yaml
from core.agent import Agent
from core.safety import is_yes


def remove_repeat(text):
    if not text:
        return text
    t = text.strip()
    half = len(t) // 2
    for cut in range(half - 2, half + 3):
        a, b = t[:cut].strip(), t[cut:].strip()
        if a and a == b:
            return a
    sentences = re.split(r"(?<=[.!?])\s*", t)
    seen, result = set(), []
    for s in sentences:
        key = s.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(s.strip())
    return " ".join(result)


def main():
    with open("config.yaml", "r") as f:
        voice_cfg = yaml.safe_load(f).get("voice", {})

    mode = input("Choose mode, t for text or v for voice: ").strip().lower()
    voice_mode = mode == "v"

    stt = tts = None
    confirm = None

    if voice_mode:
        from core.voice import SpeechToText, TextToSpeech
        stt = SpeechToText(
            model_size=voice_cfg.get("stt_model", "small"),
            language=voice_cfg.get("stt_language", "en"),
        )
        tts = TextToSpeech(voice=voice_cfg.get("tts_voice", "en-US-AriaNeural"))

        def voice_confirm(name, args):
            print(f"\n  Agent wants to run {name}")
            if "command" in args:
                print(f"  Command {args['command']}")
            reason = args.get("reason") or f"I need your permission to {name.replace('_', ' ')}"
            question = f"{reason.rstrip('.')}. Should I go ahead?"
            print(f"  Agent: {question}")
            tts.speak(question)

            answer = stt.listen()
            allowed = is_yes(answer)
            print(f"  You (voice): {answer}  ->  {'allowed' if allowed else 'denied'}")
            return allowed

        confirm = voice_confirm

    agent = Agent(voice_mode=voice_mode, confirm=confirm)
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

        reply = remove_repeat(agent.run(user_input))
        print(f"Agent: {reply}\n")
        if tts:
            tts.speak(reply)


if __name__ == "__main__":
    main()