/**
 * Переиспользуемые утилиты для тестовых страниц
 * Используется всеми HTML тестовыми страницами
 */

// === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
let testResults = {};
let testLogs = {};
let isRunning = false;

// === ОСНОВНЫЕ ФУНКЦИИ ===

/**
 * Создает HTML карточку для теста
 * @param {Object} test - Объект теста
 * @returns {string} HTML строка карточки
 */
function createTestCard(test) {
    return `
        <div class="test-card" id="card-${test.id}">
            <div class="test-title">
                <span class="icon">🧪</span>
                <span>${test.title}</span>
                <span class="test-status pending" id="status-${test.id}">Ожидание</span>
            </div>
            <div class="test-description">${test.description}</div>
            <div class="test-log" id="log-${test.id}">Ожидание выполнения...</div>
            <div class="test-actions" id="actions-${test.id}" style="margin-top: 10px; display: none;">
                <button class="btn btn-info" onclick="downloadTestLog('${test.id}')" style="font-size: 12px; padding: 5px 10px;">
                    📄 Скачать лог
                </button>
                <button class="btn btn-info" onclick="showDetailedLog('${test.id}')" style="font-size: 12px; padding: 5px 10px;">
                    🔍 Детальный лог
                </button>
            </div>
        </div>
    `;
}

/**
 * Обновляет статус теста
 * @param {string} testId - ID теста
 * @param {string} status - Статус (pending, running, passed, failed)
 * @param {string} message - Сообщение для лога
 */
