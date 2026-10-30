from dotenv import load_dotenv
load_dotenv()
import yaml
from litellm import completion

class LLMProvider:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)["llm"]
        self.model = cfg["model"]
        self.api_base = cfg.get("api_base")
        self.api_key = cfg.get("api_key")
        self.temperature = cfg.get("temperature", 0.2)

    def chat(self, messages, tools=None):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if tools:
            kwargs["tools"] = tools

        response = completion(**kwargs)
        return response.choices[0].message