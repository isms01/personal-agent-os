"""
Google Calendarと連携したスケジュール実現性チェッカー
- 新しい予定の入力
- Google Calendarから既存予定を取得
- スケジュール重複チェック
- 移動時間を考慮した実現可能性チェック
"""

import os
from datetime import datetime, timedelta

from anthropic import Anthropic
from dotenv import load_dotenv

from app.tools.calendar import GoogleCalendarClient

# .envファイルを読み込む
load_dotenv()


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """日付と時刻を結合してdatetimeオブジェクトを作成"""
    # 例: "2026-01-05" + "14:00" -> datetime(2026, 1, 5, 14, 0)
    dt_str = f"{date_str} {time_str}"
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


def check_with_claude(new_event: dict, calendar_events: list) -> None:
    """
    Claude APIを使って新しい予定が実現可能かチェック

    Args:
        new_event: 新しい予定の情報
        calendar_events: Google Calendarから取得した既存予定のリスト
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # 既存予定を整形
    existing_schedules = ""
    if calendar_events:
        for event in calendar_events:
            existing_schedules += f"- {event['summary']} ({event['start']} - {event['end']}) @ {event.get('location', '場所未指定')}\n"
    else:
        existing_schedules = "（この日の予定はありません）"

    prompt = f"""あなたはスケジュール管理のエキスパートです。
以下の新しい予定を追加できるか判定してください。

【追加したい予定】
- 案件名: {new_event['summary']}
- 日時: {new_event['start']} - {new_event['end']}
- 場所: {new_event['location']}

【既存の予定（Google Calendar）】
{existing_schedules}

以下の2点を確認してください：
1. 時間の重複チェック（新しい予定が既存予定と重複していないか）
2. 移動時間チェック（前後の予定との間に十分な移動時間があるか）

以下の形式で回答してください：

1. 重複チェック結果
2. 移動時間チェック結果（前の予定から/次の予定への移動）
3. 総合判定（Accept または Reject）
4. 判定理由

判定結果は必ず「Accept」または「Reject」のいずれかを含めてください。
"""

    print("\n🤖 Claude が分析中...\n")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    print("=" * 60)
    print(response_text)
    print("=" * 60)

    # 判定結果を返す
    return "Accept" in response_text or "accept" in response_text


def main():
    """メイン処理"""
    user_input = input("予定を入力: ").strip()

    if not user_input:
        print("✗ 予定を入力してください")
        return

    print("\nClaude が予定を解析中...\n")

    # Claude APIで自然言語から情報を抽出
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    parse_prompt = f"""以下の自然言語から予定情報を抽出してください。

入力: {user_input}

以下のJSON形式で回答してください（JSON以外の説明は不要）：
{{
    "summary": "案件名",
    "date": "YYYY-MM-DD",
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "location": "場所"
}}

- 「明日」「今日」などの相対表現は具体的な日付に変換してください（今日は{datetime.now().strftime('%Y-%m-%d')}です）
- 終了時刻が指定されていない場合は、開始時刻から1時間後にしてください
- 場所が指定されていない場合は "" としてください
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": parse_prompt}],
    )

    # JSONを抽出
    import json

    response_text = message.content[0].text
    try:
        # ```json ``` で囲まれている場合を考慮
        if "```json" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
        else:
            json_str = response_text

        event_data = json.loads(json_str)

        print(f"✓ 解析完了:")
        print(f"  案件名: {event_data['summary']}")
        print(
            f"  日時: {event_data['date']} {event_data['start_time']}-{event_data['end_time']}"
        )
        print(f"  場所: {event_data['location']}\n")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"✗ 予定の解析に失敗しました: {e}")
        print(f"Claude の応答: {response_text}")
        return

    # datetimeオブジェクトに変換
    try:
        start_dt = parse_datetime(event_data["date"], event_data["start_time"])
        end_dt = parse_datetime(event_data["date"], event_data["end_time"])
    except ValueError as e:
        print(f"✗ 日付・時刻の形式が正しくありません: {e}")
        return

    new_event = {
        "summary": event_data["summary"],
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M"),
        "location": event_data["location"],
    }

    print("📅 Google Calendarから予定を取得中...\n")

    # Google Calendarから同じ日の予定を取得
    try:
        calendar = GoogleCalendarClient()

        # その日の0時から23:59までの予定を取得
        day_start = start_dt.replace(hour=0, minute=0, second=0)
        day_end = start_dt.replace(hour=23, minute=59, second=59)

        events = calendar.get_events(
            time_min=day_start, time_max=day_end, max_results=50
        )

        # イベントを整形
        calendar_events = []
        for event in events:
            calendar_events.append(
                {
                    "summary": event.get("summary", "無題"),
                    "start": event["start"].get("dateTime", event["start"].get("date")),
                    "end": event["end"].get("dateTime", event["end"].get("date")),
                    "location": event.get("location", "場所未指定"),
                }
            )

        print(f"取得した予定数: {len(calendar_events)}件\n")

        # Claude APIで判定
        is_accepted = check_with_claude(new_event, calendar_events)

        # Acceptの場合はGoogle Calendarに登録
        if is_accepted:
            print("\n📝 Google Calendarに登録中...\n")

            created_event = calendar.create_event(
                summary=new_event["summary"],
                start_time=start_dt,
                end_time=end_dt,
                location=new_event["location"] if new_event["location"] else None,
            )

            event_link = created_event.get("htmlLink", "")
            print("=" * 60)
            print("✓ カレンダーに登録しました！")
            print(f"リンク: {event_link}")
            print("=" * 60)
        else:
            print("\n⚠️  カレンダーへの登録はスキップされました")

    except FileNotFoundError as e:
        print(f"✗ Google Calendar 認証エラー\n")
        print("=" * 60)
        print("Google Calendar APIのセットアップが必要です：")
        print()
        print("1. Google Cloud Console にアクセス")
        print("   https://console.cloud.google.com/")
        print()
        print("2. プロジェクトを作成または選択")
        print()
        print("3. Google Calendar API を有効化")
        print(
            "   https://console.cloud.google.com/apis/library/calendar-json.googleapis.com"
        )
        print()
        print("4. OAuth 2.0 クライアントIDを作成")
        print("   - 「認証情報」→「認証情報を作成」→「OAuth クライアントID」")
        print("   - アプリケーションの種類: デスクトップアプリ")
        print()
        print("5. credentials.json をダウンロード")
        print()
        print("6. 以下のパスに配置:")
        print("   ~/.config/personal-agent-os/credentials.json")
        print()
        print("=" * 60)
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # API キーチェック
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("✗ エラー: ANTHROPIC_API_KEY が設定されていません")
        print("  .env ファイルに ANTHROPIC_API_KEY=your_key を追加してください")
        exit(1)

    main()
