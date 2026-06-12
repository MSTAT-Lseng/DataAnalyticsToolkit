/**
 * common.js — 数据分析工具箱公共函数
 */

/**
 * HTML 转义函数，防止 XSS
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

/**
 * 解析 CSV 文件内容，返回 { headers, rows }
 */
function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length === 0) return { headers: [], rows: [] };

    const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
        if (values.length === headers.length) {
            rows.push(values);
        }
    }
    return { headers, rows };
}

/**
 * 读取上传文件的内容
 */
function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(new Error('文件读取失败'));
        reader.readAsText(file);
    });
}

/**
 * 截断文本显示
 */
function truncateText(text, maxLen) {
    if (!text) return '';
    if (text.length <= maxLen) return escapeHtml(text);
    return escapeHtml(text.slice(0, maxLen)) + '…';
}

/**
 * 显示/隐藏加载状态
 */
function showSpinner(selector) {
    const el = document.querySelector(selector);
    if (el) {
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        spinner.id = 'loading-spinner';
        el.appendChild(spinner);
    }
}

function hideSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.remove();
}
