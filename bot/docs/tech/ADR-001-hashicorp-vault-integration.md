# ADR-001: HashiCorp Vault Integration for Production Key Management

**Status**: Accepted  
**Date**: 2025-10-10  
**Author**: eslinko  
**Deciders**: eslinko, AI Assistant (Claude Sonnet 4.5)

## Context

### Problem Statement

Amanita bot использует приватные ключи для взаимодействия с Polygon blockchain (SELLER_PRIVATE_KEY, DEPLOYER_PRIVATE_KEY) и ArWeave (ARWEAVE_PRIVATE_KEY). **Дважды** произошла компрометация ключей, несмотря на попытки исправления:

1. **Первый инцидент**: Приватные ключи попали в логи Railway через `console.log` и `error.stack`
2. **Второй инцидент**: Повторное опустошение адресов deployer и seller на Polygon

### Current State (Before ADR-001)

```python
# bot/config.py
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY")

# bot/services/core/blockchain.py
self.seller_key = SELLER_PRIVATE_KEY
self.seller_account = Account.from_key(SELLER_PRIVATE_KEY)
```

**Проблемы текущего подхода**:
- ❌ Ключи хранятся в Railway Variables (защита только от UI просмотра)
- ❌ Легко утекают в логи при ошибках (`error.stack`, `console.log`)
- ❌ Нет audit trail для доступа к ключам
- ❌ Невозможность rotation без редеплоя
- ❌ Нет централизованного управления секретами

### Requirements

**Functional Requirements**:
- FR1: Защита production ключей (Polygon profile) от утечек в логах
- FR2: Audit trail всех обращений к ключам
- FR3: Возможность rotation ключей без редеплоя
- FR4: Сохранение простоты для localhost development

**Non-Functional Requirements**:
- NFR1: Latency < 500ms для получения ключа
- NFR2: Backward compatibility с localhost .env workflow
- NFR3: Прозрачность для существующих сервисов (blockchain.py, ar_weave.py)
- NFR4: Graceful degradation при недоступности Vault

## Decision

Интегрировать **HashiCorp Vault** для хранения production ключей с **profile-based configuration**:

- **Polygon profile** (production) → ключи из Vault
- **Localhost profile** (development) → ключи из .env file

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         bot/config.py                       │
│                                                             │
│  if DEPLOYMENT_PROFILE == "polygon":                        │
│      vault = VaultService(VAULT_ADDR, VAULT_TOKEN)          │
│      SELLER_PRIVATE_KEY = vault.get_secret("SELLER_KEY")    │
│      ARWEAVE_PRIVATE_KEY = vault.get_secret("ARWEAVE_KEY")  │
│  else:  # localhost                                         │
│      SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")   │
│      ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY") │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ (import)
                              ▼
        ┌──────────────────────────────────────────┐
        │     bot/services/core/blockchain.py      │
        │                                          │
        │  self.seller_key = SELLER_PRIVATE_KEY    │
        │  # (прозрачно, не знает об источнике)    │
        └──────────────────────────────────────────┘
```

### Implementation Details

**Phase 1**: Create VaultService
```python
# bot/services/vault_service.py
class VaultService:
    def __init__(self, vault_addr: str, vault_token: str):
        self.client = hvac.Client(url=vault_addr, token=vault_token)
    
    def get_secret(self, secret_key: str, vault_path: str = "secret/data/amanita") -> str:
        response = self.client.secrets.kv.v2.read_secret_version(path=vault_path)
        return response['data']['data'][secret_key]
```

**Phase 2**: Modify config.py
```python
# bot/config.py
DEPLOYMENT_PROFILE = os.getenv("DEPLOYMENT_PROFILE", "localhost")

if DEPLOYMENT_PROFILE == "polygon":
    vault = VaultService(
        vault_addr=os.getenv("VAULT_ADDR"),
        vault_token=os.getenv("VAULT_TOKEN")
    )
    SELLER_PRIVATE_KEY = vault.get_secret("SELLER_PRIVATE_KEY")
    ARWEAVE_PRIVATE_KEY = vault.get_secret("ARWEAVE_PRIVATE_KEY")
else:
    SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
    ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY")
```

**Phase 3**: Railway Configuration
```bash
# Railway Variables (только для polygon deployments)
DEPLOYMENT_PROFILE=polygon
VAULT_ADDR=https://vault.example.com:8200
VAULT_TOKEN=s.xxxxxxxxxxxxxxxxxxxxxx
VAULT_PATH=secret/data/amanita

