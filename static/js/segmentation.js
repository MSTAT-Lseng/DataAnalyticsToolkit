/**
 * segmentation.js — 分词统计页面交互逻辑
 * 处理 Ajax 请求、渲染高频词表格与 Plotly 柱状图
 */

(function () {
    'use strict';

    const form = document.getElementById('segmentation-form');
    const textInput = document.getElementById('text-input');
    const fileInput = document.getElementById('file-input');
    const topNInput = document.getElementById('top-n');
    const removeStopwordsCheck = document.getElementById('remove-stopwords');
    const resultsContainer = document.getElementById('results-container');
    const statsBar = document.getElementById('stats-bar');
    const freqTableBody = document.querySelector('#freq-table tbody');
    const chartDiv = document.getElementById('chart');

    // ---- 文件上传时自动读取内容到 textarea ----
    fileInput.addEventListener('change', async function () {
        const file = fileInput.files[0];
        if (!file) return;
        try {
            const text = await readFileAsText(file);
            textInput.value = text;
        } catch (err) {
            alert('读取文件失败：' + err.message);
        }
    });

    // ---- 表单提交 ----
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const text = textInput.value.trim();
        if (!text) {
            alert('请输入文本或上传文件');
            return;
        }

        const topN = parseInt(topNInput.value) || 20;
        const removeStopwords = removeStopwordsCheck.checked;

        resultsContainer.style.display = 'block';

        try {
            const resp = await fetch('/api/segmentation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    top_n: topN,
                    remove_stopwords: removeStopwords
                })
            });

            const data = await resp.json();

            if (!data.success) {
                alert('分词失败：' + (data.error || '未知错误'));
                return;
            }

            const words = data.words;  // [[word, count], ...]

            // Stats bar
            statsBar.innerHTML = `
                <span>总词数（去重）：${data.unique_words || words.length}</span>
                <span>总词频：${data.total_count || words.reduce((s, w) => s + w[1], 0)}</span>
                <span>显示前 ${topN} 个</span>
            `;

            // Frequency table
            freqTableBody.innerHTML = words.map((w, i) =>
                `<tr>
                    <td>${i + 1}</td>
                    <td><strong>${escapeHtml(w[0])}</strong></td>
                    <td>${w[1]}</td>
                </tr>`
            ).join('');

            // Chart — Plotly bar chart
            const labels = words.map(w => w[0]);
            const values = words.map(w => w[1]);

            Plotly.newPlot(chartDiv, [{
                type: 'bar',
                x: labels,
                y: values,
                marker: {
                    color: '#00ed64',
                    line: { color: '#00684a', width: 1 }
                },
                text: values,
                textposition: 'outside',
                hovertemplate: '<b>%{x}</b><br>频次: %{y}<extra></extra>'
            }], {
                margin: { t: 30, r: 30, b: 80, l: 50 },
                xaxis: {
                    title: { text: '词语', font: { size: 14, color: '#3d4f5b' } },
                    tickangle: -30
                },
                yaxis: {
                    title: { text: '频次', font: { size: 14, color: '#3d4f5b' } }
                },
                plot_bgcolor: '#ffffff',
                paper_bgcolor: '#ffffff',
                font: { family: 'Lexend, sans-serif', color: '#001e2b' }
            }, { responsive: true });

        } catch (err) {
            alert('请求失败：' + err.message);
        }
    });
})();