function updateTestStatus(testId, status, message = '') {
    const card = document.getElementById(`card-${testId}`);
    const statusEl = document.getElementById(`status-${testId}`);
    const logEl = document.getElementById(`log-${testId}`);
    const actionsEl = document.getElementById(`actions-${testId}`);
    
    // Обновляем статус
    statusEl.textContent = status;
    statusEl.className = `test-status ${status}`;
    
    // Обновляем карточку
    card.className = `test-card ${status}`;
    
    // Обновляем лог
    if (message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${message}`;
        logEl.innerHTML += `<div>${logEntry}</div>`;
        logEl.scrollTop = logEl.scrollHeight;
        
        // Сохраняем в детальный лог
        if (!testLogs[testId]) {
            testLogs[testId] = [];
        }
        testLogs[testId].push(logEntry);
    }
    
    // Показываем кнопки действий для завершенных тестов
    if (status === 'passed' || status === 'failed') {
        actionsEl.style.display = 'block';
    }
}

/**
 * Обновляет прогресс выполнения тестов
 * @param {number} total - Общее количество тестов
 * @param {Object} results - Результаты тестов
 */
function updateProgress(total, results = testResults) {
    const completed = Object.keys(results).length;
    const passed = Object.values(results).filter(r => r === true).length;
    const failed = Object.values(results).filter(r => r === false).length;
    
    const progress = (completed / total) * 100;
    document.getElementById('progressFill').style.width = `${progress}%`;
    
    const summaryText = document.getElementById('summaryText');
    if (completed === 0) {
        summaryText.textContent = 'Ожидание запуска тестов...';
    } else if (completed < total) {
        summaryText.textContent = `Выполнено: ${completed}/${total} | Пройдено: ${passed} | Провалено: ${failed}`;
    } else {
        summaryText.innerHTML = `
            <strong>Завершено: ${completed}/${total}</strong><br>
            ✅ Пройдено: ${passed}<br>
            ❌ Провалено: ${failed}<br>
            📈 Успешность: ${((passed/total)*100).toFixed(1)}%
        `;
    }
}

/**
 * Обновляет статус страницы
 * @param {string} message - Сообщение
 * @param {string} type - Тип (info, success, error, running)
 */
function updateStatus(message, type = 'info') {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status ${type}`;
}

/**
 * Очищает результаты тестов
 * @param {Array} allTests - Массив всех тестов
 */
function clearResults(allTests) {
    testResults = {};
    testLogs = {};
    updateProgress(allTests.length);
    
    allTests.forEach(test => {
        updateTestStatus(test.id, 'pending', 'Ожидание выполнения...');
        document.getElementById(`log-${test.id}`).innerHTML = 'Ожидание выполнения...';
        document.getElementById(`actions-${test.id}`).style.display = 'none';
    });
    
    updateStatus('Результаты очищены', 'info');
}

/**
 * Скачивает лог теста
 * @param {string} testId - ID теста
 * @param {Array} allTests - Массив всех тестов
 */
function downloadTestLog(testId, allTests) {
    const test = allTests.find(t => t.id === testId);
    const logs = testLogs[testId] || [];
    const result = testResults[testId];
    
    let logContent = `# Детальный лог теста: ${test.title}\n`;
    logContent += `Дата: ${new Date().toLocaleString()}\n`;
    logContent += `Статус: ${result ? '✅ ПРОЙДЕН' : '❌ ПРОВАЛЕН'}\n`;
    logContent += `Описание: ${test.description}\n`;
    logContent += `Категория: ${test.category}\n\n`;
    logContent += `## Логи выполнения:\n\n`;
    
    logs.forEach(logEntry => {
        logContent += `${logEntry}\n`;
    });
    
    const blob = new Blob([logContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-log-${testId}-${new Date().toISOString().slice(0,19)}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Показывает детальный лог теста в модальном окне
 * @param {string} testId - ID теста
 * @param {Array} allTests - Массив всех тестов
 */
function showDetailedLog(testId, allTests) {
    const test = allTests.find(t => t.id === testId);
    const logs = testLogs[testId] || [];
    const result = testResults[testId];
    
    let logContent = `Детальный лог теста: ${test.title}\n`;
    logContent += `Дата: ${new Date().toLocaleString()}\n`;
    logContent += `Статус: ${result ? '✅ ПРОЙДЕН' : '❌ ПРОВАЛЕН'}\n\n`;
    logContent += `Логи выполнения:\n`;
    logContent += `${'='.repeat(50)}\n`;
    
    logs.forEach(logEntry => {
        logContent += `${logEntry}\n`;
    });
    
    // Создаем модальное окно для показа логов
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: center;
    `;
    
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        padding: 20px;
        border-radius: 10px;
        max-width: 80%;
        max-height: 80%;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        white-space: pre-wrap;
    `;
    
    modalContent.textContent = logContent;
    modal.appendChild(modalContent);
    
    // Кнопка закрытия
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '❌ Закрыть';
    closeBtn.style.cssText = `
        position: absolute;
        top: 10px;
        right: 10px;
        background: #dc3545;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 5px;
        cursor: pointer;
    `;
    closeBtn.onclick = () => document.body.removeChild(modal);
    modal.appendChild(closeBtn);
    
    // Кнопка скачивания
    const downloadBtn = document.createElement('button');
    downloadBtn.textContent = '📄 Скачать';
    downloadBtn.style.cssText = `
        position: absolute;
        top: 10px;
        right: 80px;
        background: #17a2b8;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 5px;
        cursor: pointer;
    `;
    downloadBtn.onclick = () => {
        downloadTestLog(testId, allTests);
        document.body.removeChild(modal);
    };
    modal.appendChild(downloadBtn);
    
    document.body.appendChild(modal);
    
    // Закрытие по клику вне модального окна
    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    };
}

/**
 * Экспортирует результаты тестов в Markdown
 * @param {Array} allTests - Массив всех тестов
 * @param {string} title - Заголовок отчета
 * @returns {string} Markdown содержимое
 */
function exportResults(allTests, title = 'Отчет о тестировании') {
    const timestamp = new Date().toISOString().slice(0,19);
    const passed = Object.values(testResults).filter(r => r === true).length;
    const total = allTests.length;
    
    let report = `# ${title}\n`;
    report += `Дата: ${new Date().toLocaleString()}\n`;
    report += `Всего тестов: ${total}\n`;
    report += `Пройдено: ${passed}\n`;
    report += `Провалено: ${total - passed}\n`;
    report += `Успешность: ${((passed/total)*100).toFixed(1)}%\n\n`;
    
    report += `## Детальные результаты:\n\n`;
    
    allTests.forEach(test => {
        const result = testResults[test.id];
        const status = result === true ? '✅ ПРОЙДЕН' : result === false ? '❌ ПРОВАЛЕН' : '⏳ НЕ ВЫПОЛНЕН';
        report += `### ${test.title}\n`;
        report += `- **Статус:** ${status}\n`;
        report += `- **Описание:** ${test.description}\n`;
        report += `- **Категория:** ${test.category}\n\n`;
    });
    
    return report;
}

/**
 * Скачивает отчет о тестировании
 * @param {Array} allTests - Массив всех тестов
 * @param {string} title - Заголовок отчета
 */
function downloadTestReport(allTests, title = 'Отчет о тестировании') {
    const content = exportResults(allTests, title);
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-report-${new Date().toISOString().slice(0,19)}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Проверяет готовность к тестированию
 * @param {Array} requiredFunctions - Массив необходимых функций
 * @returns {boolean} Готовность к тестированию
 */
function checkReadiness(requiredFunctions = []) {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
        console.log('✅ Web Crypto API доступен');
    } else {
        updateStatus('❌ Web Crypto API недоступен', 'error');
        return false;
    }
    
    if (requiredFunctions.length > 0) {
        const missingFunctions = requiredFunctions.filter(fn => typeof window[fn] !== 'function');
        
        if (missingFunctions.length > 0) {
            updateStatus(`❌ Отсутствуют функции: ${missingFunctions.join(', ')}`, 'error');
            return false;
        }
    }
    
    updateStatus('✅ Все функции доступны, готов к тестированию', 'success');
    return true;
}

/**
 * Инициализирует тестовую страницу
 * @param {Array} allTests - Массив всех тестов
 * @param {Array} requiredFunctions - Массив необходимых функций
 */
function initializeTestPage(allTests, requiredFunctions = []) {
    const grid = document.getElementById('testsGrid');
    grid.innerHTML = '';
    
    allTests.forEach(test => {
        grid.innerHTML += createTestCard(test);
    });
    
    updateProgress(allTests.length);
    
    if (checkReadiness(requiredFunctions)) {
        console.log('Тестовая страница инициализирована успешно');
    }
}

// === ЭКСПОРТ ГЛОБАЛЬНЫХ ФУНКЦИЙ ===
window.TestUtils = {
    createTestCard,
    updateTestStatus,
    updateProgress,
    updateStatus,
    clearResults,
    downloadTestLog,
    showDetailedLog,
    exportResults,
    downloadTestReport,
    checkReadiness,
    initializeTestPage,
    // Глобальные переменные
    getTestResults: () => testResults,
    getTestLogs: () => testLogs,
    setTestResults: (results) => { testResults = results; },
    setTestLogs: (logs) => { testLogs = logs; },
    getIsRunning: () => isRunning,
    setIsRunning: (running) => { isRunning = running; }
};

// Дополнительно экспортируем функции напрямую в window для совместимости
window.createTestCard = createTestCard;
window.updateTestStatus = updateTestStatus;
window.updateProgress = updateProgress;
window.updateStatus = updateStatus;
window.clearResults = clearResults;
window.downloadTestLog = downloadTestLog;
window.showDetailedLog = showDetailedLog;
window.downloadTestReport = downloadTestReport;

console.log('✅ TestUtils экспортирован в window.TestUtils и window');
