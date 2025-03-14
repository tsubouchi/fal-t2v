import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import requests
import csv
import io
import time
import json

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key")

# Fal.ai API設定
FAL_API_KEY = os.environ.get("FAL_API_KEY", "5db59d74-127a-4240-a028-2662d88522a4:f7e522e4afbf3486f03f771446bbfe4b")
FAL_API_URL = "https://fal.ai/models/fal-ai/wan/v2.1/1.3b/text-to-video/api"

def generate_video(prompt):
    """Fal.ai APIを使用して動画を生成する"""
    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality",
        "num_frames": 24
    }

    try:
        response = requests.post(FAL_API_URL, headers=headers, json=data)
        response.raise_for_status()
        logger.debug(f"API Response: {response.text}")  # レスポンスの内容をログに出力

        # レスポンスがJSONでない場合はエラーを発生させる
        if not response.text:
            raise ValueError("Empty response from API")

        response_data = response.json()
        if 'result' not in response_data:
            raise ValueError(f"Unexpected API response format: {response_data}")

        # APIのレスポンス形式に合わせて処理
        return {
            'video_url': response_data['result'].get('url'),
            'task_id': response_data.get('task_id')
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse API response: {str(e)}")
        raise ValueError(f"Invalid API response: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.form.get('prompt')
    if not prompt:
        return jsonify({'error': 'プロンプトを入力してください'}), 400

    try:
        result = generate_video(prompt)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        return jsonify({'error': 'サーバーエラーが発生しました'}), 500

@app.route('/batch', methods=['POST'])
def batch_generate():
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
                result = generate_video(prompt)
                results.append({
                    'prompt': prompt,
                    'result': result,
                    'status': 'success'
                })
                time.sleep(1)  # API制限を考慮して遅延を入れる
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