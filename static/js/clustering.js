/**
 * clustering.js — 文本与表格列的 TF-IDF + K-Means 聚类。
 */

(function () {
    'use strict';

    const state = {
        file: null,
        column: '',
        result: null
    };

    const modeButtons = document.querySelectorAll('[data-cluster-mode]');
    const textPanel = document.getElementById('cluster-text-panel');
    const tablePanel = document.getElementById('cluster-table-panel');
    const textForm = document.getElementById('cluster-text-form');
    const textInput = document.getElementById('cluster-text');
    const textCount = document.getElementById('cluster-text-count');
    const textSubmit = document.getElementById('cluster-text-submit');
    const fileInput = document.getElementById('cluster-file');
    const fileName = document.getElementById('cluster-file-name');
    const uploadStatus = document.getElementById('cluster-upload-status');
    const columnSelect = document.getElementById('cluster-column');
    const tableForm = document.getElementById('cluster-table-form');
    const tableCount = document.getElementById('cluster-table-count');
    const tableSubmit = document.getElementById('cluster-table-submit');
    const previewCard = document.getElementById('cluster-table-preview-card');
    const previewContainer = document.getElementById('cluster-preview');
    const previewMeta = document.getElementById('cluster-preview-meta');
    const emptyState = document.getElementById('cluster-empty-state');
    const resultArea = document.getElementById('cluster-result');
    const resultsMeta = document.getElementById('cluster-results-meta');
    const method = document.getElementById('cluster-method');
    const resultCount = document.getElementById('cluster-result-count');
    const featureCount = document.getElementById('cluster-feature-count');
    const summary = document.getElementById('cluster-summary');
    const items = document.getElementById('cluster-items');
    const exportButton = document.getElementById('cluster-export');

    modeButtons.forEach(button => {
        button.addEventListener('click', () => setMode(button.dataset.clusterMode));
    });
    fileInput.addEventListener('click', function () {
        fileInput.value = '';
    });
    fileInput.addEventListener('change', handleFileChange);
    textForm.addEventListener('submit', handleTextClustering);
    tableForm.addEventListener('submit', handleTableClustering);
    exportButton.addEventListener('click', handleExport);
    columnSelect.addEventListener('change', function () {
        state.column = columnSelect.value;
        tableSubmit.disabled = !state.column;
    });

    function setMode(mode) {
        modeButtons.forEach(button => {
            const active = button.dataset.clusterMode === mode;
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', String(active));
        });
        textPanel.hidden = mode !== 'text';
        tablePanel.hidden = mode !== 'table';
    }

    async function handleFileChange() {
        const file = fileInput.files[0];
        if (!file) return;

        state.file = file;
        state.column = '';
        state.result = null;
        fileName.textContent = file.name;
        tableForm.hidden = true;
        previewCard.hidden = true;
        resultArea.hidden = true;
        exportButton.hidden = true;
        exportButton.disabled = true;
        emptyState.hidden = false;
        setUploadStatus('正在读取表格并识别可聚类列……', false);

        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch('/api/heat-analysis/clustering/preview', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '文件预览失败');
            }
            renderColumnOptions(data.column_details || []);
            renderPreview(data);
            tableForm.hidden = false;
            previewCard.hidden = false;
            const eligibleCount = (data.column_details || []).filter(item => item.eligible).length;
            setUploadStatus(
                `已读取 ${data.total_rows} 行、${data.columns.length} 列，可用聚类列 ${eligibleCount} 列。`,
                false
            );
        } catch (error) {
            setUploadStatus(error.message, true);
            tableForm.hidden = true;
            previewCard.hidden = true;
        }
    }

    function renderColumnOptions(details) {
        const eligible = details.filter(detail => detail.eligible);
        if (!eligible.length) {
            columnSelect.innerHTML = '<option value="">没有包含至少 2 个非空值的列</option>';
            columnSelect.disabled = true;
            tableSubmit.disabled = true;
            return;
        }
        columnSelect.innerHTML = `
            <option value="">请选择一列</option>
            ${eligible.map(detail => `<option value="${escapeHtml(detail.name)}">${escapeHtml(detail.name)} · ${detail.sample_count} 个值</option>`).join('')}
        `;
        columnSelect.disabled = false;
        tableSubmit.disabled = true;
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

    async function handleTextClustering(event) {
        event.preventDefault();
        const text = textInput.value.trim();
        if (!text) {
            window.alert('请输入需要聚类的文本');
            return;
        }

        const formData = new FormData();
        formData.append('mode', 'text');
        formData.append('text', text);
        formData.append('n_clusters', textCount.value);
        await submitClustering(formData, textSubmit);
    }

    async function handleTableClustering(event) {
        event.preventDefault();
        if (!state.file || !state.column) return;

        const formData = new FormData();
        formData.append('mode', 'table');
        formData.append('file', state.file);
        formData.append('column', state.column);
        formData.append('n_clusters', tableCount.value);
        await submitClustering(formData, tableSubmit);
    }

    async function submitClustering(formData, button) {
        setButtonLoading(button, '正在聚类');
        try {
            const response = await fetch('/api/heat-analysis/clustering', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '聚类分析失败');
            }
            renderResults(data.result);
        } catch (error) {
            window.alert(`聚类失败：${error.message}`);
        } finally {
            resetButton(button, '开始聚类');
        }
    }

    function renderResults(result) {
        state.result = result;
        emptyState.hidden = true;
        resultArea.hidden = false;
        exportButton.hidden = false;
        exportButton.disabled = false;
        resultsMeta.textContent = result.source_label;
        method.textContent = result.method;
        resultCount.textContent = `${result.document_count} 个样本 · ${result.n_clusters} 个聚类`;
        featureCount.textContent = `${result.feature_count} 个 TF-IDF 特征`;

        summary.innerHTML = result.clusters.map((cluster, index) => `
            <article class="cluster-summary-item">
                <div class="cluster-summary-head">
                    <span class="cluster-color-dot cluster-color-${index % 6}" aria-hidden="true"></span>
                    <strong>${escapeHtml(cluster.label)}</strong>
                    <span>${cluster.size} 个样本</span>
                </div>
                <div class="cluster-keywords">
                    ${(cluster.keywords || []).map(keyword => `<span>${escapeHtml(keyword)}</span>`).join('') || '<span>暂无突出关键词</span>'}
                </div>
            </article>
        `).join('');

        items.innerHTML = `
            <table class="data-table cluster-items-table">
                <thead><tr><th>序号</th><th>聚类</th><th>文本</th><th>中心距离</th></tr></thead>
                <tbody>${result.items.map(item => `
                    <tr>
                        <td>${item.index}</td>
                        <td><span style="color: white" class="cluster-label cluster-color-${(item.cluster - 1) % 6}">${escapeHtml(item.cluster_label)}</span></td>
                        <td>${escapeHtml(item.text)}</td>
                        <td>${formatNumber(item.distance, 4)}</td>
                    </tr>
                `).join('')}</tbody>
            </table>
        `;
        renderChart(result);
    }

    async function handleExport() {
        if (!state.result) return;

        setButtonLoading(exportButton, '导出中…');
        try {
            const response = await fetch('/api/heat-analysis/clustering/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ result: state.result })
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || '服务器导出失败');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = '聚类分析结果.xlsx';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } catch (error) {
            window.alert(`导出失败：${error.message}`);
        } finally {
            resetButton(exportButton, '导出 Excel');
        }
    }

    function renderChart(result) {
        const colors = ['#4b6fe8', '#d45b45', '#1f9d8b', '#8a55c7', '#e4b63f', '#737373'];
        const traces = result.clusters.map((cluster, index) => {
            const clusterItems = result.items.filter(item => item.cluster === cluster.id);
            return {
                type: 'scatter',
                mode: 'markers',
                name: cluster.label,
                x: clusterItems.map(item => item.x),
                y: clusterItems.map(item => item.y),
                customdata: clusterItems.map(item => [item.index, item.text]),
                marker: {
                    color: colors[index % colors.length],
                    size: 10,
                    line: { color: '#ffffff', width: 1 }
                },
                hovertemplate: '样本 %{customdata[0]}<br>%{customdata[1]}<extra></extra>'
            };
        });
        const chartHeight = Math.max(420, Math.min(640, result.n_clusters * 32 + 360));
        Plotly.newPlot('cluster-chart', traces, {
            height: chartHeight,
            margin: { t: 24, r: 24, b: 58, l: 58 },
            xaxis: { title: { text: 'TF-IDF 维度 1' }, zeroline: false },
            yaxis: { title: { text: 'TF-IDF 维度 2' }, zeroline: false },
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
