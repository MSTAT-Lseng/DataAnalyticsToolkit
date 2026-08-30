/**
 * social_network.js — 社会网络关系图页面交互逻辑。
 * 文本/表格来源共用分词准备流程，词表由分词统计导出的 Excel 导入。
 */

(function () {
    'use strict';

    const REQUEST_TIMEOUT_MS = 60000;

    const sourceText = document.getElementById('source-text');
    const sourceTextFile = document.getElementById('source-text-file');
    const sourceTableFile = document.getElementById('source-table-file');
    const sourceStatus = document.getElementById('source-status');
    const tablePreviewArea = document.getElementById('table-preview-area');
    const previewTable = document.getElementById('preview-table');
    const previewTableHead = previewTable.querySelector('thead');
    const previewTableBody = previewTable.querySelector('tbody');
    const tableInfo = document.getElementById('table-info');
    const selectedColumnDisplay = document.getElementById('selected-column-display');
    const segmentationFile = document.getElementById('segmentation-file');
    const segmentationStatus = document.getElementById('segmentation-status');
    const prepareBtn = document.getElementById('prepare-btn');
    const graphBtn = document.getElementById('graph-btn');
    const prepareHint = document.getElementById('prepare-hint');
    const preparedCard = document.getElementById('prepared-card');
    const preparedStats = document.getElementById('prepared-stats');
    const preparedWords = document.getElementById('prepared-words');
    const emptyState = document.getElementById('empty-state');
    const graphResults = document.getElementById('graph-results');
    const graphStats = document.getElementById('graph-stats');
    const networkChart = document.getElementById('network-chart');
    const linksTableBody = document.getElementById('links-table-body');

    const state = {
        mode: 'text',
        tableFile: null,
        selectedColumn: null,
        selectedColumnIndex: null,
        segmentationWords: [],
        segmentationImporting: false,
        segmentationImportError: false,
        prepared: false,
    };
    let segmentationImportId = 0;

    function fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
        return fetch(url, { ...options, signal: controller.signal })
            .finally(() => clearTimeout(timeoutId));
    }

    function requestErrorMessage(err) {
        return err.name === 'AbortError'
            ? '请求超时，请检查文件大小或稍后重试'
            : err.message;
    }

    ['window-size', 'min-frequency', 'max-nodes', 'max-edges'].forEach(id => {
        document.getElementById(id).addEventListener('input', invalidatePrepared);
    });

    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', function () {
            tabs.forEach(item => item.classList.remove('active'));
            tabContents.forEach(item => item.style.display = 'none');
            this.classList.add('active');
            document.getElementById(this.dataset.tab).style.display = '';
            state.mode = this.dataset.tab === 'table-tab' ? 'table' : 'text';
            sourceStatus.textContent = state.mode === 'table' ? '表格模式' : '文本模式';
            sourceStatus.className = 'badge badge-muted';
            tablePreviewArea.style.display = state.mode === 'table' && state.tableFile ? '' : 'none';
            invalidatePrepared();
        });
    });

    sourceTextFile.addEventListener('change', async function () {
        const file = this.files[0];
        if (!file) return;
        try {
            sourceText.value = await readFileAsText(file);
            invalidatePrepared();
        } catch (err) {
            alert('读取文本文件失败：' + err.message);
        }
    });

    sourceText.addEventListener('input', invalidatePrepared);

    sourceTableFile.addEventListener('change', async function () {
        const file = this.files[0];
        state.tableFile = file || null;
        state.selectedColumn = null;
        state.selectedColumnIndex = null;
        resetColumnSelection();
        invalidatePrepared();
        if (!file) {
            tablePreviewArea.style.display = 'none';
            return;
        }

        tablePreviewArea.style.display = '';
        previewTableHead.innerHTML = '';
        previewTableBody.innerHTML = '';
        tableInfo.innerHTML = '<span class="spinner"></span> 正在解析表格，请稍候…';
        try {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetchWithTimeout('/api/social-network/preview', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (!data.success) {
                alert('预览失败：' + (data.error || '未知错误'));
                tablePreviewArea.style.display = 'none';
                return;
            }
            renderPreview(data);
        } catch (err) {
            alert('请求失败：' + requestErrorMessage(err));
            tablePreviewArea.style.display = 'none';
        }
    });

    function renderPreview(data) {
        previewTableHead.innerHTML = '<tr>' + data.columns.map((column, index) =>
            `<th data-col-index="${index}">${escapeHtml(column)}</th>`
        ).join('') + '</tr>';
        previewTableBody.innerHTML = data.rows.map(row =>
            '<tr>' + row.map((value, index) =>
                `<td data-col-index="${index}">${escapeHtml(value)}</td>`
            ).join('') + '</tr>'
        ).join('');
        tableInfo.textContent = `显示前 ${data.rows.length} 行，共 ${data.total_rows} 行 · ${data.columns.length} 列`;
        previewTableHead.querySelectorAll('th').forEach(th => {
            th.addEventListener('click', () => {
                selectColumn(parseInt(th.dataset.colIndex, 10), data.columns[parseInt(th.dataset.colIndex, 10)]);
            });
        });
    }

    function selectColumn(index, name) {
        previewTableHead.querySelectorAll('th').forEach(th => th.classList.remove('col-selected'));
        previewTableBody.querySelectorAll('td').forEach(td => td.classList.remove('col-selected'));
        const head = previewTableHead.querySelector(`th[data-col-index="${index}"]`);
        if (head) head.classList.add('col-selected');
        previewTableBody.querySelectorAll(`td[data-col-index="${index}"]`).forEach(td => td.classList.add('col-selected'));
        state.selectedColumn = name;
        state.selectedColumnIndex = index;
        selectedColumnDisplay.textContent = name;
        selectedColumnDisplay.className = 'badge badge-green';
        invalidatePrepared();
    }

    function resetColumnSelection() {
        selectedColumnDisplay.textContent = '未选择（点击表头）';
        selectedColumnDisplay.className = 'badge badge-muted';
    }

    async function importFrequency(file) {
        const importId = ++segmentationImportId;
        state.segmentationWords = [];
        state.segmentationImportError = false;
        invalidatePrepared();
        if (!file) {
            state.segmentationImporting = false;
            prepareBtn.disabled = false;
            segmentationStatus.textContent = '上传“分词统计”中的“导出全部词频” Excel，作为分词规则';
            segmentationStatus.className = 'form-hint';
            return;
        }
        state.segmentationImporting = true;
        prepareBtn.disabled = true;
        segmentationStatus.className = 'form-hint';
        segmentationStatus.innerHTML = '<span class="spinner"></span> 正在导入…';
        try {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetchWithTimeout('/api/social-network/import-frequency', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (importId !== segmentationImportId) return;
            if (!data.success) {
                state.segmentationImportError = true;
                segmentationStatus.textContent = data.error || '导入失败';
                alert('分词统计结果导入失败：' + (data.error || '未知错误'));
                return;
            }
            if (!Array.isArray(data.words)) {
                throw new Error('接口返回的分词规则格式无效');
            }
            state.segmentationWords = data.words;
            segmentationStatus.textContent = `已导入 ${data.count} 个分词规则（${data.word_column}列）`;
            segmentationStatus.className = 'form-hint network-imported-status';
        } catch (err) {
            if (importId !== segmentationImportId) return;
            state.segmentationImportError = true;
            segmentationStatus.textContent = '导入失败';
            alert('分词统计结果导入失败：' + requestErrorMessage(err));
        } finally {
            if (importId === segmentationImportId) {
                state.segmentationImporting = false;
                prepareBtn.disabled = false;
            }
        }
    }

    segmentationFile.addEventListener('change', function () {
        importFrequency(this.files[0]);
    });

    function invalidatePrepared() {
        state.prepared = false;
        graphBtn.disabled = true;
        preparedCard.style.display = 'none';
        graphResults.style.display = 'none';
        emptyState.style.display = '';
        prepareHint.textContent = '准备来源数据和分词规则表后开始。';
    }

    function buildFormData() {
        const formData = new FormData();
        formData.append('mode', state.mode);
        formData.append('segmentation_words', JSON.stringify(state.segmentationWords));
        formData.append('window_size', document.getElementById('window-size').value);
        formData.append('min_frequency', document.getElementById('min-frequency').value);
        formData.append('max_nodes', document.getElementById('max-nodes').value);
        formData.append('max_edges', document.getElementById('max-edges').value);
        if (state.mode === 'text') {
            formData.append('text', sourceText.value.trim());
        } else {
            if (state.tableFile) formData.append('file', state.tableFile);
            formData.append('column', state.selectedColumn || '');
        }
        return formData;
    }

    prepareBtn.addEventListener('click', async function () {
        if (!validateSource()) return;
        setButtonLoading(prepareBtn, '准备中…');
        try {
            const response = await fetchWithTimeout('/api/social-network/prepare', {
                method: 'POST',
                body: buildFormData(),
            });
            const data = await response.json();
            if (!data.success) {
                alert('准备失败：' + (data.error || '未知错误'));
                return;
            }
            renderPrepared(data.result);
            state.prepared = true;
            graphBtn.disabled = false;
            prepareHint.textContent = '分词数据已准备，可以绘制关系图。';
        } catch (err) {
            alert('请求失败：' + requestErrorMessage(err));
        } finally {
            resetButton(prepareBtn, '准备分词数据');
        }
    });

    graphBtn.addEventListener('click', async function () {
        if (!state.prepared || !validateSource()) return;
        setButtonLoading(graphBtn, '绘制中…');
        try {
            const response = await fetchWithTimeout('/api/social-network/graph', {
                method: 'POST',
                body: buildFormData(),
            });
            const data = await response.json();
            if (!data.success) {
                alert('绘图失败：' + (data.error || '未知错误'));
                return;
            }
            renderGraph(data.result);
        } catch (err) {
            alert('请求失败：' + requestErrorMessage(err));
        } finally {
            resetButton(graphBtn, '绘制关系图');
        }
    });

    function validateSource() {
        if (state.segmentationImporting) {
            alert('分词统计结果仍在导入，请稍候');
            return false;
        }
        if (state.segmentationImportError) {
            alert('分词统计结果导入失败，请重新选择文件');
            return false;
        }
        if (!state.segmentationWords.length) {
            alert('请先导入“分词统计”中的“导出全部词频” Excel');
            return false;
        }
        if (state.mode === 'text' && !sourceText.value.trim()) {
            alert('请输入文本或上传文本文件');
            return false;
        }
        if (state.mode === 'table' && (!state.tableFile || !state.selectedColumn)) {
            alert('请上传表格并点击表头选择文本列');
            return false;
        }
        return true;
    }

    function renderPrepared(result) {
        preparedCard.style.display = '';
        preparedStats.innerHTML = `
            <span>文本单元：${result.document_count}</span>
            <span>有效词数：${result.token_count}</span>
            <span>去重词数：${result.unique_words}</span>
            <span>分词规则：${result.segmentation_word_count}</span>
        `;
        preparedWords.innerHTML = result.top_words.length
            ? result.top_words.map((item, index) => `<tr><td>${index + 1}</td><td><strong>${escapeHtml(item.word)}</strong></td><td>${item.count}</td></tr>`).join('')
            : '<tr><td colspan="3" class="text-muted">没有可显示的词语</td></tr>';
        emptyState.style.display = 'none';
        preparedCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderGraph(result) {
        graphResults.style.display = '';
        emptyState.style.display = 'none';
        graphStats.innerHTML = `
            <span>节点：${result.node_count}</span>
            <span>关系：${result.edge_count}</span>
            <span>文本单元：${result.document_count}</span>
            <span>窗口：${result.window_size}</span>
            <span>最小词频：${result.min_frequency}</span>
        `;
        linksTableBody.innerHTML = result.links.length
            ? result.links.map(link => `<tr><td>${escapeHtml(link.source)}</td><td>${escapeHtml(link.target)}</td><td>${link.weight}</td></tr>`).join('')
            : '<tr><td colspan="3" class="text-muted">当前参数下没有词语共现关系</td></tr>';
        drawPlotlyGraph(result);
        graphResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function drawPlotlyGraph(result) {
        const chartWidth = networkChart.clientWidth || 960;
        const chartHeight = networkChart.clientHeight || 600;
        const aspect = Math.max(0.85, Math.min(2.4, chartWidth / chartHeight));
        const positions = makeLayout(result.nodes, result.links, aspect);
        const nodeSizes = makeNodeSizes(result.nodes);
        const edgeGroups = new Map();
        result.links.forEach(link => {
            const weight = link.weight;
            if (!edgeGroups.has(weight)) edgeGroups.set(weight, { x: [], y: [] });
            const group = edgeGroups.get(weight);
            group.x.push(positions[link.source].x, positions[link.target].x, null);
            group.y.push(positions[link.source].y, positions[link.target].y, null);
        });
        const edgeTraces = Array.from(edgeGroups.entries()).map(([weight, group]) => ({
            type: 'scatter',
            mode: 'lines',
            x: group.x,
            y: group.y,
            hoverinfo: 'none',
            line: {
                color: 'rgba(70, 70, 70, 0.62)',
                width: Math.min(2, 0.55 + Math.sqrt(weight) * 0.36),
            },
        }));
        const nodeTrace = {
            type: 'scatter',
            mode: 'markers+text',
            x: result.nodes.map(node => positions[node.id].x),
            y: result.nodes.map(node => positions[node.id].y),
            text: result.nodes.map(node => node.label),
            textposition: 'top center',
            textfont: { size: 11, color: '#c62828' },
            customdata: result.nodes.map(node => [node.count, node.rank]),
            hovertemplate: '<b>%{text}</b><br>词频：%{customdata[0]}<br>排名：%{customdata[1]}<extra></extra>',
            marker: {
                size: nodeSizes,
                sizemode: 'diameter',
                sizemin: 14,
                color: '#7a6bb5',
                opacity: 0.9,
                line: { color: '#ffffff', width: 1.5 },
            },
        };
        Plotly.newPlot(networkChart, [...edgeTraces, nodeTrace], {
            autosize: true,
            height: chartHeight,
            margin: { t: 20, r: 20, b: 20, l: 20 },
            xaxis: {
                visible: false,
                fixedrange: false,
                range: [-aspect, aspect],
            },
            yaxis: {
                visible: false,
                fixedrange: false,
                range: [-1, 1],
            },
            showlegend: false,
            hovermode: 'closest',
            plot_bgcolor: '#ffffff',
            paper_bgcolor: '#ffffff',
            font: { family: 'ui-sans-serif, system-ui, sans-serif', color: '#525252' },
        }, { responsive: true, displaylogo: false });
    }

    function makeNodeSizes(nodes) {
        const counts = nodes.map(node => Math.max(0, Number(node.count) || 0));
        if (!counts.length) return [];
        const minCount = Math.min(...counts);
        const maxCount = Math.max(...counts);
        const minSize = 16;
        const maxSize = 52;

        if (maxCount <= minCount) {
            return nodes.map(() => 24);
        }

        const minLog = Math.log1p(minCount);
        const logRange = Math.log1p(maxCount) - minLog;
        return counts.map(count => {
            const ratio = (Math.log1p(count) - minLog) / logRange;
            return minSize + ratio * (maxSize - minSize);
        });
    }

    function makeLayout(nodes, links, aspect = 1) {
        const positions = {};
        const connectedNodeIds = new Set();
        links.forEach(link => {
            connectedNodeIds.add(link.source);
            connectedNodeIds.add(link.target);
        });
        const hasConnectedNodes = connectedNodeIds.size > 0;
        const total = Math.max(nodes.length, 1);
        nodes.forEach((node, index) => {
            const angle = (Math.PI * 2 * index) / total;
            positions[node.id] = {
                x: Math.cos(angle) * 0.78 * aspect,
                y: Math.sin(angle) * 0.78,
            };
        });
        // Fixed relaxation passes keep related nodes close while remaining deterministic.
        for (let pass = 0; pass < 56; pass += 1) {
            const delta = {};
            nodes.forEach(node => { delta[node.id] = { x: 0, y: 0 }; });

            // Keep isolated nodes near the connected component instead of
            // letting repulsion push them to the edge of the viewport.
            let coreCenterX = 0;
            let coreCenterY = 0;
            if (hasConnectedNodes) {
                const connectedNodes = nodes.filter(node => connectedNodeIds.has(node.id));
                coreCenterX = connectedNodes.reduce(
                    (sum, node) => sum + positions[node.id].x,
                    0,
                ) / connectedNodes.length;
                coreCenterY = connectedNodes.reduce(
                    (sum, node) => sum + positions[node.id].y,
                    0,
                ) / connectedNodes.length;
                nodes.forEach(node => {
                    if (connectedNodeIds.has(node.id)) return;
                    const position = positions[node.id];
                    delta[node.id].x += (coreCenterX - position.x) * 0.035;
                    delta[node.id].y += (coreCenterY - position.y) * 0.035;
                });
            }

            for (let i = 0; i < nodes.length; i += 1) {
                for (let j = i + 1; j < nodes.length; j += 1) {
                    const a = positions[nodes[i].id];
                    const b = positions[nodes[j].id];
                    const dx = a.x - b.x;
                    const dy = a.y - b.y;
                    const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 0.08);
                    const force = 0.008 / (distance * distance);
                    delta[nodes[i].id].x += dx / distance * force;
                    delta[nodes[i].id].y += dy / distance * force;
                    delta[nodes[j].id].x -= dx / distance * force;
                    delta[nodes[j].id].y -= dy / distance * force;
                }
            }
            links.forEach(link => {
                if (!positions[link.source] || !positions[link.target]) return;
                const a = positions[link.source];
                const b = positions[link.target];
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 0.08);
                const force = Math.min(0.018, 0.004 * link.weight) * (distance - 0.65);
                delta[link.source].x += dx / distance * force;
                delta[link.source].y += dy / distance * force;
                delta[link.target].x -= dx / distance * force;
                delta[link.target].y -= dy / distance * force;
            });
            nodes.forEach(node => {
                positions[node.id].x += delta[node.id].x;
                positions[node.id].y += delta[node.id].y;
            });
        }

        // Fit the relaxed coordinates to the full plot viewport. This prevents
        // dense graphs from occupying only the default center range.
        const xs = nodes.map(node => positions[node.id].x);
        const ys = nodes.map(node => positions[node.id].y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const spanX = Math.max(maxX - minX, 0.08);
        const spanY = Math.max(maxY - minY, 0.08);
        nodes.forEach(node => {
            positions[node.id].x = ((positions[node.id].x - centerX) / spanX) * 1.72 * aspect;
            positions[node.id].y = ((positions[node.id].y - centerY) / spanY) * 1.72;
        });
        return positions;
    }
})();
