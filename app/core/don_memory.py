"""
Don Agent の会話記憶（1 会話 = 1 ファイルの追記型）。
一次記録は不変とし、過去の相談を構造化して保存、次回の会話で参照する。
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

from app.core.context_classifier import InputContext

MODEL = "claude-sonnet-5"
DEFAULT_MEMORY_DIR = Path("logs/don_memory")
DEFAULT_LOAD_COUNT = 10

JST = timezone(timedelta(hours=9))


class ConversationRecord(BaseModel):
    date: str  # 例: "2026-07-06 21:30"
    summary: str
    homework: str | None
    keywords: list[str]


_SUMMARIZE_SYSTEM_PROMPT = """\
あなたは Don Agent の会話記録エンジンです。
今回の相談と Don の応答を読み、次回の会話で Don が過去の文脈を
思い出すための記録を JSON のみで返してください。

## 記録の基準
- summary: 相談内容と Don の応答の要点（3〜5 文、事実ベースで端的に）
- homework: Don が「次に聞かせてほしい」と求めた内容。なければ null
- keywords: 過去相談の検索に使うキーワード（固有名詞・案件名など）

## 出力 JSON の形式（他のテキストは一切出力しない）
{
  "summary": "...",
  "homework": "... または null",
  "keywords": ["..."]
}
"""


def summarize_conversation(
    client: Anthropic,
    user_input: str,
    response_text: str,
    context: InputContext,
) -> ConversationRecord:
    user_content = (
        f"ユーザーの相談:\n{user_input}\n\n"
        f"Don の応答:\n{response_text}\n\n"
        f"文脈サマリー: {context.summary}"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        # JSON のみを返す呼び出し。思考トークンで出力が切れないよう思考オフ
        thinking={"type": "disabled"},
        system=_SUMMARIZE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    block = response.content[0]
    raw = getattr(block, "text", None)
    if not isinstance(raw, str):
        raise ValueError(f"Unexpected response block type: {type(block)}")
    raw = raw.strip()

    # ```json ``` ブロックへの対応
    if raw.startswith("```"):
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    data = json.loads(raw)

    # 分類器のキーワードと統合（順序を保って重複排除）
    merged = list(dict.fromkeys([*data.get("keywords", []), *context.search_keywords]))

    return ConversationRecord(
        date=datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        summary=data["summary"],
        homework=data.get("homework"),
        keywords=merged,
    )


def save_record(
    record: ConversationRecord, memory_dir: Path = DEFAULT_MEMORY_DIR
) -> Path:
    memory_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = memory_dir / f"{stamp}.json"
    counter = 1
    while path.exists():
        path = memory_dir / f"{stamp}_{counter}.json"
        counter += 1
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_recent_records(
    count: int = DEFAULT_LOAD_COUNT, memory_dir: Path = DEFAULT_MEMORY_DIR
) -> list[ConversationRecord]:
    if not memory_dir.is_dir():
        return []

    records: list[ConversationRecord] = []
    # 新しい順に走査し、壊れたファイルはスキップして count 件まで集める
    for path in sorted(memory_dir.glob("*.json"), reverse=True):
        if len(records) >= count:
            break
        try:
            raw = path.read_text(encoding="utf-8")
            records.append(ConversationRecord.model_validate_json(raw))
        except (ValidationError, OSError, UnicodeDecodeError):
            continue

    records.reverse()  # 古い順に戻す
    return records


def format_records(records: list[ConversationRecord]) -> str:
    if not records:
        return ""

    parts = ["## 過去の相談記録（古い順）"]
    for r in records:
        lines = [f"[{r.date}]", f"要点: {r.summary}"]
        if r.homework:
            lines.append(f"宿題（Don が次回聞きたいと言った内容）: {r.homework}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
