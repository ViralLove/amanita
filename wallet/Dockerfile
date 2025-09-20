# Multi-stage build для оптимизации размера образа
FROM nginx:alpine AS base

# Установка необходимых пакетов
RUN apk add --no-cache \
    curl \
    && rm -rf /var/cache/apk/*

# Используем существующего пользователя nginx из базового образа
# Проверяем, что пользователь nginx существует
RUN id nginx

# Копирование конфигурации Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Создание директорий для статических файлов
RUN mkdir -p /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /run

# Копирование файлов приложения в nginx html директорию
COPY --chown=nginx:nginx index.html /usr/share/nginx/html/
COPY --chown=nginx:nginx main.js /usr/share/nginx/html/
COPY --chown=nginx:nginx styles.css /usr/share/nginx/html/
COPY --chown=nginx:nginx localization/ /usr/share/nginx/html/localization/
COPY --chown=nginx:nginx assets/ /usr/share/nginx/html/assets/

# Создание конфигурационного файла с переменными окружения
RUN echo 'window.RAILWAY_ENV = { \
  DEBUG_MODE: "${DEBUG_MODE:-false}", \
  NODE_ENV: "${NODE_ENV:-production}" \
};' > /usr/share/nginx/html/config.js

# Переключение на пользователя nginx
USER nginx

# Экспорт порта
EXPOSE 8080

# Healthcheck для Railway
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Запуск Nginx
CMD ["nginx", "-g", "daemon off;"]
