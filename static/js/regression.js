/**
 * regression.js — 回归分析页面交互逻辑
 * 处理 CSV 上传 / 手动输入，渲染统计摘要和 Plotly 散点图 + 回归线
 */

(function () {
    'use strict';

    // ---- Tab switching ----
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');
            this.classList.add('active');
            const targetId = this.dataset.tab;
            document.getElementById(targetId).style.display = '';
        });
    });

    // ---- CSV form ----
    const csvForm = document.getElementById('csv-form');
    csvForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const fileInput = document.getElementById('csv-file');
        const xCol = document.getElementById('x-col').value.trim();
        const yCol = document.getElementById('y-col').value.trim();

        if (!fileInput.files[0]) { alert('请选择 CSV 文件'); return; }
        if (!xCol || !yCol) { alert('请填写 X 和 Y 列名'); return; }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('x_column', xCol);
        formData.append('y_column', yCol);

        try {
            const resp = await fetch('/api/regression', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            if (data.success) {
                showResults(data.result);
            } else {
                alert('分析失败：' + (data.error || '未知错误'));
            }
        } catch (err) {
            alert('请求失败：' + err.message);
        }
    });

    // ---- Manual form ----
    const manualForm = document.getElementById('manual-form');
    manualForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const xRaw = document.getElementById('manual-x').value.trim();
        const yRaw = document.getElementById('manual-y').value.trim();

        if (!xRaw || !yRaw) { alert('请输入 X 和 Y 值'); return; }

        const xVals = xRaw.split(',').map(s => parseFloat(s.trim())).filter(v => !isNaN(v));
        const yVals = yRaw.split(',').map(s => parseFloat(s.trim())).filter(v => !isNaN(v));

        if (xVals.length < 2 || yVals.length < 2) {
            alert('X 和 Y 至少需要 2 个有效数值');
            return;
        }
        if (xVals.length !== yVals.length) {
            alert('X 和 Y 的数量必须一致');
            return;
        }

        try {
            const resp = await fetch('/api/regression/manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data: xVals.map((x, i) => ({ x: x, y: yVals[i] }))
                })
            });
            const data = await resp.json();
            if (data.success) {
                showResults(data.result);
            } else {
                alert('分析失败：' + (data.error || '未知错误'));
            }
        } catch (err) {
            alert('请求失败：' + err.message);
        }
    });

    // ---- Render results ----
    function showResults(r) {
        document.getElementById('regression-result').style.display = '';
        document.getElementById('empty-state').style.display = 'none';

        // Stats
        const r2Pct = (r.r_squared * 100).toFixed(2);
        document.getElementById('regression-stats').innerHTML = `
            <div class="regression-stat-item">
                <div class="stat-label">样本数</div>
                <div class="stat-value">${r.sample_count}</div>
            </div>
            <div class="regression-stat-item">
                <div class="stat-label">R² 决定系数</div>
                <div class="stat-value">${r.r_squared.toFixed(4)}</div>
            </div>
            <div class="regression-stat-item">
                <div class="stat-label">截距 (b₀)</div>
                <div class="stat-value">${r.intercept.toFixed(4)}</div>
            </div>
            <div class="regression-stat-item">
                <div class="stat-label">斜率 (b₁)</div>
                <div class="stat-value">${r.slope.toFixed(4)}</div>
            </div>
            <div class="stat-equation">
                📐 ${escapeHtml(r.equation)} &nbsp;&nbsp;|&nbsp;&nbsp; R² = ${r.r_squared.toFixed(4)} &nbsp;&nbsp;|&nbsp;&nbsp; MSE = ${r.mse.toFixed(4)}
            </div>
        `;

        // Chart — scatter + regression line
        const xVals = r.x_values;
        const yTrue = r.y_true;
        const yPred = r.y_pred;

        // Sort by X for line
        const sorted = xVals.map((x, i) => [x, yPred[i]]).sort((a, b) => a[0] - b[0]);
        const sortedX = sorted.map(p => p[0]);
        const sortedY = sorted.map(p => p[1]);

        Plotly.newPlot('regression-chart', [
            {
                type: 'scatter',
                mode: 'markers',
                x: xVals,
                y: yTrue,
                name: '观测值',
                marker: {
                    color: '#000000',
                    size: 10,
                    line: { color: '#000000', width: 1 }
                },
                hovertemplate: '<b>%{x}, %{y}</b><extra></extra>'
            },
            {
                type: 'scatter',
                mode: 'lines',
                x: sortedX,
                y: sortedY,
                name: '回归线',
                line: {
                    color: '#737373',
                    width: 2,
                    dash: 'solid'
                },
                hovertemplate: '回归线<extra></extra>'
            }
        ], {
            margin: { t: 30, r: 30, b: 60, l: 60 },
            xaxis: {
                title: { text: r.x_label, font: { size: 14, color: '#737373' } }
            },
            yaxis: {
                title: { text: r.y_label, font: { size: 14, color: '#737373' } }
            },
            legend: { x: 0.01, y: 0.99 },
            plot_bgcolor: '#ffffff',
            paper_bgcolor: '#ffffff',
            font: { family: 'ui-sans-serif, system-ui, sans-serif', color: '#525252' }
        }, { responsive: true });
    }
})();
