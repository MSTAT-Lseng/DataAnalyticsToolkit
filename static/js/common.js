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

/**
 * 按钮进入加载状态：禁用、显示旋转图标、替换文字
 * @param {HTMLElement} btn - 按钮元素
 * @param {string} loadingText - 加载中显示的文字
 */
function setButtonLoading(btn, loadingText) {
    if (!btn) return;
    btn.disabled = true;
    btn._originalText = btn.textContent;
    btn.classList.add('btn-loading');
    btn.innerHTML = `<span class="spinner spinner-light"></span>${loadingText}`;
}

/**
 * 恢复按钮到正常状态
 * @param {HTMLElement} btn - 按钮元素
 * @param {string} [text] - 恢复后的文字，不传则使用加载前文字
 */
function resetButton(btn, text) {
    if (!btn) return;
    btn.disabled = false;
    btn.classList.remove('btn-loading');
    btn.textContent = text || btn._originalText || btn.textContent;
    delete btn._originalText;
}

/**
 * 在容器内显示加载覆盖层
 * @param {HTMLElement} container - 容器元素
 * @param {string} message - 加载提示文字
 */
function showLoadingOverlay(container, message) {
    if (!container) return;
    hideLoadingOverlay(container);
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loading-overlay-inline';
    overlay.innerHTML = `
        <span class="spinner spinner-lg"></span>
        <span class="loading-overlay-text">${escapeHtml(message)}</span>
    `;
    container.innerHTML = '';
    container.appendChild(overlay);
}

/**
 * 移除容器内的加载覆盖层
 * @param {HTMLElement} container - 容器元素
 */
function hideLoadingOverlay(container) {
    if (!container) return;
    const overlay = container.querySelector('#loading-overlay-inline');
    if (overlay) overlay.remove();
}
