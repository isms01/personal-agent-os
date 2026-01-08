"""
Google Calendar API クライアント
"""

import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Calendar API のスコープ
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    """Google Calendar API クライアント"""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        初期化

        Args:
            credentials_path: credentials.json のパス（省略時は ~/.config/personal-agent-os/credentials.json）
        """
        # 認証情報のパス
        if credentials_path is None:
            config_dir = Path.home() / ".config" / "personal-agent-os"
            config_dir.mkdir(parents=True, exist_ok=True)
            credentials_path = str(config_dir / "credentials.json")

        self.credentials_path = credentials_path
        self.token_path = str(Path(credentials_path).parent / "token.pickle")

        # 認証
        self.service = self._authenticate()

    def _authenticate(self):
        """Google Calendar API の認証"""
        creds = None

        # トークンファイルがあれば読み込む
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        # 認証情報が無効または存在しない場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    # トークンをリフレッシュ
                    creds.refresh(Request())
                except Exception:
                    # リフレッシュ失敗時はトークンを削除して再認証
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)
                    creds = None

            if not creds:
                # 新規認証
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"認証情報ファイルが見つかりません: {self.credentials_path}\n"
                        "Google Cloud Console でOAuth 2.0クライアントIDを作成し、\n"
                        "credentials.json としてダウンロードしてください。"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # トークンを保存
            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        return build("calendar", "v3", credentials=creds)

    def get_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10,
        calendar_id: str = "primary",
    ) -> list:
        """
        イベントを取得

        Args:
            time_min: 開始時刻（この時刻以降のイベント）
            time_max: 終了時刻（この時刻以前のイベント）
            max_results: 最大取得件数
            calendar_id: カレンダーID（デフォルトはprimary）

        Returns:
            イベントのリスト
        """
        # 時刻をRFC3339形式に変換
        params = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if time_min:
            params["timeMin"] = time_min.isoformat() + "Z"
        if time_max:
            params["timeMax"] = time_max.isoformat() + "Z"

        events_result = self.service.events().list(**params).execute()
        events = events_result.get("items", [])

        return events

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        description: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> dict:
        """
        イベントを作成

        Args:
            summary: イベント名
            start_time: 開始時刻
            end_time: 終了時刻
            location: 場所
            description: 説明
            calendar_id: カレンダーID（デフォルトはprimary）

        Returns:
            作成されたイベント
        """
        event = {
            "summary": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "Asia/Tokyo",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "Asia/Tokyo",
            },
        }

        if location:
            event["location"] = location

        if description:
            event["description"] = description

        created_event = (
            self.service.events().insert(calendarId=calendar_id, body=event).execute()
        )

        return created_event
