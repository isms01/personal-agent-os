import json
from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock

from app.core.context_classifier import InputContext, Topic, classify_context


def _make_mock_response(data: dict[str, object]) -> MagicMock:
    mock_content = MagicMock(spec=TextBlock)
    mock_content.text = json.dumps(data, ensure_ascii=False)
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


_VENTING_RESPONSE: dict[str, object] = {
    "topics": [
        {"content": "上司に理不尽に怒られた", "submode": "venting", "weight": 1.0}
    ],
    "mode_override_occurred": False,
    "original_mode": None,
    "emotional_temperature": "hot",
    "summary": "上司への不満を吐き出している",
    "search_keywords": ["上司", "職場"],
}

_MIXED_RESPONSE: dict[str, object] = {
    "topics": [
        {"content": "転職すべきか迷っている", "submode": "decision", "weight": 0.7},
        {"content": "先週褒められた", "submode": "celebration", "weight": 0.0},
    ],
    "mode_override_occurred": False,
    "original_mode": None,
    "emotional_temperature": "warm",
    "summary": "転職の決断と小さな喜びが混在",
    "search_keywords": ["転職"],
}

_OUT_OF_SCOPE_RESPONSE: dict[str, object] = {
    "topics": [
        {
            "content": "Python の型ヒントの書き方を教えて",
            "submode": "out_of_scope_technical",
            "weight": 0.0,
        }
    ],
    "mode_override_occurred": False,
    "original_mode": None,
    "emotional_temperature": "cold",
    "summary": "技術的な質問",
    "search_keywords": [],
}


@patch("app.core.context_classifier.Anthropic")
def test_classify_venting(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_VENTING_RESPONSE)

    result = classify_context("上司にひどいことを言われた。もう限界だ。")

    assert isinstance(result, InputContext)
    assert len(result.topics) == 1
    assert result.topics[0].submode == "venting"
    assert result.topics[0].weight == 1.0
    assert result.emotional_temperature == "hot"
    assert result.mode_override_occurred is False


@patch("app.core.context_classifier.Anthropic")
def test_classify_mixed_topics(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_MIXED_RESPONSE)

    input_text = "転職を考えている。先週は上司に褒められて少し嬉しかったけど。"
    result = classify_context(input_text)

    assert len(result.topics) == 2
    submodes = {t.submode for t in result.topics}
    assert "decision" in submodes
    assert "celebration" in submodes


@patch("app.core.context_classifier.Anthropic")
def test_classify_out_of_scope(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_OUT_OF_SCOPE_RESPONSE)

    result = classify_context("Python の型ヒントの書き方を教えて")

    assert result.topics[0].submode == "out_of_scope_technical"
    assert result.emotional_temperature == "cold"


@patch("app.core.context_classifier.Anthropic")
def test_mode_override_conflict(mock_anthropic_class: MagicMock) -> None:
    # mode=celebration を指定したが LLM は venting と判定
    # → 矛盾なので override_occurred=True
    response_data: dict[str, object] = {
        "topics": [{"content": "悔しい", "submode": "venting", "weight": 1.0}],
        "mode_override_occurred": False,
        "original_mode": None,
        "emotional_temperature": "hot",
        "summary": "感情の吐き出し",
        "search_keywords": [],
    }
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(response_data)

    result = classify_context("すごく悔しい", mode_override="celebration")

    assert result.mode_override_occurred is True
    assert result.original_mode == "celebration"


@patch("app.core.context_classifier.Anthropic")
def test_mode_override_with_overlap(mock_anthropic_class: MagicMock) -> None:
    # mode=venting を指定して LLM も venting → 矛盾なし
    response_data: dict[str, object] = {
        "topics": [{"content": "怒っている", "submode": "venting", "weight": 1.0}],
        "mode_override_occurred": False,
        "original_mode": None,
        "emotional_temperature": "hot",
        "summary": "怒りの発散",
        "search_keywords": [],
    }
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(response_data)

    result = classify_context("本当に腹が立つ", mode_override="venting")

    assert result.mode_override_occurred is False


@patch("app.core.context_classifier.Anthropic")
def test_search_keywords_included(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_VENTING_RESPONSE)

    result = classify_context("上司にひどいことを言われた")

    assert isinstance(result.search_keywords, list)
    assert "上司" in result.search_keywords


@patch("app.core.context_classifier.Anthropic")
def test_past_records_included_in_prompt(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_VENTING_RESPONSE)

    past_text = "## 過去の相談記録\n要点: 上司との衝突"
    classify_context("上司の件、報告したい", past_records_text=past_text)

    user_content = create.call_args.kwargs["messages"][0]["content"]
    assert "過去の相談記録" in user_content
    assert "上司との衝突" in user_content


@patch("app.core.context_classifier.Anthropic")
def test_past_records_omitted_when_empty(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_VENTING_RESPONSE)

    classify_context("つらい", past_records_text="")

    user_content = create.call_args.kwargs["messages"][0]["content"]
    assert "過去の相談記録" not in user_content


@patch("app.core.context_classifier.Anthropic")
def test_topic_model_fields(mock_anthropic_class: MagicMock) -> None:
    create = mock_anthropic_class.return_value.messages.create
    create.return_value = _make_mock_response(_VENTING_RESPONSE)

    result = classify_context("つらい")

    topic = result.topics[0]
    assert isinstance(topic, Topic)
    assert topic.content
    assert topic.submode
    assert isinstance(topic.weight, float)
