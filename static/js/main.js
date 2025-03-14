document.addEventListener('DOMContentLoaded', function() {
    const singleGenerationForm = document.getElementById('singleGenerationForm');
    const batchGenerationForm = document.getElementById('batchGenerationForm');
    const singleResult = document.getElementById('singleResult');
    const batchResult = document.getElementById('batchResult');

    // 単一生成フォームの処理
    singleGenerationForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const prompt = this.querySelector('#prompt').value;
        const singleProgress = singleResult.querySelector('.progress');
        const videoContainer = document.getElementById('singleVideoContainer');

        try {
            singleProgress.classList.remove('d-none');
            videoContainer.innerHTML = '';

            const progressDiv = document.createElement('div');
            progressDiv.className = 'alert alert-info mt-2';
            progressDiv.textContent = '動画を生成中...';
            videoContainer.appendChild(progressDiv);

            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '動画生成中にエラーが発生しました');
            }

            // 動画の表示
            const video = document.createElement('video');
            video.src = data.video_url;
            video.controls = true;
            video.className = 'img-fluid';

            const downloadBtn = document.createElement('a');
            downloadBtn.href = data.video_url;
            downloadBtn.className = 'btn btn-success mt-2';
            downloadBtn.innerHTML = '<i class="fa fa-download"></i> ダウンロード';
            downloadBtn.download = 'generated-video.mp4';

            videoContainer.innerHTML = '';
            videoContainer.appendChild(video);
            videoContainer.appendChild(downloadBtn);

        } catch (error) {
            showError(videoContainer, error.message);
        } finally {
            singleProgress.classList.add('d-none');
        }
    });

    // バッチ生成フォームの処理
    batchGenerationForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const batchProgress = batchResult.querySelector('.progress');
        const resultList = document.getElementById('batchResultList');

        try {
            batchProgress.classList.remove('d-none');
            resultList.innerHTML = '';

            const response = await fetch('/api/batch', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'バッチ処理中にエラーが発生しました');
            }

            // 結果の表示
            data.results.forEach((result, index) => {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'card mb-3';

                let content = `
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">プロンプト: ${result.prompt}</h6>
                `;

                if (result.status === 'success' && result.video_url) {
                    content += `
                        <video src="${result.video_url}" controls class="img-fluid mb-2"></video>
                        <a href="${result.video_url}" class="btn btn-success btn-sm" download="batch-video-${index + 1}.mp4">
                            <i class="fa fa-download"></i> ダウンロード
                        </a>
                    `;
                } else {
                    content += `
                        <div class="alert alert-danger">
                            エラー: ${result.error || '動画の生成に失敗しました'}
                        </div>
                    `;
                }

                content += '</div>';
                resultDiv.innerHTML = content;
                resultList.appendChild(resultDiv);
            });

        } catch (error) {
            showError(resultList, error.message);
        } finally {
            batchProgress.classList.add('d-none');
        }
    });

    function showError(container, message) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fa fa-exclamation-triangle"></i> ${message}
            </div>
        `;
    }
});