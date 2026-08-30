/**
 * heat_analysis.js — 相关性热力图。
 */

(function () {
    'use strict';

    const state = {
        file: null,
        selectedColumns: []
    };
    const fileInput = document.getElementById('heat-file');
    const fileName = document.getElementById('heat-file-name');
    const uploadStatus = document.getElementById('heat-upload-status');
    const workspace = document.getElementById('heat-workspace');
    const columnsContainer = document.getElementById('heat-columns');
    const selectedCount = document.getElementById('heat-selected-count');
    const columnHint = document.getElementById('heat-column-hint');
    const analyzeButton = document.getElementById('heat-analyze');
    const analysisForm = document.getElementById('heat-form');
    const previewContainer = document.getElementById('heat-preview');
    const previewMeta = document.getElementById('heat-preview-meta');
    const emptyState = document.getElementById('heat-empty-state');
    const resultArea = document.getElementById('heat-result');
    const resultsMeta = document.getElementById('heat-results-meta');
    const sampleCount = document.getElementById('heat-sample-count');

    fileInput.addEventListener('click', function () {
        fileInput.value = '';
    });
    fileInput.addEventListener('change', handleFileChange);
    analysisForm.addEventListener('submit', handleAnalysis);

    async function handleFileChange() {
        const file = fileInput.files[0];
        if (!file) return;

        state.file = file;
        state.selectedColumns = [];
        fileName.textContent = file.name;
        workspace.hidden = true;
        resultArea.hidden = true;
        emptyState.hidden = false;
        setUploadStatus('正在读取表格并识别数值列……', false);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/heat-analysis/preview', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '文件预览失败');
            }
            renderColumnOptions(data.column_details || []);
            renderPreview(data);
            workspace.hidden = false;
            setUploadStatus(
                `已读取 ${data.total_rows} 行、${data.columns.length} 列，可用数值列 ${data.eligible_columns.length} 列。`,
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
                <label class="regression-column-option ${stateClass}" for="heat-column-${index}">
                    <input type="checkbox" id="heat-column-${index}"
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
        columnHint.textContent = count < 2
            ? '请至少选择 2 列，系统会计算每一对列之间的热力值。'
            : `当前将交叉计算 ${count * count} 个热力格。`;
    }

    async function handleAnalysis(event) {
        event.preventDefault();
        if (!state.file || state.selectedColumns.length < 2) return;

        setButtonLoading(analyzeButton, '正在分析');
        const formData = new FormData();
        formData.append('file', state.file);
        formData.append('columns', JSON.stringify(state.selectedColumns));

        try {
            const response = await fetch('/api/heat-analysis', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '热力分析失败');
            }
            renderResults(data.result);
        } catch (error) {
            window.alert(`分析失败：${error.message}`);
        } finally {
            resetButton(analyzeButton, '生成热力图');
        }
    }

    function renderResults(result) {
        emptyState.hidden = true;
        resultArea.hidden = false;
        resultsMeta.textContent = `${result.source_file} · ${result.columns.length} 列`;
        sampleCount.textContent = `${result.sample_count} 个样本`;
        renderHeatmap(result);
    }

    function renderHeatmap(result) {
        const labels = result.columns;
        const text = result.values.map(row => row.map(value => Number(value).toFixed(2)));
        const chartHeight = Math.max(420, Math.min(720, labels.length * 64 + 180));

        Plotly.newPlot('heat-chart', [{
            type: 'heatmap',
            z: result.values,
            x: labels,
            y: labels,
            zmin: -1,
            zmax: 1,
            colorscale: [
                [0, '#d45b45'],
                [0.25, '#f2b39f'],
                [0.5, '#ffffff'],
                [0.75, '#9fd9d1'],
                [1, '#1f9d8b']
            ],
            text: text,
            texttemplate: '%{text}',
            textfont: { color: '#171717', size: 13 },
            xgap: 2,
            ygap: 2,
            hovertemplate: '%{x} × %{y}<br>热力值：%{z:.4f}<extra></extra>',
            colorbar: {
                title: { text: '热力值', side: 'right' },
                thickness: 12,
                len: 0.8,
                tickvals: [-1, -0.5, 0, 0.5, 1]
            }
        }], {
            height: chartHeight,
            margin: { t: 24, r: 72, b: 80, l: 92 },
            xaxis: { side: 'bottom', tickangle: labels.length > 5 ? -35 : 0, automargin: true },
            yaxis: { autorange: 'reversed', automargin: true },
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