# Удалить из Railway:
# SELLER_PRIVATE_KEY  ← переместить в Vault
# ARWEAVE_PRIVATE_KEY ← переместить в Vault
```

**Phase 4**: Vault Setup
```bash
# В HashiCorp Vault UI или CLI
vault kv put secret/amanita \
  SELLER_PRIVATE_KEY="0x..." \
  ARWEAVE_PRIVATE_KEY="..." \
  DEPLOYER_PRIVATE_KEY="0x..."
```

## Alternatives Considered

### Alternative 1: Keep in Railway Variables + Fix Code (Minimum Effort)

**Pros**:
- ✅ Нет новых зависимостей
- ✅ Нулевая latency
- ✅ Простота

**Cons**:
- ❌ Ключи все еще в Railway Variables (доступны через Railway API)
- ❌ Нет audit trail
- ❌ Human error risk (случайный `console.log`)
- ❌ Невозможность rotation без редеплоя

**Decision**: Отклонено из-за повторных компрометаций. Недостаточно надежно для production.

### Alternative 2: AWS Secrets Manager

**Pros**:
- ✅ Managed service
- ✅ Интеграция с AWS экосистемой
- ✅ Автоматическая rotation

**Cons**:
- ❌ Vendor lock-in (AWS)
- ❌ Стоимость (~$0.40/secret/month + API calls)
- ❌ Требует AWS аккаунт
- ❌ Overkill для текущего масштаба

**Decision**: Отклонено из-за vendor lock-in и стоимости.

### Alternative 3: HashiCorp Vault (Chosen)

**Pros**:
- ✅ Platform-agnostic
- ✅ Отличный audit trail
- ✅ Free tier (HCP Vault)
- ✅ Пользователь уже настраивает аккаунт
- ✅ Гибкость (можно мигрировать на self-hosted)
- ✅ Industry standard для secrets management

**Cons**:
- ⚠️ Дополнительная зависимость (external service)
- ⚠️ Latency (~50-200ms для HTTP request)
- ⚠️ Single point of failure (mitigation: caching, fallback)

**Decision**: ✅ **Принято**. Оптимальный баланс безопасности, гибкости и стоимости.

### Alternative 4: Hardware Security Module (HSM)

**Pros**:
- ✅ Максимальная безопасность
- ✅ Compliance-ready (FIPS 140-2)

**Cons**:
- ❌ Очень дорого ($1000-10000/month)
- ❌ Сложная настройка
- ❌ Overkill для текущего масштаба

**Decision**: Отклонено из-за стоимости и сложности.

## Risks and Mitigation

### Risk 1: Vault Unavailability
**Impact**: High (bot не может подписывать транзакции)  
**Probability**: Low (HCP Vault SLA 99.95%)  
**Mitigation**:
- Использовать HCP Vault (managed) вместо self-hosted
- Мониторинг доступности Vault (healthcheck)
- Future: Local encrypted cache с TTL (Phase 5)

### Risk 2: Invalid Vault Token
**Impact**: High (bot не запустится)  
**Probability**: Medium (token rotation, ошибка конфигурации)  
**Mitigation**:
- Validation при старте бота (fail-fast)
- Clear error messages с инструкциями
- Alert в Telegram при старте с проблемами

### Risk 3: Latency Impact
**Impact**: Low (добавляет 50-200ms к операциям с ключами)  
**Probability**: High (каждый запрос к Vault)  
**Mitigation**:
- Ключи загружаются 1 раз при старте бота (не на каждую транзакцию)
- Future: In-memory cache с refresh (Phase 5)

### Risk 4: Localhost Breakage
**Impact**: Medium (developer experience)  
**Probability**: Low (explicit conditional logic)  
**Mitigation**:
- Явная проверка `DEPLOYMENT_PROFILE`
- Localhost использует старый .env workflow
- Backward compatibility test перед deploy

### Risk 5: Git History Leak (Existing Keys)
**Impact**: Critical (старые ключи уже в Git history)  
**Probability**: Certain (уже произошло)  
**Mitigation**:
- ✅ Пользователь уже заменил ключи
- 🔜 Очистка Git history (CLEAN_GIT_HISTORY.sh)
- 🔜 Pre-commit hook (detect-secrets)

## Validation Strategy

### Acceptance Criteria

**AC1**: Bot запускается с `DEPLOYMENT_PROFILE=polygon` и загружает ключи из Vault
```bash
DEPLOYMENT_PROFILE=polygon VAULT_ADDR=... VAULT_TOKEN=... python bot/main.py
# Expected: "VaultService initialized successfully"
# Expected: "Seller address: 0x..." (loaded from Vault)
```

**AC2**: Bot запускается с `DEPLOYMENT_PROFILE=localhost` и загружает ключи из .env
```bash
DEPLOYMENT_PROFILE=localhost python bot/main.py
# Expected: "Using local .env configuration"
# Expected: "Seller address: 0x..." (loaded from .env)
```

**AC3**: Ключи не появляются в логах при ошибках
```python
# Test: намеренно вызвать ошибку в blockchain.py
# Expected: error.message содержит описание, но НЕ содержит private keys
```

**AC4**: Audit trail в Vault показывает обращения к секретам
```bash
# В Vault UI → Audit Logs
# Expected: запись "read secret/data/amanita" с timestamp и IP
```

### Rollback Plan

Если интеграция Vault провалится в production:

**Step 1**: Немедленный rollback конфигурации
```bash
# В Railway Variables
DEPLOYMENT_PROFILE=localhost
SELLER_PRIVATE_KEY=0x...  # вернуть ключ в Railway Variables
```

**Step 2**: Revert code changes
```bash
git revert <commit-hash-of-vault-integration>
git push
```

**Step 3**: Проверка восстановления
```bash
# Убедиться что bot работает с .env configuration
railway logs
```

**Recovery Time Objective (RTO)**: < 10 минут  
**Recovery Point Objective (RPO)**: 0 (stateless bot)

## Consequences

### Positive

- ✅ **Security**: Ключи не хранятся в Railway Variables
- ✅ **Auditability**: Полный audit trail обращений к ключам
- ✅ **Rotation**: Можно менять ключи в Vault без редеплоя
- ✅ **Centralization**: Единая точка управления секретами
- ✅ **Compliance**: Industry-standard secrets management
- ✅ **Developer Experience**: Localhost workflow не изменился

### Negative

- ⚠️ **Complexity**: Дополнительный external service
- ⚠️ **Dependency**: Зависимость от доступности Vault
- ⚠️ **Latency**: +50-200ms при загрузке ключей (только при старте)
- ⚠️ **Learning Curve**: Команда должна знать Vault basics

### Neutral

- 🔄 **Migration Effort**: ~4 часа работы (4 фазы implementation)
- 🔄 **Maintenance**: Периодическая rotation Vault token (~раз в месяц)

## Implementation Timeline

**Phase 1**: Create vault_service.py (1 hour)
- [ ] Создать `bot/services/vault_service.py`
- [ ] Написать unit tests для VaultService
- [ ] Добавить `hvac` в requirements.txt

**Phase 2**: Modify config.py (1 hour)
- [ ] Добавить profile-based configuration
- [ ] Добавить validation и error handling
- [ ] Обновить документацию в docstrings

**Phase 3**: Railway Configuration (30 minutes)
- [ ] Добавить VAULT_* переменные в Railway
- [ ] Удалить SELLER_PRIVATE_KEY из Railway
- [ ] Изменить DEPLOYMENT_PROFILE на polygon

**Phase 4**: Vault Setup (1.5 hours)
- [ ] Создать namespace в HCP Vault
- [ ] Загрузить ключи в secret/amanita
- [ ] Настроить access policy
- [ ] Проверить connectivity с Railway

**Total Estimated Effort**: ~4 hours

## Success Metrics

**Short-term (1 week)**:
- ✅ Bot работает на production с Vault
- ✅ Ключи успешно загружаются при каждом старте
- ✅ 0 ошибок связанных с Vault
- ✅ Audit logs показывают обращения к секретам

**Medium-term (1 month)**:
- ✅ 0 утечек ключей в логах
- ✅ 0 компрометаций адресов
- ✅ Latency < 500ms при старте бота
- ✅ Developer workflow для localhost остался прежним

**Long-term (3 months)**:
- ✅ Vault audit trail используется для security reviews
- ✅ Key rotation проведена минимум 1 раз без проблем
- ✅ Команда комфортно работает с Vault

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [HCP Vault Free Tier](https://cloud.hashicorp.com/products/vault)
- [HVAC Python Client](https://hvac.readthedocs.io/)
- [SECURITY-AUDIT-2025-10-09.md](../SECURITY-AUDIT-2025-10-09.md)
- [AIJournal.md - Vault Integration Analysis](../bot/docs/AIJournal.md)
- [meta.extract.vault-security-integration.20251010T143000Z.mdc](../../meta/meta.extract.vault-security-integration.20251010T143000Z.mdc)

## Approval

**Decision Date**: 2025-10-10  
**Approved by**: eslinko  
**Implementation Start**: 2025-10-10  
**Expected Completion**: 2025-10-11

---

**ADR Status**: ✅ **ACCEPTED**

**Next Action**: Begin Phase 1 - Create `bot/services/vault_service.py`

