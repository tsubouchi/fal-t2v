import os
import logging
from flask import Flask, render_template, request, jsonify
import requests
import json

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key")

# Fal.ai API設定
FAL_API_KEY = os.environ.get("FAL_API_KEY")
FAL_API_URL = "https://fal.ai/models/fal-ai/wan/v2.1/1.3b/text-to-video/api"

def generate_video(prompt):
    """Fal.ai APIを使用して動画を生成"""
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
        }
    }

    try:
        logger.debug(f"Sending request to Fal.ai API:")
        logger.debug(f"Data: {json.dumps(data, indent=2)}")

        response = requests.post(FAL_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        logger.debug(f"Received response: {json.dumps(result, indent=2)}")

        return {
            "status": "completed",
            "video_url": result["data"]["url"],
            "request_id": result.get("requestId")
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """単一動画生成エンドポイント"""
    data = request.get_json()
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "プロンプトを入力してください"}), 400

    result = generate_video(prompt)
    if result["status"] == "error":
        return jsonify({"error": result["error"]}), 500

    return jsonify(result)

@app.route('/api/batch', methods=['POST'])
def api_batch():
    """バッチ動画生成エンドポイント"""
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルがアップロードされていません'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'CSVファイルのみ対応しています'}), 400

    results = []
    try:
        content = file.read().decode('utf-8')
        prompts = [line.strip() for line in content.split('\n') if line.strip()]

        for prompt in prompts:
            result = generate_video(prompt)
            results.append({
                'prompt': prompt,
                'status': 'success' if result["status"] == "completed" else 'error',
                'video_url': result.get("video_url"),
                'error': result.get("error")
            })

    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)