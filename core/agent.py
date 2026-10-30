import json
from core.llm import LLMProvider
from core.safety import needs_confirmation, ask_user
from tools.registry import get_schemas, run_tool
import tools.system
import tools.powershell
import tools.notifications

SYSTEM_PROMPT = """You are a Windows device assistant running on the user's computer.
You can use tools to check and fix problems on this computer.
Always use a tool to get real information instead of guessing.
System data changes all the time, so always call the tool again for every new question instead of reusing old results.
Use specific tools when available. Use run_powershell only when no other tool fits.
Some actions need user approval. If the user denies an action, do not try it again, explain what they can do instead.
Reply in the same language the user writes in. Keep answers short and clear."""


class Agent:
    def __init__(self):
        self.llm = LLMProvider()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

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

                if needs_confirmation(name, args) and not ask_user(name, args):
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

        return "Sorry, main is kaam ko complete nahi kar saka."