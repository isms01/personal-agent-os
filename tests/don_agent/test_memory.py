import json
from pathlib import Path
from unittest.mock import MagicMock

from anthropic.types import TextBlock

from app.core.context_classifier import InputContext, Topic
from app.core.don_memory import (
    DEFAULT_MEMORY_DIR,
    ConversationRecord,
    format_records,
    load_recent_records,
    save_record,
    summarize_conversation,
)

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


def _make_context(search_keywords: list[str] | None = None) -> InputContext:
    return InputContext(
        topics=[Topic(content="転職の悩み", submode="decision", weight=1.0)],
        mode_override_occurred=False,
        original_mode=None,
        emotional_temperature="warm",
        summary="転職について迷っている",
        search_keywords=search_keywords if search_keywords is not None else ["転職"],
    )


def _make_record(
    summary: str = "要約", homework: str | None = None
) -> ConversationRecord:
    return ConversationRecord(
        date="2026-07-06 21:30",
        summary=summary,
        homework=homework,
        keywords=["転職"],
    )


# --------------------------------------------------------------------------
# summarize_conversation
# --------------------------------------------------------------------------


def test_summarize_returns_record() -> None:
    resp = json.dumps(
        {
            "summary": "転職の相談。Don は焦らず条件を整理するよう助言した。",
            "homework": "上司との面談の結果を聞かせてほしい",
            "keywords": ["転職", "上司"],
        },
        ensure_ascii=False,
    )
    client = _make_client(resp)
    context = _make_context(search_keywords=["転職", "面談"])

    record = summarize_conversation(client, "転職すべきか", "Don の応答", context)

    assert record.summary == "転職の相談。Don は焦らず条件を整理するよう助言した。"
    assert record.homework == "上司との面談の結果を聞かせてほしい"
    # LLM と分類器のキーワードが順序を保って重複排除される
    assert record.keywords == ["転職", "上司", "面談"]
    assert record.date  # 日時が付与される


def test_summarize_handles_fenced_json() -> None:
    inner = json.dumps(
        {"summary": "要約文", "homework": None, "keywords": []},
        ensure_ascii=False,
    )
    client = _make_client(f"```json\n{inner}\n```")
    context = _make_context(search_keywords=[])

    record = summarize_conversation(client, "入力", "応答", context)

    assert record.summary == "要約文"
    assert record.homework is None
    assert record.keywords == []


def test_summarize_passes_conversation_to_llm() -> None:
    resp = json.dumps({"summary": "s", "homework": None, "keywords": []})
    client = _make_client(resp)
    context = _make_context()

    summarize_conversation(client, "ユーザー入力テキスト", "Don 応答テキスト", context)

    call_kwargs = client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "ユーザー入力テキスト" in user_content
    assert "Don 応答テキスト" in user_content


# --------------------------------------------------------------------------
# save_record / load_recent_records
# --------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    record = _make_record(summary="往復テスト", homework="次回の報告")

    path = save_record(record, memory_dir=tmp_path)

    assert path.exists()
    loaded = load_recent_records(count=10, memory_dir=tmp_path)
    assert loaded == [record]


def test_save_avoids_filename_collision(tmp_path: Path) -> None:
    path1 = save_record(_make_record(summary="1 回目"), memory_dir=tmp_path)
    path2 = save_record(_make_record(summary="2 回目"), memory_dir=tmp_path)

    assert path1 != path2
    assert path1.exists()
    assert path2.exists()


def test_load_returns_latest_n_in_chronological_order(tmp_path: Path) -> None:
    for i in range(12):
        record = _make_record(summary=f"会話 {i}")
        (tmp_path / f"20260101_{i:02d}0000.json").write_text(
            record.model_dump_json(), encoding="utf-8"
        )

    loaded = load_recent_records(count=10, memory_dir=tmp_path)

    assert len(loaded) == 10
    assert loaded[0].summary == "会話 2"  # 古い 2 件は落ちる
    assert loaded[-1].summary == "会話 11"  # 最新が末尾（古い順）


def test_load_skips_corrupt_files_and_backfills(tmp_path: Path) -> None:
    for i in range(3):
        record = _make_record(summary=f"正常 {i}")
        (tmp_path / f"20260101_{i:02d}0000.json").write_text(
            record.model_dump_json(), encoding="utf-8"
        )
    # 最新のファイルを壊す
    (tmp_path / "20260101_990000.json").write_text("{ broken", encoding="utf-8")

    loaded = load_recent_records(count=3, memory_dir=tmp_path)

    assert [r.summary for r in loaded] == ["正常 0", "正常 1", "正常 2"]


def test_load_missing_dir_returns_empty(tmp_path: Path) -> None:
    loaded = load_recent_records(count=10, memory_dir=tmp_path / "not_exist")

    assert loaded == []


# --------------------------------------------------------------------------
# DEFAULT_MEMORY_DIR
# --------------------------------------------------------------------------


def test_default_memory_dir_is_anchored_to_project_root() -> None:
    # cwd に依存せず、常にプロジェクトルート配下の logs/don_memory を指す
    project_root = Path(__file__).resolve().parent.parent.parent
    assert DEFAULT_MEMORY_DIR.is_absolute()
    assert project_root / "logs" / "don_memory" == DEFAULT_MEMORY_DIR


# --------------------------------------------------------------------------
# format_records
# --------------------------------------------------------------------------


def test_format_records_includes_fields() -> None:
    records = [
        _make_record(summary="最初の相談", homework="宿題の内容"),
        _make_record(summary="次の相談", homework=None),
    ]

    text = format_records(records)

    assert "過去の相談記録" in text
    assert "最初の相談" in text
    assert "宿題の内容" in text
    assert "次の相談" in text


def test_format_records_empty_returns_empty_string() -> None:
    assert format_records([]) == ""
