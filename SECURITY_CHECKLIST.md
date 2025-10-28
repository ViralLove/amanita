# ✅ Чеклист безопасности Amanita

## 📊 Текущая ситуация

- ✅ Ключи заменены на новые
- ✅ `.env` в `.gitignore`
- 🔴 **Старые ключи в Git истории** ← КРИТИЧНО!
- 🔴 **Railway Variables вместо Secrets** ← КРИТИЧНО!
- 🟡 Консоль логи с чувствительными данными

---

## 🎯 ПЛАН НЕМЕДЛЕННЫХ ДЕЙСТВИЙ

### Приоритет 1: КРИТИЧНЫЕ (СЕГОДНЯ)

#### ☐ 1. Проверить статус GitHub репозитория

```bash
# Проверить, публичный ли репозиторий
open https://github.com/ViralLove/amanita

# Если публичный → НЕМЕДЛЕННО сделать приватным:
# Settings → Danger Zone → Change visibility → Make private
```

**Если был публичный:**
- 🚨 Боты уже проскранили историю!
- 🚨 Немедленно ротировать ВСЕ ключи
- 🚨 Проверить транзакции на PolygonScan

#### ☐ 2. Очистить Git историю

```bash
# Использовать подготовленный скрипт
chmod +x CLEAN_GIT_HISTORY.sh
./CLEAN_GIT_HISTORY.sh
```

**Или вручную:**
```bash
# Установить BFG
brew install bfg

# Удалить .env из истории
bfg --delete-files .env

# Очистить
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (⚠️ ОПАСНО!)
git push origin --force --all
```

#### ☐ 3. Перенести Railway Variables → Secrets

**Инструкция:** См. `RAILWAY_SECRETS_GUIDE.md`

```bash
# Установить Railway CLI
npm install -g @railway/cli

# Логин
railway login

# Link к проекту
railway link

# Перенести критичные переменные
railway variables set DEPLOYER_PRIVATE_KEY="ВАШ_НОВЫЙ_КЛЮЧ" --secret
railway variables set SELLER_PRIVATE_KEY="ВАШ_НОВЫЙ_КЛЮЧ" --secret
railway variables set TELEGRAM_BOT_TOKEN="ВАШ_ТОКЕН" --secret
```

#### ☐ 4. Ротировать ВСЕ credentials

**Создать новые:**
- [ ] Deployer кошелек (MetaMask)
- [ ] Seller кошелек (MetaMask)
- [ ] Telegram Bot Token (@BotFather → /revoke → /newbot)
- [ ] Pinata API Key (Pinata Dashboard → Regenerate)
- [ ] ArWeave Key (создать новый кошелек)
- [ ] Supabase Service Role Key (если compromised)

**Обновить в:**
- [ ] Railway Secrets
- [ ] Локальный `.env`
- [ ] Hardhat config (если там есть)

---

### Приоритет 2: ВАЖНЫЕ (ЗАВТРА)

#### ☐ 5. Исправить консоль логи

**Найти и исправить:**
```bash
# Найти error.stack
grep -r "error\.stack" --include="*.js" --include="*.ts" bot/ scripts/ wallet/

# Заменить на error.message
# Вместо: console.error("Stack:", error.stack);
# Использовать: console.error("Error:", error.message);
```

**Создать sanitizer:**
```javascript
// utils/logger.js
function sanitizeError(error) {
  return {
    message: error.message,
    name: error.name,
    // НЕ включать stack в production!
  };
}

// Использование:
console.error("Error:", sanitizeError(error));
```

#### ☐ 6. Удалить console.log с чувствительными данными

```bash
# Найти проблемные логи
grep -r "console\.\(log\|error\|debug\)" --include="*.js" \
  | grep -i -E "private|key|secret|password|token"

# Удалить или заменить на безопасные
```

#### ☐ 7. Создать .env.example

