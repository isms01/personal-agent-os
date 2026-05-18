import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from app.agents.thought_partner.agent import ThoughtPartnerAgent

load_dotenv()


class AnthropicClient:
    def __init__(self):
        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def generate(self, system_prompt: str, user_input: str) -> tuple[str, int, int]:
        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
        )
        usage = message.usage
        return message.content[0].text, usage.input_tokens, usage.output_tokens


def main():
    agent = ThoughtPartnerAgent(llm_client=AnthropicClient(), log_dir=Path("logs"))
    print(f"思考ログ開始: {agent.log_file}\n終了: Ctrl+C\n")
    while True:
        text = input("> ").strip()
        if not text:
            continue
        contradiction, tokens = agent.add(text)
        token_hint = f"\033[2m({tokens} tokens)\033[0m" if tokens else ""
        if contradiction:
            print(f"[矛盾検出] {contradiction} {token_hint}\n")
        else:
            print(f"ログとして保存しました {token_hint}\n")


if __name__ == "__main__":
    main()
