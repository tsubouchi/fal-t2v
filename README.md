# Fal.ai Text-to-Video Generator

Fal.aiのtext-to-video APIを使用したバッチ処理対応の動画生成Webアプリケーション。WebSocketを使用してリアルタイムに生成の進捗状況を表示します。

## 機能

- 単一プロンプトからの動画生成
- CSVファイルを使用したバッチ処理による複数動画の生成
- WebSocketによるリアルタイムな進捗状況の表示
- 生成された動画のダウンロード機能

## 必要条件

- Python 3.11以上
- Fal.ai APIキー

## インストール

```bash
# 依存パッケージのインストール
pip install flask flask-sock flask-sqlalchemy websockets gunicorn python-dotenv
```

## 環境変数の設定

`.env`ファイルを作成し、以下の環境変数を設定してください：

```env
FAL_API_KEY=your_fal_ai_api_key
SESSION_SECRET=your_session_secret
```

## 使用方法

1. サーバーの起動:
```bash
python main.py
```

2. ブラウザで `http://localhost:5000` にアクセス

3. 動画生成:
   - 単一生成: プロンプトを入力して生成開始
   - バッチ生成: プロンプトを記載したCSVファイルをアップロード

## API実装詳細

Fal.aiのtext-to-video APIは、WebSocketを使用して実装されています。

```python
# WebSocket接続設定
FAL_API_URL = "wss://fal.ai/models/fal-ai/wan/v2.1/1.3b/text-to-video/api"

# リクエストデータ形式
data = {
    "input": {
        "prompt": "動画の説明文",
        "negative_prompt": "blurry, low quality",
        "num_frames": 24,
        "style": "Realistic cinematic video. High quality, 8K resolution.",
        "duration": 5
    },
    "logs": True
}

# WebSocket接続とストリーミング処理
async with websockets.connect(FAL_API_URL, extra_headers=headers) as websocket:
    await websocket.send(json.dumps(data))

    while True:
        response = await websocket.recv()
        response_data = json.loads(response)

        # 進捗状況の更新
        if response_data["status"] == "IN_PROGRESS":
            # 進捗ログの処理
            logs = response_data.get("logs", [])
        elif response_data["status"] == "COMPLETED":
            # 完了時の処理
            video_url = response_data["data"]["url"]
            request_id = response_data["requestId"]
```

### レスポンスの形式

1. 進捗状況
```json
{
    "status": "IN_PROGRESS",
    "logs": [
        {"message": "Generating frames..."},
        {"message": "Processing video..."}
    ]
}
```

2. 完了時
```json
{
    "status": "COMPLETED",
    "data": {
        "url": "https://example.com/generated-video.mp4"
    },
    "requestId": "unique-request-id"
}
```

## エラーハンドリング

アプリケーションは以下のようなエラーを適切に処理します：

- WebSocket接続エラー
- APIレスポンスのパースエラー
- 生成処理の失敗
- バッチ処理時の個別エラー

## 注意事項

- APIキーは必ず環境変数として設定し、コード内にハードコードしないでください
- バッチ処理時はAPI制限を考慮して適切な遅延を設定してください
- WebSocket接続は自動的に再接続を試みます