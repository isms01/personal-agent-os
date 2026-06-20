import json
import os

from anthropic import Anthropic
from anthropic.types import TextBlock
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

MODEL = "claude-sonnet-4-6"

VALID_SUBMODES = {
    "venting",
    "lost",
    "conflict",
    "decision",
    "celebration",
    "out_of_scope_technical",
    "out_of_scope_casual",
    "out_of_scope_other",
}


class Topic(BaseModel):
    content: str
    submode: str
    weight: float


class InputContext(BaseModel):
    topics: list[Topic]
    mode_override_occurred: bool
    original_mode: str | None
    emotional_temperature: str  # cold / warm / hot
    summary: str
    search_keywords: list[str]


_CLASSIFY_SYSTEM_PROMPT = """\
あなたは Don Agent の文脈分類エンジンです。
ユーザーの入力を分析し、JSON のみを返してください。

## サブモードの定義
- venting: 感情を吐き出したい、聞いてほしい、発散が主目的
- lost: 方向性が分からない、選択肢が見えない、迷っている
- conflict: 特定の相手や状況との衝突、対人関係の摩擦
- decision: 具体的な決断を迫られている、選択肢は見えているが選べない
- celebration: 喜びや成功の共有
- out_of_scope_technical: コードレビュー、事実調査、ファイル操作など
- out_of_scope_casual: 雑談・挨拶
- out_of_scope_other: agent メタ質問、振る舞い変更指示、危険な内容、意味不明な入力など

## トピック抽出の基準
- 入力で触れられたトピックはすべて抽出する（閾値による足切りはしない）
- weight は困難時サブモード（venting/lost/conflict/decision）間の
  相対的な比重（合計は 1.0）
- celebration と out_of_scope 系の weight は 0.0 とする

## emotional_temperature の定義
- cold: 淡々としている、感情が抑制されている
- warm: 感情が穏やかに表れている
- hot: 怒り・悲しみ・興奮など強い感情が表れている

## 出力 JSON の形式（他のテキストは一切出力しない）
{
  "topics": [
    {"content": "トピックの内容", "submode": "サブモード名", "weight": 0.0}
  ],
  "mode_override_occurred": false,
  "original_mode": null,
  "emotional_temperature": "cold|warm|hot",
  "summary": "入力の要約（1〜2 文）",
  "search_keywords": ["過去相談の検索に使うキーワード（固有名詞・案件名など）"]
}
"""


def classify_context(user_input: str, mode_override: str | None = None) -> InputContext:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_content = f"ユーザー入力:\n{user_input}"
    if mode_override:
        user_content += f"\n\nmode 指定: {mode_override}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_CLASSIFY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    block = response.content[0]
    if not isinstance(block, TextBlock):
        raise ValueError(f"Unexpected response block type: {type(block)}")
    raw = block.text.strip()

    # ```json ``` ブロックへの対応
    if raw.startswith("```"):
        start = raw.find("{")
        end = raw.rfind("}") + 1
        raw = raw[start:end]

    data = json.loads(raw)

    # mode_override との矛盾チェック:
    # topics に mode_override のサブモードが一切含まれない場合に上書き
    if mode_override and mode_override in VALID_SUBMODES:
        topic_submodes = {t["submode"] for t in data["topics"]}
        difficult_submodes = {"venting", "lost", "conflict", "decision"}
        celebration = {"celebration"}
        out_of_scope = {
            "out_of_scope_technical",
            "out_of_scope_casual",
            "out_of_scope_other",
        }

        override_group = (
            difficult_submodes
            if mode_override in difficult_submodes
            else celebration
            if mode_override in celebration
            else out_of_scope
        )
        has_overlap = bool(topic_submodes & override_group)
        if not has_overlap:
            data["mode_override_occurred"] = True
            data["original_mode"] = mode_override

    return InputContext(**data)
