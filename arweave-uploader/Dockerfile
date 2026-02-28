# arweave-uploader — Node ESM, GET /health, POST /v1/crystalize
# Railway: PORT из env, healthcheckPath /health

FROM node:20-alpine

WORKDIR /app

# Зависимости (package.json + lock если есть)
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

# Код приложения
COPY dist ./dist

# Порт задаётся Railway через PORT
ENV PORT=3000
EXPOSE 3000

USER node
CMD ["node", "dist/server.js"]
