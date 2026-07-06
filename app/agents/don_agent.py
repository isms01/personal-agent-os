"""
Don Agent — 人生領域の相談を担う Agent。
Vito Corleone の判断構造を内面化し、観察と具体的な助言を提供する。
"""

import argparse
import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

from app.core.context_classifier import InputContext, Topic, classify_context
from app.core.don_memory import (
    format_records,
    load_recent_records,
    save_record,
    summarize_conversation,
)
from app.core.don_principles import (
    ALL_PRINCIPLES,
    PRINCIPLE_LINKAGE_MAP,
    STRUCTURAL_PRINCIPLES,
    Principle,
)

load_dotenv()

MODEL = "claude-sonnet-5"
MAX_TOKENS_RESPONSE = 4000

_DIFFICULT_SUBMODES = {"venting", "lost", "conflict", "decision"}

# --------------------------------------------------------------------------
# Step 1: 入力前処理
# --------------------------------------------------------------------------


def preprocess_input(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# --------------------------------------------------------------------------
# Step 3: 原則発火（2 段階）
# --------------------------------------------------------------------------

_STAGE1_PREFIX = """\
ユーザーの相談内容と文脈を読み、以下の構造原則から最大 2 個を選んでください。
発火条件に最も当てはまるものを選び、JSON のみを返してください。

出力形式:
{"selected_ids": ["S1"], "reason": "選択理由の一文"}
"""

_STAGE2_PREFIX = """\
選ばれた構造原則を実現するための実践原則を候補から最大 2 個選んでください。
発火条件に最も当てはまるものを選び、JSON のみを返してください。

出力形式:
{"selected_ids": ["P1"], "reason": "選択理由の一文"}
"""


def _format_principles(principles: list[Principle]) -> str:
    parts = []
    for p in principles:
        signals = "\n".join(f"  - {s}" for s in p.activation_signals)
        parts.append(f"[{p.id}] {p.name}\n発火条件:\n{signals}")
    return "\n\n".join(parts)


def _parse_principle_ids(raw: str, allowed_ids: set[str]) -> list[str]:
    try:
        if raw.startswith("```"):
            raw = raw[raw.find("{") : raw.rfind("}") + 1]
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return [pid for pid in data.get("selected_ids", []) if pid in allowed_ids]


def select_structural_principles(
    client: Anthropic, user_input: str, context: InputContext
) -> list[Principle]:
    principles_text = _format_principles(STRUCTURAL_PRINCIPLES)
    prompt = (
        f"{_STAGE1_PREFIX}\n"
        f"ユーザー入力: {user_input}\n"
        f"文脈サマリー: {context.summary}\n"
        f"感情温度: {context.emotional_temperature}\n\n"
        f"## 構造原則\n{principles_text}"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        # JSON のみを返す呼び出し。思考トークンで出力が切れないよう思考オフ
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )

    block = response.content[0]
    raw = getattr(block, "text", None)
    if not isinstance(raw, str):
        return []

    structural_ids = {p.id for p in STRUCTURAL_PRINCIPLES}
    parsed = _parse_principle_ids(raw.strip(), structural_ids)
    return [ALL_PRINCIPLES[pid] for pid in parsed]


def select_practical_principles(
    client: Anthropic,
    user_input: str,
    context: InputContext,
    structural: list[Principle],
) -> list[Principle]:
    if not structural:
        return []

    candidate_ids: set[str] = set()
    for s in structural:
        candidate_ids.update(PRINCIPLE_LINKAGE_MAP.get(s.id, []))

    candidates = [ALL_PRINCIPLES[pid] for pid in candidate_ids if pid in ALL_PRINCIPLES]
    if not candidates:
        return []

    structural_names = "・".join(f"{s.id}({s.name})" for s in structural)
    principles_text = _format_principles(candidates)
    prompt = (
        f"{_STAGE2_PREFIX}\n"
        f"選ばれた構造原則: {structural_names}\n"
        f"ユーザー入力: {user_input}\n"
        f"文脈サマリー: {context.summary}\n\n"
        f"## 候補となる実践原則\n{principles_text}"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        # JSON のみを返す呼び出し。思考トークンで出力が切れないよう思考オフ
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )

    block = response.content[0]
    raw = getattr(block, "text", None)
    if not isinstance(raw, str):
        return []

    parsed = _parse_principle_ids(raw.strip(), candidate_ids)
    return [ALL_PRINCIPLES[pid] for pid in parsed]


# --------------------------------------------------------------------------
# Step 4: 応答生成
# --------------------------------------------------------------------------

_DON_SYSTEM_PROMPT = """\
あなたは Don Agent です。Vito Corleone の判断構造を内面化した、人生の相談相手です。

## 役割と性格
長い年月をかけて人間というものを観てきた老人だ。声を荒げる必要はない。言葉は少なく、しかし一言ひとことに重みがある。
急かさない。怒鳴らない。ただ、深いところから静かに語りかける。
あなたはドンだ。家族を守り、敬意を重んじ、力よりも知恵で生きてきた人間だ。

## 語り口の指針
- 文は短く、間を置くように書く。長い文より、重い一文を選ぶ。
- 断定より観察。「〜というものだ」「〜ではないか」「〜ものだよ」を自然に使う。
- 老人が孫に語るような温かさと、経験から来る静かな鋭さを両立させる。
- 説教はしない。ただ、見えていないものを静かに指さし、具体的な選択肢を能動的に示す。
- 最後の判断はあなた（ユーザー）に委ねる。押しつけない。
- ユーザーを「あなた」と呼ぶ。

## Vito 原則（10 原則）
構造原則:
- S1 敬意と信用の分離: 敬意と信用は独立した変数として運用する
- S2 ボトムラインの維持: 断絶も排除も第一候補としない
- S3 ほっとく哲学: 他者を変えようとせず、強制も支配もしない

実践原則:
- P1 感情の完全な制御: 感情に行動を支配されず、一呼吸置いて判断する
- P2 拠点の死守: 家族・パートナーという精神的拠点を最優先で守る
- P3 恩義のネットワーク: 見返りを急がず、借りと貸しの関係を重視する
- P4 普遍的な敬意: 相手の立場に関わらず礼儀と敬意を持って接する
- P5 寡黙と決断の重さ: 発言を厳選し、一度下した決断にブレがない
- X  過去を蒸し返さない: 今と明日に集中する
- Z  自分の意思は明示する: 何を欲するかを曖昧にせず明示する

## 禁則事項
- 人格を傷つける表現（「お前は弱い」「そんなことだから」など）
- 関係の切断・排除を第一候補とする助言
- 早すぎる解決策の提示（まず話を受け取る）
- 過剰なキャラ演出（ファミリー等の語彙の多用）
- 喜びの場での教訓化・警告調
- ジェンダー的表現
- Michael Corleone 的論理（人を手段化する）

## 対象外の応答（2 ブロック）
1. 領分外の宣言（1 文）
2. 適切な相談先の提示（1 文）

## 喜び共有（celebration）の応答（最大 3 ブロック）
1. 受容（1〜2 文）
2. ドン自身の感情（1 文）
3. 簡潔なアドバイス（1〜2 文、任意、前向きな方向のみ）

## 困難時の応答（4 ブロック）
1. 受信の証（複数文）: 話を受け取った証拠。早すぎる助言を避ける
2. 状況の言語化（複数文）: 本人が見えていない構造を一つ指摘
3. 原則の観察（複数文）: 説教ではなく観察として置く
4. 具体的助言（複数文）: 選択肢として明日への方向性を示す

文数の目安: 困難 8〜12 文、celebration 3〜8 文、対象外 2〜3 文
応答は散文で。見出しや箇条書きは使わない。
"""


def generate_response(
    client: Anthropic,
    user_input: str,
    context: InputContext,
    structural_principles: list[Principle],
    practical_principles: list[Principle],
    main_difficult_topic: Topic | None,
    pending_topic_names: list[str],
    past_records_text: str = "",
) -> str:
    out_of_scope = [t for t in context.topics if t.submode.startswith("out_of_scope")]
    celebration = [t for t in context.topics if t.submode == "celebration"]

    topic_lines: list[str] = []
    if out_of_scope:
        names = "、".join(t.content for t in out_of_scope)
        topic_lines.append(f"対象外トピック: {names}")
    if celebration:
        names = "、".join(t.content for t in celebration)
        topic_lines.append(f"喜び共有トピック: {names}")
    if main_difficult_topic:
        topic_lines.append(
            "メイン困難トピック（4 ブロック構造で応答）: "
            + main_difficult_topic.content
        )
    if pending_topic_names:
        names = "、".join(pending_topic_names)
        topic_lines.append(
            f"持ち越しトピック（今回は触れず、最後に名指しして問い合わせる）: {names}"
        )

    fired_lines: list[str] = []
    for p in structural_principles + practical_principles:
        steps = "\n".join(f"  - {s}" for s in p.application_pattern)
        fired_lines.append(f"[{p.id}] {p.name}\n適用方法:\n{steps}")

    override_note = ""
    if context.mode_override_occurred:
        override_note = (
            f"\n（注: --mode={context.original_mode} が指定されたが内容から"
            "自動分類を優先した。応答の中で自然に言及すること）"
        )

    past_lines: list[str] = []
    if past_records_text:
        past_lines = [
            f"\n{past_records_text}",
            "（過去の記録は文脈理解に使う。宿題への答えが今回の入力に"
            "含まれていたら、覚えていたことが伝わるよう自然に言及する）",
        ]

    fired_section = fired_lines if fired_lines else ["（なし）"]
    user_prompt = "\n".join(
        [
            f"ユーザーの入力:\n{user_input}",
            f"\n文脈: 感情温度={context.emotional_temperature} / {context.summary}",
            *past_lines,
            "\n## トピック",
            *topic_lines,
            "\n## 発火した原則",
            *fired_section,
            override_note,
            "\n応答順序: 対象外（あれば最初）→ celebration → 困難（最後、重厚に）",
        ]
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_RESPONSE,
        # 応答の深みを優先し適応的思考を有効化（先頭に thinking ブロックが入る）
        thinking={"type": "adaptive"},
        system=_DON_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        raw = getattr(block, "text", None)
        if isinstance(raw, str):
            return raw.strip()

    raise ValueError("No text block in response")


# --------------------------------------------------------------------------
# メインループ
# --------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Don Agent")
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        help="venting / lost / conflict / decision / celebration",
    )
    args = parser.parse_args()

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print("どうしました。")
    print("（空行を 2 回続けると送信）")
    print()

    lines: list[str] = []
    previous_was_blank = False
    try:
        while True:
            line = input()
            if line == "":
                if previous_was_blank:
                    print()
                    print("入力を受け付けました。")
                    print("Don 実行中...")
                    break
                previous_was_blank = True
                continue

            if previous_was_blank:
                # Keep a single blank line when user is adding paragraph breaks.
                lines.append("")
                previous_was_blank = False
            lines.append(line)
    except EOFError:
        pass
    except KeyboardInterrupt:
        print()
        return

    user_input = preprocess_input("\n".join(lines))
    if not user_input:
        return

    # Step 2: 過去記録の読み込みと文脈分類
    past_records_text = format_records(load_recent_records())
    context = classify_context(
        user_input, mode_override=args.mode, past_records_text=past_records_text
    )

    # Step 3: 困難トピックの特定と原則発火
    difficult_topics = sorted(
        [t for t in context.topics if t.submode in _DIFFICULT_SUBMODES],
        key=lambda t: t.weight,
        reverse=True,
    )
    main_topic = difficult_topics[0] if difficult_topics else None
    pending_names = [t.content for t in difficult_topics[1:]]

    structural: list[Principle] = []
    practical: list[Principle] = []
    if main_topic:
        structural = select_structural_principles(client, user_input, context)
        practical = select_practical_principles(client, user_input, context, structural)

    # Step 4: 応答生成
    response_text = generate_response(
        client,
        user_input,
        context,
        structural,
        practical,
        main_topic,
        pending_names,
        past_records_text=past_records_text,
    )

    # Step 5: 出力
    print()
    print(response_text)
    print()

    # Step 6: 会話の記録（失敗しても会話体験は壊さない）
    try:
        record = summarize_conversation(client, user_input, response_text, context)
        save_record(record)
    except Exception:
        print("（今回の会話の記録に失敗した。次回は今日の話を覚えていない）")


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set")
        raise SystemExit(1)
    main()
