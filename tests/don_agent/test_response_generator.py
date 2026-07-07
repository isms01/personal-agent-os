import json
from unittest.mock import MagicMock

from anthropic.types import TextBlock

from app.agents.don_agent import (
    _parse_principle_ids,
    generate_response,
    preprocess_input,
    select_practical_principles,
    select_structural_principles,
)
from app.core.context_classifier import InputContext, Topic
from app.core.don_principles import ALL_PRINCIPLES

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _make_client(response_text: str) -> MagicMock:
    block = MagicMock(spec=TextBlock)
    block.text = response_text
    mock_response = MagicMock()
    mock_response.content = [block]
    client = MagicMock()
    client.messages.create.return_value = mock_response
    return client


def _make_context(
    submodes: list[str] | None = None,
    emotional_temperature: str = "warm",
    summary: str = "テスト用の要約",
) -> InputContext:
    submodes = submodes or ["venting"]
    topics = [
        Topic(content=f"topic_{i}", submode=s, weight=1.0 / len(submodes))
        for i, s in enumerate(submodes)
    ]
    return InputContext(
        topics=topics,
        mode_override_occurred=False,
        original_mode=None,
        emotional_temperature=emotional_temperature,
        summary=summary,
        search_keywords=["テスト"],
    )


# --------------------------------------------------------------------------
# preprocess_input
# --------------------------------------------------------------------------


def test_preprocess_strips_whitespace() -> None:
    assert preprocess_input("  hello  ") == "hello"
    assert preprocess_input("\n\ntext\n\n") == "text"


def test_preprocess_compresses_blank_lines() -> None:
    text = "line1\n\n\n\nline2"
    result = preprocess_input(text)
    assert result == "line1\n\nline2"


def test_preprocess_keeps_double_newline() -> None:
    text = "line1\n\nline2"
    assert preprocess_input(text) == "line1\n\nline2"


# --------------------------------------------------------------------------
# _parse_principle_ids
# --------------------------------------------------------------------------


def test_parse_principle_ids_plain_json() -> None:
    raw = '{"selected_ids": ["S1", "S3"], "reason": "理由"}'
    ids = _parse_principle_ids(raw, set(ALL_PRINCIPLES.keys()))
    assert ids == ["S1", "S3"]


def test_parse_principle_ids_filters_invalid() -> None:
    raw = '{"selected_ids": ["S1", "INVALID"], "reason": "理由"}'
    ids = _parse_principle_ids(raw, set(ALL_PRINCIPLES.keys()))
    assert ids == ["S1"]


# --------------------------------------------------------------------------
# select_structural_principles
# --------------------------------------------------------------------------


def test_select_structural_principles_returns_principles() -> None:
    resp = json.dumps({"selected_ids": ["S1", "S2"], "reason": "test"})
    client = _make_client(resp)
    context = _make_context(["venting"])

    result = select_structural_principles(client, "上司にひどいことを言われた", context)

    assert len(result) == 2
    assert all(p.id in ALL_PRINCIPLES for p in result)
    assert result[0].id == "S1"
    assert result[1].id == "S2"


def test_select_structural_principles_handles_invalid_ids() -> None:
    resp = json.dumps({"selected_ids": ["S9", "S1"], "reason": "test"})
    client = _make_client(resp)
    context = _make_context()

    result = select_structural_principles(client, "テスト入力", context)

    assert len(result) == 1
    assert result[0].id == "S1"


# --------------------------------------------------------------------------
# select_practical_principles
# --------------------------------------------------------------------------


def test_select_practical_principles_returns_empty_without_structural() -> None:
    client = _make_client('{"selected_ids": ["P1"]}')
    context = _make_context()

    result = select_practical_principles(client, "テスト", context, [])

    assert result == []
    client.messages.create.assert_not_called()


def test_select_practical_principles_uses_linkage_map() -> None:
    resp = json.dumps({"selected_ids": ["P1"], "reason": "test"})
    client = _make_client(resp)
    context = _make_context()
    structural = [ALL_PRINCIPLES["S1"]]

    result = select_practical_principles(client, "テスト", context, structural)

    assert len(result) == 1
    assert result[0].id == "P1"
    # S1 の候補にない原則は返ってこない
    returned_ids = {p.id for p in result}
    from app.core.don_principles import PRINCIPLE_LINKAGE_MAP

    s1_candidates = set(PRINCIPLE_LINKAGE_MAP["S1"])
    assert returned_ids.issubset(s1_candidates)


# --------------------------------------------------------------------------
# generate_response
# --------------------------------------------------------------------------


def test_generate_response_returns_string() -> None:
    client = _make_client("これが Don の応答です。")
    context = _make_context(["venting"])
    structural = [ALL_PRINCIPLES["S1"]]
    practical = [ALL_PRINCIPLES["P1"]]
    main_topic = context.topics[0]

    result = generate_response(
        client,
        "上司に怒られた",
        context,
        structural,
        practical,
        main_topic,
        [],
    )

    assert isinstance(result, str)
    assert result == "これが Don の応答です。"
    client.messages.create.assert_called_once()


def test_generate_response_calls_with_system_prompt() -> None:
    client = _make_client("応答テキスト")
    context = _make_context(["decision"])

    generate_response(client, "転職すべきか", context, [], [], context.topics[0], [])

    call_kwargs = client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert "Don Agent" in call_kwargs["system"]


def test_generate_response_with_pending_topics() -> None:
    client = _make_client("メイントピックへの応答")
    context = _make_context(["venting"])
    main_topic = context.topics[0]

    generate_response(
        client,
        "複数の悩みがある",
        context,
        [],
        [],
        main_topic,
        ["持ち越しトピックA", "持ち越しトピックB"],
    )

    call_kwargs = client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "持ち越しトピックA" in user_content


def test_generate_response_includes_past_records() -> None:
    client = _make_client("久しぶりだな。上司の件はどうなった。")
    context = _make_context(["venting"])
    past_text = "## 過去の相談記録（古い順）\n要点: 上司との衝突\n宿題: 面談の結果"

    generate_response(
        client,
        "上司の件、報告があります",
        context,
        [],
        [],
        context.topics[0],
        [],
        past_records_text=past_text,
    )

    call_kwargs = client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "過去の相談記録" in user_content
    assert "面談の結果" in user_content


def test_generate_response_omits_past_section_when_empty() -> None:
    client = _make_client("応答")
    context = _make_context(["venting"])

    generate_response(client, "初回の相談", context, [], [], context.topics[0], [])

    call_kwargs = client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "過去の相談記録" not in user_content


def test_generate_response_out_of_scope() -> None:
    client = _make_client("領分外の相談ですね。")
    context = _make_context(["out_of_scope_technical"], emotional_temperature="cold")

    result = generate_response(
        client, "Pythonの書き方教えて", context, [], [], None, []
    )

    assert isinstance(result, str)
    call_kwargs = client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "対象外トピック" in user_content
