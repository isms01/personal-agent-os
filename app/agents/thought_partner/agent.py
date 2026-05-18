from datetime import datetime
from pathlib import Path

_CONTRADICTION_PROMPT = """以下は、ある人物が断続的に記録した思考・意見のログです。
最新の発言を踏まえ、ログ全体から矛盾・葛藤・ズレを1つだけ簡潔に指摘してください。
矛盾が見当たらない場合は、何も返さず空文字のみを返してください。
指摘は1〜2文で、断定せず柔らかく表現してください。"""


class ThoughtPartnerAgent:
    def __init__(self, llm_client, log_dir: Path = Path("logs")):
        self.llm_client = llm_client
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / "thoughts.txt"
        self.thoughts: list[str] = []

    def add(self, text: str) -> tuple[str | None, int]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{now}] {text}"
        self.thoughts.append(entry)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
        return self._check_contradiction()

    def _check_contradiction(self) -> tuple[str | None, int]:
        if len(self.thoughts) < 2:
            return None, 0
        log_text = "\n".join(self.thoughts)
        result, input_tokens, output_tokens = self.llm_client.generate(
            system_prompt=_CONTRADICTION_PROMPT,
            user_input=log_text,
        )
        result = result.strip()
        return (result if result else None), (input_tokens + output_tokens)
