# Метрики газа: ActivityRegistry (Фаза 4.3)

**Дата:** 2026-01-29  
**Команда:** `REPORT_GAS=true npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`  
**Результат:** 36 passing; газ в разумных пределах.

---

## Порядок величин газа (по плану 4.3)

| Метод | Min | Max | Avg | # calls |
|-------|-----|-----|-----|--------|
| **createActivity** | 146 949 | 181 245 | **172 955** | 27 |
| **activateActivity** | 84 966 | 102 066 | **100 641** | 12 |
| **deactivateActivity** | — | — | **43 737** | 3 |

Дополнительно зафиксированы: forceDeactivate ~45 183; pause ~54 424; unpause ~32 144; setSpiralEngine ~40 242; upgradeToAndCall ~37 454. Деплой Proxy ~262 146; Logic ~1 630 557.

**Проверка по плану:** газ в разумных пределах; createActivity/activate/deactivate — порядок 10⁵ gas, что приемлемо для UUPS Logic с маппингами и массивами.
