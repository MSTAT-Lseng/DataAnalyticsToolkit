/**
 * regression.js — 表格上传、多列选择和两两回归图表。
 */

(function () {
    'use strict';

    const state = {
        file: null,
        selectedColumns: [],
        columnDetails: []
    };

    const fileInput = document.getElementById('regression-file');
    const fileName = document.getElementById('regression-file-name');
    const uploadStatus = document.getElementById('regression-upload-status');
    const workspace = document.getElementById('regression-workspace');
    const columnsContainer = document.getElementById('regression-columns');
    const selectedCount = document.getElementById('regression-selected-count');
    const columnHint = document.getElementById('regression-column-hint');
    const analyzeButton = document.getElementById('regression-analyze');
    const regressionForm = document.getElementById('regression-form');
    const previewContainer = document.getElementById('regression-preview');
    const previewMeta = document.getElementById('regression-preview-meta');
    const emptyState = document.getElementById('empty-state');
    const resultArea = document.getElementById('regression-result');
    const resultsMeta = document.getElementById('regression-results-meta');
    const resultsContainer = document.getElementById('regression-results');

    // Clear the native input before opening the picker so selecting the same file again works.
    fileInput.addEventListener('click', function () {
        fileInput.value = '';
    });
    fileInput.addEventListener('change', handleFileChange);
    regressionForm.addEventListener('submit', handleAnalysis);

    async function handleFileChange() {
        const file = fileInput.files[0];
        if (!file) return;

        state.file = file;
        state.selectedColumns = [];
        fileName.textContent = file.name;
        workspace.hidden = true;
        resultArea.hidden = true;
        emptyState.hidden = false;
        resultsContainer.innerHTML = '';
        setUploadStatus('正在读取表格并识别数值列……', false);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/regression/preview', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '文件预览失败');
            }
            state.columnDetails = data.column_details || [];
            renderColumnOptions(state.columnDetails);
            renderPreview(data);
            workspace.hidden = false;
            const eligibleCount = data.eligible_columns.length;
            setUploadStatus(
                `已读取 ${data.total_rows} 行、${data.columns.length} 列，可用数值列 ${eligibleCount} 列。`,
                false
            );
            updateSelection();
        } catch (error) {
            setUploadStatus(error.message, true);
            workspace.hidden = true;
        }
    }

    function renderColumnOptions(details) {
        if (!details.length) {
            columnsContainer.innerHTML = '<p class="regression-columns-empty">表格中没有可识别的列。</p>';
            columnHint.textContent = '请上传包含标题行和数值数据的表格。';
            return;
        }

        columnsContainer.innerHTML = details.map((detail, index) => {
            const name = escapeHtml(detail.name);
            const stateClass = detail.eligible ? 'is-eligible' : 'is-disabled';
            const range = detail.eligible
                ? `${formatNumber(detail.min)} - ${formatNumber(detail.max)}`
                : escapeHtml(detail.reason);
            return `
                <label class="regression-column-option ${stateClass}" for="regression-column-${index}">
                    <input type="checkbox" id="regression-column-${index}"
                        value="${name}" ${detail.eligible ? '' : 'disabled'}>
                    <span class="regression-column-main">
                        <span class="regression-column-name">${name}</span>
                        <span class="regression-column-meta">${detail.eligible ? `${detail.sample_count} 个值 · ${range}` : range}</span>
                    </span>
                    <span class="regression-column-state">${detail.eligible ? '可用' : '不可用'}</span>
                </label>
            `;
        }).join('');

        columnsContainer.querySelectorAll('input[type="checkbox"]').forEach(input => {
            input.addEventListener('change', updateSelection);
        });
    }

    function renderPreview(data) {
        previewMeta.textContent = `${data.total_rows} 行 · 显示前 ${data.rows.length} 行`;
        const header = data.columns.map(column => `<th>${escapeHtml(column)}</th>`).join('');
        const rows = data.rows.map(row => `
            <tr>${row.map(value => `<td>${escapeHtml(String(value))}</td>`).join('')}</tr>
        `).join('');
        previewContainer.innerHTML = `
            <table class="data-table">
                <thead><tr>${header}</tr></thead>
                <tbody>${rows || '<tr><td colspan="99">没有可预览的数据</td></tr>'}</tbody>
            </table>
        `;
    }

    function updateSelection() {
        state.selectedColumns = Array.from(
            columnsContainer.querySelectorAll('input[type="checkbox"]:checked')
        ).map(input => input.value);

        const count = state.selectedColumns.length;
        selectedCount.textContent = `已选 ${count} 列`;
        analyzeButton.disabled = count < 2;
        if (count < 2) {
            columnHint.textContent = '请至少选择 2 列，系统会为每两列生成一张回归图。';
        } else {
            const pairCount = count * (count - 1) / 2;
            columnHint.textContent = `当前将生成 ${pairCount} 张回归图。前一列作为自变量，后一列作为因变量。`;
        }
    }

    async function handleAnalysis(event) {
        event.preventDefault();
        if (!state.file || state.selectedColumns.length < 2) return;

        setButtonLoading(analyzeButton, '正在分析');
        const formData = new FormData();
        formData.append('file', state.file);
        formData.append('columns', JSON.stringify(state.selectedColumns));

        try {
            const response = await fetch('/api/regression', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '回归分析失败');
            }
            renderResults(data.result);
        } catch (error) {
            window.alert(`分析失败：${error.message}`);
        } finally {
            resetButton(analyzeButton, '生成回归图');
            analyzeButton.insertAdjacentHTML('afterbegin', '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="20" x2="21" y2="20"/><polyline points="5 17 9 9 13 13 18 5 21 8"/></svg>');
        }
    }

    function renderResults(result) {
        emptyState.hidden = true;
        resultArea.hidden = false;
        resultsMeta.textContent = `${result.source_file} · ${result.selected_columns.length} 列 · ${result.pair_count} 个组合`;
        resultsContainer.innerHTML = result.results.map((item, index) => `
            <article class="card regression-result-card">
                <div class="card-header">
                    <div>
                        <p class="regression-pair-label">组合 ${index + 1}</p>
                        <h3 class="card-title">${escapeHtml(item.x_label)} → ${escapeHtml(item.y_label)}</h3>
                    </div>
                    <span class="badge badge-muted">${item.sample_count} 个样本</span>
                </div>
                <div class="card-body">
                    <div class="regression-result-stats">
                        <div class="regression-stat-item">
                            <div class="stat-label">R² 决定系数</div>
                            <div class="stat-value">${formatNumber(item.r_squared, 4)}</div>
                        </div>
                        <div class="regression-stat-item">
                            <div class="stat-label">均方误差 MSE</div>
                            <div class="stat-value">${formatNumber(item.mse, 4)}</div>
                        </div>
                        <div class="regression-stat-item">
                            <div class="stat-label">斜率</div>
                            <div class="stat-value">${formatNumber(item.slope, 4)}</div>
                        </div>
                        <div class="stat-equation">${escapeHtml(item.equation)}</div>
                    </div>
                    <div id="regression-chart-${index}" class="chart-container regression-chart"></div>
                </div>
            </article>
        `).join('');

        result.results.forEach((item, index) => renderChart(`regression-chart-${index}`, item));
    }

    function renderChart(containerId, result) {
        Plotly.newPlot(containerId, [
            {
                type: 'scatter',
                mode: 'markers',
                x: result.x_values,
                y: result.y_true,
                name: '观测值',
                marker: { color: '#000000', size: 9, line: { color: '#000000', width: 1 } },
                hovertemplate: `${escapeHtml(result.x_label)}: %{x}<br>${escapeHtml(result.y_label)}: %{y}<extra></extra>`
            },
            {
                type: 'scatter',
                mode: 'lines',
                x: result.x_line,
                y: result.y_line,
                name: '回归线',
                line: { color: '#1f9d8b', width: 2 },
                hovertemplate: '回归线<extra></extra>'
            }
        ], {
            margin: { t: 18, r: 20, b: 58, l: 58 },
            xaxis: { title: { text: result.x_label, font: { size: 13, color: '#737373' } }, dtick: 1 },
            yaxis: { title: { text: result.y_label, font: { size: 13, color: '#737373' } }, dtick: 1 },
            legend: { orientation: 'h', x: 0, y: 1.08 },
            plot_bgcolor: '#ffffff',
            paper_bgcolor: '#ffffff',
            font: { family: 'ui-sans-serif, system-ui, sans-serif', color: '#525252' }
        }, { responsive: true, displaylogo: false });
    }

    function setUploadStatus(message, isError) {
        uploadStatus.textContent = message;
        uploadStatus.classList.toggle('is-error', isError);
    }

    function formatNumber(value, digits = 2) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
        return Number(value).toFixed(digits);
    }
})();
