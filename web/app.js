/**
 * VideoNotes - 前端逻辑
 */

// ═══════════════════ 全局状态 ═══════════════════
// ═══════════════════ 免责声明 ═══════════════════
async function checkDisclaimer() {
    try {
        var agreed = await pywebview.api.has_agreed_disclaimer();
        var overlay = document.getElementById('disclaimer-overlay');
        if (!agreed) {
            overlay.classList.add('active');
        } else {
            overlay.classList.add('hidden');
        }
    } catch (e) {
        console.error('Check disclaimer failed:', e);
    }
}
function onDisclaimerCheckChange() {
    var cb = document.getElementById('agree-checkbox');
    var btn = document.getElementById('btn-agree');
    btn.disabled = !cb.checked;
}
async function acceptDisclaimer() {
    try {
        await pywebview.api.save_disclaimer_agreement();
        var overlay = document.getElementById('disclaimer-overlay');
        overlay.classList.remove('active');
        setTimeout(function() {
            overlay.classList.add('hidden');
        }, 400);
    } catch (e) {
        console.error('Save agreement failed:', e);
    }
}
async function declineDisclaimer() {
    try {
        await pywebview.api.exit_app();
    } catch (e) {
        // 如果 exit_app 失败，前端强制提示
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-size:16px;color:#666;">您已拒绝用户协议，请关闭窗口。</div>';
    }
}
let selectedFiles = [];
let pollTimer = null;
let saveTimer = null;
let currentConfig = {};

// ═══════════════════ 初始化 ═══════════════════

window.addEventListener('pywebviewready', async () => {
    console.log('pywebview ready');
    await checkDisclaimer();
    await loadConfig();
    startPolling();
    bindConfigInputs();
    checkFirstTime();
});

// ═══════════════════ Tab 切换 ═══════════════════

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === 'panel-' + tabName);
    });
}

// ═══════════════════ 配置管理 ═══════════════════

async function loadConfig() {
    try {
        const config = await pywebview.api.load_config();
        currentConfig = config || {};
        document.querySelectorAll('.cfg-input').forEach(input => {
            const key = input.dataset.key;
            if (key && currentConfig[key]) {
                input.value = currentConfig[key];
            }
        });
    } catch (e) {
        console.error('加载配置失败:', e);
    }
}

function bindConfigInputs() {
    document.querySelectorAll('.cfg-input').forEach(input => {
        input.addEventListener('input', () => {
            currentConfig[input.dataset.key] = input.value;
            debounceSave();
        });
    });
}

function debounceSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
        try {
            const result = await pywebview.api.save_config(currentConfig);
            if (result && result.ok) {
                showSaveIndicator();
            } else if (result && result.error) {
                showToast('保存失败: ' + result.error, 'error');
            }
        } catch (e) {
            showToast('保存配置时出错', 'error');
        }
    }, 500);
}

function showSaveIndicator() {
    const el = document.getElementById('save-indicator');
    el.classList.add('visible');
    setTimeout(() => el.classList.remove('visible'), 2200);
}

async function checkFirstTime() {
    try {
        const check = await pywebview.api.check_config_complete();
        const banner = document.getElementById('first-time-banner');
        if (!check.complete && Object.keys(currentConfig).length === 0) {
            banner.style.display = 'flex';
            // 首次打开自动切到设置页
            switchTab('settings');
        } else {
            banner.style.display = 'none';
        }
    } catch (e) {
        // 忽略
    }
}

// ─── 选择文件夹 ───

async function selectFolder() {
    try {
        const folder = await pywebview.api.select_folder();
        if (folder) {
            const input = document.getElementById('cfg-save_markdown_path');
            input.value = folder;
            currentConfig['save_markdown_path'] = folder;
            debounceSave();
        }
    } catch (e) {
        showToast('选择文件夹失败', 'error');
    }
}

// ═══════════════════ 上传弹窗 ═══════════════════

function openUploadModal() {
    selectedFiles = [];
    renderSelectedFiles();
    document.getElementById('modal-overlay').classList.add('active');
}

function closeUploadModal() {
    document.getElementById('modal-overlay').classList.remove('active');
    selectedFiles = [];
}

