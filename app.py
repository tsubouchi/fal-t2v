import os
import logging
from flask import Flask, render_template, request, jsonify
import requests
import csv
import io
import time
import json
import websockets
import asyncio
from flask_sock import Sock

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
sock = Sock(app)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key")

# Fal.ai API設定
FAL_API_KEY = os.environ.get("FAL_API_KEY")
FAL_API_URL = "wss://fal.ai/models/fal-ai/wan/v2.1/1.3b/text-to-video/api"

async def generate_video_with_progress(prompt):
    """Fal.ai APIを使用して動画を生成し、進行状況を返す"""
    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "input": {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality",
            "num_frames": 24,
            "style": "Realistic cinematic video. High quality, 8K resolution.",
            "duration": 5
        },
        "logs": True
    }

    try:
        async with websockets.connect(FAL_API_URL, extra_headers=headers) as websocket:
            await websocket.send(json.dumps(data))
            logger.debug(f"Request sent to Fal.ai API:")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Data: {json.dumps(data, indent=2)}")

            while True:
                try:
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    logger.debug(f"Received response: {json.dumps(response_data, indent=2)}")

                    if "status" in response_data:
                        if response_data["status"] == "IN_PROGRESS":
                            yield {
                                "status": "progress",
                                "logs": response_data.get("logs", [])
                            }
                        elif response_data["status"] == "COMPLETED":
                            if "data" in response_data and "url" in response_data["data"]:
                                yield {
                                    "status": "completed",
                                    "video_url": response_data["data"]["url"],
                                    "request_id": response_data.get("requestId")
                                }
                                break
                            else:
                                raise ValueError("Completed response missing video URL")
                        elif response_data["status"] == "FAILED":
                            error_message = response_data.get("error", "Unknown error occurred")
                            logger.error(f"API request failed: {error_message}")
                            yield {
                                "status": "error",
                                "error": error_message
                            }
                            break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse API response: {e}")
                    yield {
                        "status": "error",
                        "error": "Invalid response format from API"
                    }
                    break

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed unexpectedly: {e}")
        yield {
            "status": "error",
            "error": "WebSocket connection closed"
        }
    except Exception as e:
        logger.error(f"Unexpected error during video generation: {str(e)}")
        yield {
            "status": "error",
            "error": f"Error generating video: {str(e)}"
        }

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/generate-ws')
async def generate_ws(ws):
    """WebSocket endpoint for video generation"""
    while True:
        try:
            data = await ws.receive()
            request_data = json.loads(data)
            prompt = request_data.get('prompt')

            if not prompt:
                await ws.send(json.dumps({
                    "status": "error",
                    "error": "プロンプトを入力してください"
                }))
                continue

            async for update in generate_video_with_progress(prompt):
                await ws.send(json.dumps(update))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
            await ws.send(json.dumps({
                "status": "error",
                "error": "無効なリクエスト形式です"
            }))
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            await ws.send(json.dumps({
                "status": "error",
                "error": "サーバーエラーが発生しました"
            }))

@app.route('/batch', methods=['POST'])
async def batch_generate():
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルがアップロードされていません'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'CSVファイルのみ対応しています'}), 400

    results = []
    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        csv_reader = csv.reader(stream)

        for row in csv_reader:
            if not row:  # 空行をスキップ
                continue

            prompt = row[0]
            try:
                async for update in generate_video_with_progress(prompt):
                    if update["status"] == "completed":
                        results.append({
                            'prompt': prompt,
                            'result': {
                                'video_url': update["video_url"],
                                'request_id': update.get("request_id")
                            },
                            'status': 'success'
                        })
                        break
                    elif update["status"] == "error":
                        results.append({
                            'prompt': prompt,
                            'error': update["error"],
                            'status': 'error'
                        })
                        break

                await asyncio.sleep(1)  # API制限を考慮して遅延を入れる

            except Exception as e:
                logger.error(f"Failed to generate video for prompt '{prompt}': {str(e)}")
                results.append({
                    'prompt': prompt,
                    'error': str(e),
                    'status': 'error'
                })

        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)