"""
pytest フック: テスト実行結果を logs/test_results.log に追記する。
- 実行のたびにタイムスタンプ付きのセクションを追加する
- 失敗・エラー時はトレースバックも記録する
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

import pytest

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "test_results.log"

JST = timezone(timedelta(hours=9))


class _TestResult(TypedDict):
    nodeid: str
    when: str
    outcome: str
    longrepr: str | None
    duration: float


_results: list[_TestResult] = []


def pytest_sessionstart(session: pytest.Session) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    _results.clear()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    # setup / teardown の失敗もキャプチャ、通常の pass は call フェーズのみ
    is_relevant = report.when == "call" or (
        report.when in ("setup", "teardown") and report.failed
    )
    if is_relevant:
        _results.append(
            _TestResult(
                nodeid=report.nodeid,
                when=report.when,
                outcome=report.outcome,
                longrepr=str(report.longrepr) if report.longrepr else None,
                duration=report.duration,
            )
        )


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: int | pytest.ExitCode
) -> None:
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S %z")
    passed = sum(1 for r in _results if r["outcome"] == "passed")
    failed = sum(1 for r in _results if r["outcome"] in ("failed", "error"))
    total = len(_results)

    lines = [
        f"\n{'=' * 70}",
        f"実行日時: {now}",
        f"結果サマリー: {passed} passed, {failed} failed, {total} total",
        "=" * 70,
    ]

    for r in _results:
        status = r["outcome"].upper()
        lines.append(f"  [{status}] {r['nodeid']}  ({r['duration']:.3f}s)")
        if r["longrepr"]:
            for line in r["longrepr"].splitlines():
                lines.append(f"           {line}")

    lines.append("")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