function handleOverlayClick(event) {
    if (event.target === event.currentTarget) {
        closeUploadModal();
    }
}

async function handleSelectFiles() {
    try {
        const files = await pywebview.api.select_files();
        if (files && files.length > 0) {
            files.forEach(fp => {
                if (!selectedFiles.includes(fp)) {
                    selectedFiles.push(fp);
                }
            });
            renderSelectedFiles();
        }
    } catch (e) {
        showToast('选择文件失败', 'error');
    }
}

function removeSelectedFile(index) {
    selectedFiles.splice(index, 1);
    renderSelectedFiles();
}

function renderSelectedFiles() {
    const container = document.getElementById('selected-files');
    const submitBtn = document.getElementById('btn-submit');
    const countSpan = document.getElementById('btn-count');

    if (selectedFiles.length === 0) {
        container.innerHTML = '';
        submitBtn.disabled = true;
        countSpan.textContent = '';
        return;
    }

    submitBtn.disabled = false;
    countSpan.textContent = selectedFiles.length;

    container.innerHTML = selectedFiles.map((fp, i) => {
        const name = fp.split(/[/\\]/).pop();
        return '<div class="selected-file">' +
            '<div class="selected-file-info">' +
                '<span class="selected-file-icon">🎬</span>' +
                '<span class="selected-file-name" title="' + escapeHtml(fp) + '">' + escapeHtml(name) + '</span>' +
            '</div>' +
            '<button class="selected-file-remove" onclick="removeSelectedFile(' + i + ')" title="移除">×</button>' +
        '</div>';
    }).join('');
}

// ─── 提交任务 ───

async function submitSelectedFiles() {
    if (selectedFiles.length === 0) return;

    // 检查配置
    try {
        const check = await pywebview.api.check_config_complete();
        if (!check.complete) {
            showToast('请先完成系统设置（缺少：' + check.missing.join('、') + '）', 'error');
            return;
        }
    } catch (e) {
        // 继续
    }

    try {
        const result = await pywebview.api.submit_tasks(selectedFiles);
        closeUploadModal();
        if (result && result.length > 0) {
            showToast('已提交 ' + result.length + ' 个任务', 'success');
        }
    } catch (e) {
        showToast('提交任务失败', 'error');
    }
}

// ═══════════════════ 任务轮询 ═══════════════════

function startPolling() {
    pollTimer = setInterval(pollTasks, 2000);
    pollTasks();
}

async function pollTasks() {
    try {
        const tasks = await pywebview.api.get_tasks();
        renderTasks(tasks);
    } catch (e) {
        // 静默
    }
}

