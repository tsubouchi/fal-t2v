const express = require('express');
const fileUpload = require('express-fileupload');
const { fal } = require('@fal-ai/client');
const app = express();
const path = require('path');

// Set FAL_AI_API_KEY from environment variable
fal.auth({
  credentials: process.env.FAL_API_KEY
});

app.use(express.json());
app.use(express.static('static'));
app.use(fileUpload({
  createParentPath: true,
  limits: {
    fileSize: 1024 * 1024 // 1MB max file size
  }
}));

// Serve the main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

// Handle single video generation
app.post('/api/generate', async (req, res) => {
  try {
    const { prompt } = req.body;

    if (!prompt) {
      return res.status(400).json({ error: 'プロンプトを入力してください' });
    }

    console.log('Generating video for prompt:', prompt);

    const result = await fal.subscribe("fal-ai/wan/v2.1/1.3b/text-to-video", {
      input: {
        prompt: prompt,
        negative_prompt: "blurry, low quality",
        num_frames: 24,
        style: "Realistic cinematic video. High quality, 8K resolution.",
        duration: 5
      },
      logs: true,
      onQueueUpdate: (update) => {
        if (update.status === "IN_PROGRESS") {
          console.log("Progress:", update.logs.map(log => log.message));
        }
      },
    });

    console.log('Generation completed:', result);

    res.json({
      status: 'completed',
      video_url: result.data.url,
      request_id: result.requestId
    });

  } catch (error) {
    console.error('Error generating video:', error);
    res.status(500).json({ error: 'サーバーエラーが発生しました' });
  }
});

// Handle batch video generation
app.post('/api/batch', async (req, res) => {
  try {
    if (!req.files || !req.files.file) {
      return res.status(400).json({ error: 'ファイルがアップロードされていません' });
    }

    const file = req.files.file;
    const prompts = file.data.toString().split('\n').filter(line => line.trim());

    console.log('Processing batch with prompts:', prompts);

    const results = [];
    for (const prompt of prompts) {
      try {
        console.log('Processing prompt:', prompt);

        const result = await fal.subscribe("fal-ai/wan/v2.1/1.3b/text-to-video", {
          input: {
            prompt: prompt,
            negative_prompt: "blurry, low quality",
            num_frames: 24,
            style: "Realistic cinematic video. High quality, 8K resolution.",
            duration: 5
          },
          logs: true,
          onQueueUpdate: (update) => {
            if (update.status === "IN_PROGRESS") {
              console.log("Progress for prompt:", prompt, update.logs.map(log => log.message));
            }
          },
        });

        console.log('Prompt completed:', prompt, result);

        results.push({
          prompt: prompt,
          status: 'success',
          video_url: result.data.url,
          request_id: result.requestId
        });

      } catch (error) {
        console.error(`Error processing prompt "${prompt}":`, error);
        results.push({
          prompt: prompt,
          status: 'error',
          error: error.message
        });
      }

      // API制限を考慮して遅延を入れる
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    res.json({ results });

  } catch (error) {
    console.error('Error in batch processing:', error);
    res.status(500).json({ error: 'バッチ処理中にエラーが発生しました' });
  }
});

const port = process.env.PORT || 5000;
app.listen(port, '0.0.0.0', () => {
  console.log(`Server is running on port ${port}`);
});