# Schedule Agent

Google Calendar と連携し、自然言語でイベントの追加・実行可否判定を行うエージェント。

## 機能

- 自然言語からイベント情報を抽出（案件名・日時・場所）
- Google Calendar から同日の既存予定を取得
- Claude API による時間重複・移動時間チェック
- 問題がなければ自動でカレンダーに登録

## 使い方

依存関係のインストール後、プロジェクトルートから以下を実行：

```bash
poetry run python -m app.agents.scheduling.schedule_agent
```

実行すると入力プロンプトが表示されるので、自然言語でイベントを入力する。

```
Enter your event details: 明日の14時から田中さんとミーティング1時間
```

## セットアップ

### 1. 依存関係のインストール

```bash
poetry install
```

### 2. 必要な環境変数

プロジェクトルート（`pyproject.toml` と同じディレクトリ）に `.env` ファイルを作成し、以下を設定：

```
ANTHROPIC_API_KEY=your_api_key
```

または、環境変数として直接 export しても動作する：

```bash
export ANTHROPIC_API_KEY=your_api_key
```

> **Note:** `load_dotenv()` はカレントディレクトリの `.env` を読み込むため、**プロジェクトルートから実行**してください。

### Google Calendar API 認証

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Google Calendar API を有効化
3. OAuth 2.0 クライアントID（デスクトップアプリ）を作成
4. `credentials.json` をダウンロードし、以下に配置：
   ```
   ~/.config/personal-agent-os/credentials.json
   ```
5. 初回実行時にブラウザで認証が走り、`token.pickle` が自動生成される

## 処理フロー

```
ユーザー入力
  → Claude API で自然言語をパース（JSON抽出）
  → Google Calendar から同日の予定を取得
  → Claude API で重複・移動時間を判定
  → Accept → カレンダーに登録
  → Reject → スキップ（登録しない）
```

## 依存関係

- `anthropic` — LLM による自然言語解析・実行可否判定
- `google-api-python-client` — Google Calendar API
- `google-auth-oauthlib` — OAuth 2.0 認証

## 現在の制限

- イベントの**削除には未対応**
- Accept/Reject はテキスト判定のため、ユーザーが確認・キャンセルする手段がない
- 代替案の提示はテキストのみ（構造化されていない）
