import json
from core.llm import LLMProvider
from core.safety import needs_confirmation, ask_user
from tools.registry import get_schemas, run_tool
import tools.system
import tools.powershell
import tools.notifications
import tools.audio
import tools.apps

SYSTEM_PROMPT = """You are a Windows device assistant running on the user's computer.
You can use tools to check and fix problems on this computer.
Always use a tool to get real information instead of guessing.
System data changes all the time, so always call the tool again for every new question instead of reusing old results.
Use specific tools when available. Use run_powershell only when no other tool fits.
To open an app use open_app. To close an app use close_app with the app name. Never use run_powershell to start, stop or kill apps.
Never ask the user for permission in your reply. The system automatically asks the user before risky actions, so just call the tool.
If the user denies an action, do not try it again, explain what they can do instead.
Reply in the same language the user writes in. Keep answers short and clear."""

VOICE_PROMPT = """
Your replies will be read aloud by a voice.
Answer in one to three short spoken sentences.
Never use tables, lists, markdown, symbols or emojis."""


class Agent:
    def __init__(self, voice_mode=False, confirm=None):
        self.llm = LLMProvider()
        self.confirm = confirm or ask_user
        prompt = SYSTEM_PROMPT + (VOICE_PROMPT if voice_mode else "")
        self.messages = [{"role": "system", "content": prompt}]

    def run(self, user_input, max_steps=5):
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(max_steps):
            reply = self.llm.chat(self.messages, tools=get_schemas())

            if not reply.tool_calls:
                self.messages.append({"role": "assistant", "content": reply.content})
                return reply.content

            self.messages.append({
                "role": "assistant",
                "content": reply.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in reply.tool_calls
                ],
            })

            for tc in reply.tool_calls:
                name = tc.function.name
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args) if args.strip() else {}

                if needs_confirmation(name, args) and not self.confirm(name, args):
                    result = "User denied this action."
                else:
                    print(f"  [tool] {name}")
                    result = run_tool(name, args)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": result,
                })

        return "Sorry, I could not complete this task."