var _lastTasksKey = '';
function renderTasks(tasks) {
    var emptyState = document.getElementById('empty-state');
    var taskList = document.getElementById('task-list');
    if (!tasks || tasks.length === 0) {
        emptyState.classList.remove('hidden');
        if (_lastTasksKey !== 'empty') {
            taskList.innerHTML = '';
            _lastTasksKey = 'empty';
        }
        return;
    }
    emptyState.classList.add('hidden');
    // 生成一个不含 elapsed 的 key，只在状态/结果变化时重建 DOM
    var structureKey = tasks.map(function(t) {
        return t.id + ':' + t.status + ':' + (t.result || '') + ':' + (t.error || '');
    }).join('|');
    if (structureKey !== _lastTasksKey) {
        // 结构变了，重建
        _lastTasksKey = structureKey;
        taskList.innerHTML = tasks.map(function(task) {
            var sc = getStatusConfig(task.status);
            var elapsed = formatElapsed(task.elapsed);
            var metaHtml = '<span class="status-label ' + task.status + '">' + sc.label + '</span>';
            if (task.status === 'processing') {
                metaHtml += '<span class="elapsed" data-task-elapsed="' + task.id + '">&middot; ' + elapsed + '</span>';
            }
            var extraHtml = '';
            if (task.status === 'completed' && task.result) {
                var fname = task.result.split(/[/\\]/).pop();
                extraHtml = '<div class="task-result-path" title="' + escapeHtml(task.result) + '">&#x1f4c4; ' + escapeHtml(fname) + '</div>';
            }
            if (task.status === 'error' && task.error) {
                extraHtml = '<div class="task-error-msg" title="' + escapeHtml(task.error) + '">' + escapeHtml(task.error) + '</div>';
            }
            var actionsHtml = '';
            if (task.status === 'processing') {
                actionsHtml = '<button class="btn-action danger" onclick="cancelTask(\'' + task.id + '\')">取消</button>';
            } else if (task.status === 'completed') {
                actionsHtml =
                    '<button class="btn-action success" onclick="openFile(\'' + escapeJs(task.result) + '\')">打开 PDF</button>' +
                    '<button class="btn-action" onclick="openFolder(\'' + escapeJs(task.result) + '\')">所在目录</button>' +
                    '<button class="btn-action danger" onclick="removeTask(\'' + task.id + '\')">移除</button>';
            } else {
                actionsHtml = '<button class="btn-action danger" onclick="removeTask(\'' + task.id + '\')">移除</button>';
            }
            return '<div class="task-card" data-id="' + task.id + '">' +
                '<div class="task-status-icon ' + task.status + '">' + sc.icon + '</div>' +
                '<div class="task-info">' +
                    '<div class="task-filename" title="' + escapeHtml(task.file_name) + '">' + escapeHtml(task.file_name) + '</div>' +
                    '<div class="task-meta">' + metaHtml + '</div>' +
                    extraHtml +
                '</div>' +
                '<div class="task-actions">' + actionsHtml + '</div>' +
            '</div>';
        }).join('');
    } else {
        // 结构没变，只更新时间文字
        tasks.forEach(function(task) {
            if (task.status === 'processing') {
                var el = document.querySelector('[data-task-elapsed="' + task.id + '"]');
                if (el) {
                    el.textContent = '\u00B7 ' + formatElapsed(task.elapsed);
                }
            }
        });
    }
}

function getStatusConfig(status) {
    var configs = {
        processing: {
            label: '处理中...',
            icon: '<svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 2a10 10 0 0 1 10 10" /></svg>'
        },
        completed: {
            label: '已完成',
            icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
        },
        error: {
            label: '处理失败',
            icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        },
        cancelled: {
            label: '已取消',
            icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>'
        }
    };
    return configs[status] || configs.error;
}

// ═══════════════════ 任务操作 ═══════════════════

async function cancelTask(taskId) {
    try {
        await pywebview.api.cancel_task(taskId);
        showToast('任务已取消', 'info');
        pollTasks();
    } catch (e) {
        showToast('取消失败', 'error');
    }
}

async function removeTask(taskId) {
    try {
        await pywebview.api.remove_task(taskId);
        pollTasks();
    } catch (e) {
        showToast('移除失败', 'error');
    }
}

async function openFile(path) {
    try {
        await pywebview.api.open_file(path);
    } catch (e) {
        showToast('打开文件失败', 'error');
    }
}

async function openFolder(path) {
    try {
        await pywebview.api.open_folder(path);
    } catch (e) {
        showToast('打开文件夹失败', 'error');
    }
}

// ═══════════════════ Toast ═══════════════════

function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    var icons = { success: '✓', error: '✗', info: 'ⓘ' };

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML = '<span class="toast-icon">' + (icons[type] || icons.info) + '</span>' + escapeHtml(message);

    container.appendChild(toast);

    requestAnimationFrame(function() {
        requestAnimationFrame(function() {
            toast.classList.add('show');
        });
    });

    setTimeout(function() {
        toast.classList.remove('show');
        setTimeout(function() { toast.remove(); }, 400);
    }, 3500);
}

// ═══════════════════ 工具 ═══════════════════

function formatElapsed(seconds) {
    if (seconds < 60) return seconds + '秒';
    var mins = Math.floor(seconds / 60);
    var secs = seconds % 60;
    if (mins < 60) return mins + '分' + secs + '秒';
    var hours = Math.floor(mins / 60);
    var rmins = mins % 60;
    return hours + '时' + rmins + '分';
}

function openGithub() {
    try {
        pywebview.api.open_url('https://github.com/ououuo-mark/super_summary_note');
    } catch (e) {
        window.open('https://github.com/ououuo-mark/super_summary_note', '_blank');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeJs(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}