#!/bin/bash

# Скрипт для автоматического деплоя Amanita WebApp на Railway
# Использование: ./deploy.sh [tag]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker не установлен"
        exit 1
    fi
    
    if ! command -v railway &> /dev/null; then
        error "Railway CLI не установлен"
        exit 1
    fi
    
    success "Все зависимости найдены"
}

# Генерация тега
generate_tag() {
    if [ -n "$1" ]; then
        TAG="$1"
    else
        TAG="amanita-webapp-$(date +%Y%m%d-%H%M%S)"
    fi
    log "Используется тег: $TAG"
}

# Сборка Docker образа
build_image() {
    log "Сборка Docker образа..."
    
    docker build \
        --platform linux/amd64 \
        -t "zeya88888888/amanita-webapp:$TAG" \
        -t "zeya88888888/amanita-webapp:latest" \
        .
    
    success "Docker образ собран: zeya88888888/amanita-webapp:$TAG"
}

# Загрузка образа в Docker Hub
push_image() {
    log "Загрузка образа в Docker Hub..."
    
    docker push "zeya88888888/amanita-webapp:$TAG"
    docker push "zeya88888888/amanita-webapp:latest"
    
    success "Образ загружен в Docker Hub"
}

# Настройка Railway
setup_railway() {
    log "Настройка Railway..."
    
    # Проверка подключения к Railway
    if ! railway status &> /dev/null; then
        error "Не подключен к Railway проекту. Выполните: railway login && railway init"
        exit 1
    fi
    
    # Установка переменных
    railway variables --set "RAILWAY_DOCKER_IMAGE=zeya88888888/amanita-webapp:$TAG"
    railway variables --set "NODE_ENV=production"
    railway variables --set "PORT=8080"
    
    success "Railway настроен"
}

# Деплой на Railway
deploy_railway() {
    log "Деплой на Railway..."
    
    railway up
    
    success "Деплой завершен"
}

# Получение URL
get_url() {
    log "Получение URL приложения..."
    
    URL=$(railway domain)
    
    if [ -n "$URL" ]; then
        success "WebApp доступен по адресу: $URL"
        echo ""
        echo "🔗 Ссылки для тестирования:"
        echo "   Основная: $URL"
        echo "   Создание кошелька: $URL?mode=create_new&invite_verified=true"
        echo "   Восстановление: $URL?mode=recovery_only"
        echo "   Healthcheck: $URL/health"
        echo ""
        echo "📱 Для настройки в Telegram Bot используйте URL: $URL"
    else
        warning "Не удалось получить URL. Проверьте статус: railway status"
    fi
}

# Проверка работоспособности
health_check() {
    log "Проверка работоспособности..."
    
    URL=$(railway domain)
    
    if [ -n "$URL" ]; then
        # Ждем запуска сервиса
        sleep 10
        
        # Проверяем healthcheck
        if curl -f -s "$URL/health" > /dev/null; then
            success "Healthcheck прошел успешно"
        else
            warning "Healthcheck не прошел. Проверьте логи: railway logs"
        fi
        
        # Проверяем основную страницу
        if curl -f -s "$URL" > /dev/null; then
            success "Основная страница доступна"
        else
            warning "Основная страница недоступна. Проверьте логи: railway logs"
        fi
    else
        warning "Не удалось проверить работоспособность - URL не получен"
    fi
}

# Показать логи
show_logs() {
    log "Показ последних логов..."
    railway logs --tail 50
}

# Основная функция
main() {
    echo "🚀 Amanita WebApp Deploy Script"
    echo "================================"
    echo ""
    
    check_dependencies
    generate_tag "$1"
    build_image
    push_image
    setup_railway
    deploy_railway
    get_url
    health_check
    
    echo ""
    success "Деплой завершен! 🎉"
    echo ""
    echo "📋 Следующие шаги:"
    echo "1. Настройте WebApp URL в Telegram Bot"
    echo "2. Протестируйте интеграцию"
    echo "3. Проверьте логи при необходимости: railway logs"
    echo ""
}

# Обработка аргументов
case "${1:-}" in
    --help|-h)
        echo "Использование: $0 [tag]"
        echo ""
        echo "Аргументы:"
        echo "  tag    - Тег для Docker образа (по умолчанию: amanita-webapp-YYYYMMDD-HHMMSS)"
        echo ""
        echo "Примеры:"
        echo "  $0                    # Использовать автоматический тег"
        echo "  $0 v1.0.0            # Использовать тег v1.0.0"
        echo "  $0 --help             # Показать эту справку"
        exit 0
        ;;
    --logs)
        show_logs
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac
