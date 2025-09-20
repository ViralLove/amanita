/**
 * Универсальный тестовый фреймворк для браузера
 * 
 * Использование:
 * 1. Подключите этот файл в HTML
 * 2. Создайте тесты используя TestFramework
 * 3. Запустите через runAllTests() или runSingleTest()
 */

class TestFramework {
    constructor() {
        this.tests = [];
        this.results = {};
        this.logs = {};
        this.isRunning = false;
    }

    /**
     * Добавить тест в набор
     * @param {Object} testConfig - Конфигурация теста
     * @param {string} testConfig.id - Уникальный ID теста
     * @param {string} testConfig.name - Имя функции теста
     * @param {string} testConfig.title - Отображаемое название
     * @param {string} testConfig.description - Описание теста
     * @param {string} testConfig.category - Категория теста
     * @param {Function} testConfig.fn - Функция теста (async)
     */
    addTest(testConfig) {
        this.tests.push({
            id: testConfig.id,
            name: testConfig.name,
            title: testConfig.title,
            description: testConfig.description,
            category: testConfig.category,
            fn: testConfig.fn
        });
    }

    /**
     * Запустить все тесты
     * @param {Function} onProgress - Callback для обновления прогресса
     * @param {Function} onTestComplete - Callback при завершении теста
     */
    async runAllTests(onProgress = null, onTestComplete = null) {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.results = {};
        this.logs = {};
        
        for (const test of this.tests) {
            await this.runSingleTest(test, onProgress, onTestComplete);
        }
        
        this.isRunning = false;
        return this.getSummary();
    }

    /**
     * Запустить один тест
     * @param {Object} test - Объект теста
     * @param {Function} onProgress - Callback для обновления прогресса
     * @param {Function} onTestComplete - Callback при завершении теста
     */
    async runSingleTest(test, onProgress = null, onTestComplete = null) {
        this.logs[test.id] = [];
        
        try {
            // Перехватываем console.log для логирования
            const originalConsoleLog = console.log;
            const originalConsoleError = console.error;
            
            console.log = (...args) => {
                const message = args.join(' ');
                this.logs[test.id].push(`[LOG] ${message}`);
                originalConsoleLog.apply(console, args);
            };
            
            console.error = (...args) => {
                const message = args.join(' ');
                this.logs[test.id].push(`[ERROR] ${message}`);
                originalConsoleError.apply(console, args);
            };
            
            // Запускаем тест
            const result = await test.fn();
            
            // Восстанавливаем оригинальные функции
            console.log = originalConsoleLog;
            console.error = originalConsoleError;
            
            this.results[test.id] = result;
            
            if (onTestComplete) {
                onTestComplete(test, result, this.logs[test.id]);
            }
            
        } catch (error) {
            this.results[test.id] = false;
            this.logs[test.id].push(`[EXCEPTION] ${error.message}`);
            this.logs[test.id].push(`[STACK] ${error.stack}`);
            
            if (onTestComplete) {
                onTestComplete(test, false, this.logs[test.id], error);
            }
        }
        
        if (onProgress) {
            onProgress(this.getProgress());
        }
    }

    /**
     * Получить прогресс выполнения
     */
    getProgress() {
        const total = this.tests.length;
        const completed = Object.keys(this.results).length;
        const passed = Object.values(this.results).filter(r => r === true).length;
        const failed = Object.values(this.results).filter(r => r === false).length;
        
        return {
            total,
            completed,
            passed,
            failed,
            percentage: (completed / total) * 100
        };
    }

    /**
     * Получить сводку результатов
     */
    getSummary() {
        const progress = this.getProgress();
        return {
            ...progress,
            results: this.results,
            logs: this.logs,
            success: progress.failed === 0
        };
    }

    /**
     * Получить детальный лог теста
     * @param {string} testId - ID теста
     */
    getTestLog(testId) {
        const test = this.tests.find(t => t.id === testId);
        const logs = this.logs[testId] || [];
        const result = this.results[testId];
        
        return {
            test,
            result,
            logs,
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Экспортировать результаты в Markdown
     */
    exportToMarkdown() {
        const summary = this.getSummary();
        const timestamp = new Date().toISOString().slice(0,19);
        
        let content = `# Отчет о тестировании\n`;
        content += `Дата: ${new Date().toLocaleString()}\n`;
        content += `Всего тестов: ${summary.total}\n`;
        content += `Пройдено: ${summary.passed}\n`;
        content += `Провалено: ${summary.failed}\n`;
        content += `Успешность: ${summary.percentage.toFixed(1)}%\n\n`;
        
        content += `## Детальные результаты:\n\n`;
        
        this.tests.forEach(test => {
            const result = this.results[test.id];
            const status = result === true ? '✅ ПРОЙДЕН' : result === false ? '❌ ПРОВАЛЕН' : '⏳ НЕ ВЫПОЛНЕН';
            content += `### ${test.title}\n`;
            content += `- **Статус:** ${status}\n`;
            content += `- **Описание:** ${test.description}\n`;
            content += `- **Категория:** ${test.category}\n\n`;
        });
        
        return content;
    }

    /**
     * Очистить результаты
     */
    clear() {
        this.results = {};
        this.logs = {};
        this.isRunning = false;
    }
}

// Создаем глобальный экземпляр фреймворка
window.TestFramework = TestFramework;
window.testFramework = new TestFramework();

// Утилиты для работы с тестами
window.addTest = (config) => window.testFramework.addTest(config);
window.runAllTests = () => window.testFramework.runAllTests();
window.runSingleTest = (testId) => {
    const test = window.testFramework.tests.find(t => t.id === testId);
    if (test) {
        return window.testFramework.runSingleTest(test);
    }
    throw new Error(`Тест с ID ${testId} не найден`);
};
window.getTestLog = (testId) => window.testFramework.getTestLog(testId);
window.exportResults = () => window.testFramework.exportToMarkdown();
