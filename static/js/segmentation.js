/**
 * segmentation.js — 分词统计页面交互逻辑
 * 支持文本输入和表格文件上传两种模式
 * 表格模式：选择文件自动预览，点击表头选择列，整列高亮。
 */

(function () {
    'use strict';

    // ---- DOM refs ----
    // Text tab
    const form = document.getElementById('segmentation-form');
    const textInput = document.getElementById('text-input');
    const fileInput = document.getElementById('file-input');
    const topNInput = document.getElementById('top-n');
    const removeStopwordsCheck = document.getElementById('remove-stopwords');

    // Table tab
    const tableFileInput = document.getElementById('table-file-input');
    const tableTopN = document.getElementById('table-top-n');
    const tableRemoveStopwords = document.getElementById('table-remove-stopwords');
    const tablePreviewArea = document.getElementById('table-preview-area');
    const previewTable = document.getElementById('preview-table');
    const previewTableHead = previewTable.querySelector('thead');
    const previewTableBody = previewTable.querySelector('tbody');
    const tableInfo = document.getElementById('table-info');
    const selectedColumnDisplay = document.getElementById('selected-column-display');
    const tableSegmentBtn = document.getElementById('table-segment-btn');

    // Results (shared)
    const resultsContainer = document.getElementById('results-container');
    const statsBar = document.getElementById('stats-bar');
    const freqTableBody = document.querySelector('#freq-table tbody');
    const chartDiv = document.getElementById('chart');

    // State
    let currentTableFile = null;
    let selectedColumnName = null;
    let selectedColumnIndex = null;

    // ================================================================
    // Tab Switching
    // ================================================================
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');
            this.classList.add('active');
            document.getElementById(this.dataset.tab).style.display = '';
            // Toggle table preview visibility
            if (this.dataset.tab === 'text-tab') {
                tablePreviewArea.style.display = 'none';
            } else if (this.dataset.tab === 'table-tab' && currentTableFile) {
                tablePreviewArea.style.display = '';
            }
        });
    });

    // ================================================================
    // Panel accordion (stopwords / dict — mutually exclusive)
    // ================================================================
    const panelToggles = document.querySelectorAll('.panel-toggle');
    panelToggles.forEach(btn => {
        btn.addEventListener('click', function () {
            const panel = document.getElementById(this.dataset.target);
            const sibling = document.getElementById(this.dataset.sibling);
            const isOpen = panel.style.display !== 'none';

            // Close sibling panel
            if (sibling && !isOpen) {
                sibling.style.display = 'none';
                const siblingToggle = document.querySelector(`[data-target="${this.dataset.sibling}"]`);
                if (siblingToggle) {
                    const sibLabel = siblingToggle.dataset.label || siblingToggle.textContent.replace(/ [▸▾]$/, '');
                    siblingToggle.textContent = sibLabel + ' ▸';
                    siblingToggle.dataset.label = sibLabel;
                    siblingToggle.classList.remove('open');
                }
            }

            // Toggle current
            panel.style.display = isOpen ? 'none' : '';
            const label = this.dataset.label || this.textContent.replace(/ [▸▾]$/, '');
            this.dataset.label = label;
            this.textContent = label + (isOpen ? ' ▸' : ' ▾');
            this.classList.toggle('open', !isOpen);
        });
    });

    // Stopwords file upload → textarea
    const textStopwordsFile = document.getElementById('text-stopwords-file');
    const textExtraStopwords = document.getElementById('text-extra-stopwords');
    const textStopwordsCount = document.getElementById('text-stopwords-count');

    textStopwordsFile.addEventListener('change', async function () {
        const file = this.files[0];
        if (!file) return;
        try {
            const content = await readFileAsText(file);
            textExtraStopwords.value = content;
            updateStopwordsCount('text');
        } catch (err) {
            alert('读取停用词文件失败：' + err.message);
        }
    });

    textExtraStopwords.addEventListener('input', function () {
        updateStopwordsCount('text');
    });

    const tableStopwordsFile = document.getElementById('table-stopwords-file');
    const tableExtraStopwords = document.getElementById('table-extra-stopwords');
    const tableStopwordsCount = document.getElementById('table-stopwords-count');

    tableStopwordsFile.addEventListener('change', async function () {
        const file = this.files[0];
        if (!file) return;
        try {
            const content = await readFileAsText(file);
            tableExtraStopwords.value = content;
            updateStopwordsCount('table');
        } catch (err) {
            alert('读取停用词文件失败：' + err.message);
        }
    });

    tableExtraStopwords.addEventListener('input', function () {
        updateStopwordsCount('table');
    });

    function updateStopwordsCount(tab) {
        const textarea = tab === 'text' ? textExtraStopwords : tableExtraStopwords;
        const display = tab === 'text' ? textStopwordsCount : tableStopwordsCount;
        const words = parseStopwords(textarea.value);
        display.textContent = words.length > 0 ? `${words.length} 个自定义停用词` : '';
    }

    function parseStopwords(raw) {
        if (!raw || !raw.trim()) return [];
        return raw.split(/[\n\r]+/).map(s => s.trim()).filter(Boolean);
    }

    function getExtraStopwords(tab) {
        const textarea = tab === 'text' ? textExtraStopwords : tableExtraStopwords;
        return parseStopwords(textarea.value);
    }

    // Dictionary file upload → textarea
    const textDictFile = document.getElementById('text-dict-file');
    const textExtraDict = document.getElementById('text-extra-dict');
    const textDictCount = document.getElementById('text-dict-count');

    textDictFile.addEventListener('change', async function () {
        const file = this.files[0];
        if (!file) return;
        try {
            const content = await readFileAsText(file);
            textExtraDict.value = content;
            updateDictCount('text');
        } catch (err) {
            alert('读取词典文件失败：' + err.message);
        }
    });

    textExtraDict.addEventListener('input', function () {
        updateDictCount('text');
    });

    const tableDictFile = document.getElementById('table-dict-file');
    const tableExtraDict = document.getElementById('table-extra-dict');
    const tableDictCount = document.getElementById('table-dict-count');

    tableDictFile.addEventListener('change', async function () {
        const file = this.files[0];
        if (!file) return;
        try {
            const content = await readFileAsText(file);
            tableExtraDict.value = content;
            updateDictCount('table');
        } catch (err) {
            alert('读取词典文件失败：' + err.message);
        }
    });

    tableExtraDict.addEventListener('input', function () {
        updateDictCount('table');
    });

    function updateDictCount(tab) {
        const textarea = tab === 'text' ? textExtraDict : tableExtraDict;
        const display = tab === 'text' ? textDictCount : tableDictCount;
        const words = parseStopwords(textarea.value);
        display.textContent = words.length > 0 ? `${words.length} 个词典词条` : '';
    }

    function getExtraDict(tab) {
        const textarea = tab === 'text' ? textExtraDict : tableExtraDict;
        return parseStopwords(textarea.value);
    }

    // ================================================================
    // Text tab — file → textarea
    // ================================================================
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

    // ================================================================
    // Text tab — submit
    // ================================================================
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
            const extraStopwords = getExtraStopwords('text');
            const extraDict = getExtraDict('text');

            const resp = await fetch('/api/segmentation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    top_n: topN,
                    remove_stopwords: removeStopwords,
                    extra_stopwords: extraStopwords.length > 0 ? extraStopwords : undefined,
                    extra_dict: extraDict.length > 0 ? extraDict : undefined,
                })
            });
            const data = await resp.json();
            if (!data.success) {
                alert('分词失败：' + (data.error || '未知错误'));
                return;
            }
            renderResults(data, topN, null);
        } catch (err) {
            alert('请求失败：' + err.message);
        }
    });

    // ================================================================
    // Table tab — file select → auto-preview
    // ================================================================
    tableFileInput.addEventListener('change', async function () {
        const file = tableFileInput.files[0];
        currentTableFile = file || null;

        if (!file) {
            tablePreviewArea.style.display = 'none';
            resetColumnSelection();
            return;
        }

        // Immediately start preview
        tablePreviewArea.style.display = 'block';
        previewTableHead.innerHTML = '<tr><th colspan="99">解析中…</th></tr>';
        previewTableBody.innerHTML = '';
        tableInfo.textContent = '正在加载…';
        resetColumnSelection();

        try {
            const formData = new FormData();
            formData.append('file', file);

            const resp = await fetch('/api/segmentation/preview', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();

            if (!data.success) {
                alert('预览失败：' + (data.error || '未知错误'));
                tablePreviewArea.style.display = 'none';
                return;
            }

            // Render preview table with clickable headers
            renderPreviewTable(data);
        } catch (err) {
            alert('请求失败：' + err.message);
            tablePreviewArea.style.display = 'none';
        }
    });

    function renderPreviewTable(data) {
        const columns = data.columns;
        const rows = data.rows;

        // Build header with hint text
        previewTableHead.innerHTML = '<tr>' +
            columns.map((col, idx) =>
                `<th data-col-index="${idx}" data-col-name="${escapeHtml(col)}">
                    ${escapeHtml(col)}
                </th>`
            ).join('') +
            '</tr>';

        // Build body
        previewTableBody.innerHTML = rows.map(row =>
            '<tr>' + row.map((val, idx) =>
                `<td data-col-index="${idx}">${escapeHtml(val)}</td>`
            ).join('') + '</tr>'
        ).join('');

        tableInfo.textContent =
            `显示前 ${rows.length} 行，共 ${data.total_rows} 行 · ${columns.length} 列`;

        // Bind header click handlers
        previewTableHead.querySelectorAll('th').forEach(th => {
            th.addEventListener('click', function () {
                const colIdx = parseInt(this.dataset.colIndex);
                const colName = this.dataset.colName;
                selectColumn(colIdx, colName);
            });
        });
    }

    // ================================================================
    // Column selection by header click (with full-column highlight)
    // ================================================================
    function selectColumn(colIdx, colName) {
        // Deselect previous
        if (selectedColumnIndex !== null) {
            previewTableHead.querySelectorAll('th.col-selected').forEach(th => th.classList.remove('col-selected'));
            previewTableBody.querySelectorAll('td.col-selected').forEach(td => td.classList.remove('col-selected'));
        }

        // Select new
        selectedColumnIndex = colIdx;
        selectedColumnName = colName;

        // Highlight header
        const th = previewTableHead.querySelector(`th[data-col-index="${colIdx}"]`);
        if (th) th.classList.add('col-selected');

        // Highlight all cells in this column
        previewTableBody.querySelectorAll(`td[data-col-index="${colIdx}"]`).forEach(td => {
            td.classList.add('col-selected');
        });

        // Update UI
        selectedColumnDisplay.textContent = colName;
        selectedColumnDisplay.className = 'badge badge-green';
        tableSegmentBtn.disabled = false;
    }

    function resetColumnSelection() {
        selectedColumnName = null;
        selectedColumnIndex = null;
        selectedColumnDisplay.textContent = '未选择（点击表头）';
        selectedColumnDisplay.className = 'badge badge-muted';
        tableSegmentBtn.disabled = true;
    }

    // ================================================================
    // Table tab — segment button
    // ================================================================
    tableSegmentBtn.addEventListener('click', async function () {
        if (!selectedColumnName || !currentTableFile) return;

        const topN = parseInt(tableTopN.value) || 20;
        const removeStopwords = tableRemoveStopwords.checked;

        tableSegmentBtn.disabled = true;
        tableSegmentBtn.textContent = '分词中…';

        try {
            const formData = new FormData();
            formData.append('file', currentTableFile);
            formData.append('column', selectedColumnName);
            formData.append('top_n', topN);
            formData.append('remove_stopwords', removeStopwords);

            const extraStopwords = getExtraStopwords('table');
            if (extraStopwords.length > 0) {
                formData.append('extra_stopwords', extraStopwords.join('\n'));
            }

            const extraDict = getExtraDict('table');
            if (extraDict.length > 0) {
                formData.append('extra_dict', extraDict.join('\n'));
            }

            const resp = await fetch('/api/segmentation/file', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();

            if (!data.success) {
                alert('分词失败：' + (data.error || '未知错误'));
                return;
            }

            resultsContainer.style.display = 'block';
            renderResults(data, topN, {
                sourceColumn: data.source_column,
                sourceRows: data.source_rows,
            });
        } catch (err) {
            alert('请求失败：' + err.message);
        } finally {
            tableSegmentBtn.disabled = false;
            tableSegmentBtn.textContent = '对该列分词';
        }
    });

    // ================================================================
    // Shared results rendering
    // ================================================================
    function renderResults(data, topN, sourceInfo) {
        const words = data.words;

        let sourceHtml = '';
        if (sourceInfo) {
            sourceHtml = `<span>来源列：${escapeHtml(sourceInfo.sourceColumn)}</span>
                          <span>数据行数：${sourceInfo.sourceRows}</span>`;
        }
        statsBar.innerHTML = `
            ${sourceHtml}
            <span>总词数（去重）：${data.unique_words || words.length}</span>
            <span>总词频：${data.total_count || words.reduce((s, w) => s + w[1], 0)}</span>
            <span>显示前 ${topN} 个</span>
        `;

        freqTableBody.innerHTML = words.map((w, i) =>
            `<tr>
                <td>${i + 1}</td>
                <td><strong>${escapeHtml(w[0])}</strong></td>
                <td>${w[1]}</td>
            </tr>`
        ).join('');

        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

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
    }
})();