```bash
# Переименовать подготовленный шаблон
mv ENV_TEMPLATE.txt .env.example

# Проверить, что нет реальных значений
cat .env.example

# Добавить в Git
git add .env.example
git commit -m "docs: add .env.example template"
```

#### ☐ 8. Настроить мониторинг

**Polygon Transaction Alerts:**
```bash
# Установить @alch/alchemy-sdk
npm install @alch/alchemy-sdk

# Создать monitor.js (см. scripts/monitor_transactions.js)
```

**Railway Logs Monitoring:**
```bash
# Настроить алерты в Railway
# Settings → Notifications → Add webhook
```

---

### Приоритет 3: ДОЛГОСРОЧНЫЕ (НЕДЕЛЯ)

#### ☐ 9. Внедрить Secrets Manager

**Варианты:**
- [ ] HashiCorp Vault (Professional)
- [ ] AWS Secrets Manager
- [ ] GCP Secret Manager
- [ ] Azure Key Vault

#### ☐ 10. Настроить CI/CD с безопасностью

**GitHub Actions:**
```yaml
# .github/workflows/security-check.yml
name: Security Check
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check for secrets
        run: |
          if grep -r "0x[a-fA-F0-9]\{64\}" --exclude-dir=node_modules .; then
            echo "❌ Found potential private keys!"
            exit 1
          fi
```

#### ☐ 11. Security Audit

**Запустить аудит:**
```bash
# npm audit
npm audit

# Slither (Solidity)
pip install slither-analyzer
slither contracts/

# MythX (Solidity)
npm install -g truffle
truffle run verify --network polygon
```

#### ☐ 12. Обучение команды

**Документировать:**
- [ ] Security best practices
- [ ] Incident response plan
- [ ] Code review checklist
- [ ] Deployment procedure

---

## 📋 Чеклист перед каждым деплоем

```bash
# 1. Проверка кода
grep -r "console\.\(log\|error\)" --include="*.js" . | grep -i "private\|key\|secret"

# 2. Проверка .env
cat .env | grep -i "0xac0974"  # Hardhat default key - не должно быть!

# 3. Проверка Git
git status | grep ".env"  # Не должно быть!

# 4. Проверка Railway
railway variables list | grep -i "secret"

# 5. Тест на localhost
npm test

# 6. Деплой
railway up

# 7. Проверка логов
railway logs --follow | grep -i "0x"  # Не должно быть hex ключей!

# 8. Проверка баланса
# Check on PolygonScan
```

---

## 🚨 Incident Response

### Если обнаружена утечка:

1. **Немедленно:**
   - [ ] Вывести все средства с compromised кошельков
   - [ ] Ротировать ВСЕ ключи
   - [ ] Отозвать API tokens

2. **В течение часа:**
   - [ ] Проанализировать логи
   - [ ] Определить вектор атаки
   - [ ] Уведомить пользователей (если нужно)

3. **В течение дня:**
   - [ ] Исправить уязвимость
   - [ ] Обновить документацию
   - [ ] Провести post-mortem

---

## 📊 Метрики безопасности

### Целевые показатели:

- ✅ 0 приватных ключей в Git истории
- ✅ 0 приватных ключей в логах
- ✅ 100% Secrets в Railway Secrets (не Variables)
- ✅ 100% тестового coverage для критичных функций
- ✅ 0 vulnerabilities в npm audit
- ✅ < 1 минута на ротацию ключей

### Текущие показатели:

- 🔴 **Много приватных ключей в Git истории** ← В ПРОЦЕССЕ
- 🟡 20+ error.stack в коде
- 🔴 Все в Railway Variables
- 🟢 Тесты есть
- 🟢 .env в .gitignore

---

## 📞 Контакты для экстренных случаев

- Railway Support: https://railway.app/help
- GitHub Support: https://support.github.com/
- Polygon Support: https://forum.polygon.technology/

---

**Дата последнего обновления:** 10.10.2025  
**Следующий review:** После выполнения всех пунктов Приоритет 1


