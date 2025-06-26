🧩 Onboarding Flow: Telegram Bot — Technical Format
# Шаг 0 — Старт бота /start

Отправляется сообщение:
  - title: onboarding.welcome_title
  - description: onboarding.welcome_description
  - instruction: onboarding.welcome_instruction
  - footer: onboarding.welcome_choose

Кнопки:
  - onboarding.btn_have_invite → переход к шагу 1A
  - onboarding.btn_restore → переход к шагу 1B
# Шаг 1A — Ввод инвайт-кода

Сообщение:
  - text: onboarding.input_invite_label

Ждём текстовое сообщение от пользователя (формат: AMANITA-XXXX-YYYY)

⛔ Валидация:
  - Проверка формата регуляркой: /^AMANITA-\w{4}-\w{4}$/i
  - Проверка валидности кода через внешний API/контракт
    - код существует
    - не использован

Если ❌ ошибка формата:
  - reply: onboarding.invalid_invite
  - show кнопка: onboarding.retry

Если ❌ ошибка валидации NFT:
  - reply: onboarding.invalid_invite
  - show кнопка: onboarding.retry

Если ✅ код принят:
  - message: 
      - onboarding.invite_validated
      - onboarding.invite_validated_instruction
      - onboarding.invite_security_notice
  - кнопка:
      - onboarding.btn_connect → открывает WebApp (кошелёк/доступ)
# Шаг 1B — Повторное подключение (восстановление)

Сообщение:
  - onboarding.restore_intro

Кнопка:
  - onboarding.btn_restore_connect → открывает WebApp (ввод ключа доступа)
WebApp: Создание доступа
Экран 1 — Вступление

Text:
  - onboarding.webapp_intro
  - onboarding.webapp_security_note

Button:
  - onboarding.btn_show_seed → генерация сид-фразы (ключа доступа)
Экран 2 — Показ ключа доступа

Text:
  - onboarding.webapp_seed_header
  - onboarding.webapp_seed_instruction

Действие:
  - Показываются 12 слов (только один раз)

Button:
  - onboarding.btn_seed_saved → переход к установке защиты
Экран 3 — Установка защиты

Text:
  - onboarding.setup_protection_title
  - onboarding.protection_description

Options:
  - onboarding.option_pin
  - onboarding.option_biometrics

UX:
  - проверка PIN (4 цифры)
  - подтверждение биометрии (если есть)
Экран 4 — Завершение

Text:
  - onboarding.final_connected
  - onboarding.final_connected_description

Button:
  - onboarding.btn_return_to_bot → WebApp отправляет данные в бот (в т.ч. адрес)
# Шаг 3 — Завершение онбординга в боте

Сообщение:
  - onboarding.onboarding_complete
  - onboarding.onboarding_complete_summary
  - onboarding.onboarding_reminder

Кнопки:
  - onboarding.btn_catalog
  - onboarding.btn_explore_ecosystem
  - onboarding.btn_my_invites
  - onboarding.btn_access_settings
Главная навигация (после онбординга)

Команда: /menu

Сообщение:
  - onboarding.menu_title

Кнопки:
  - onboarding.menu_catalog
  - onboarding.menu_ecosystem
  - onboarding.menu_invites
  - onboarding.menu_access
  - onboarding.menu_feedback
  - onboarding.menu_exit
Восстановление доступа (в случае потери PIN)

Сообщение:
  - onboarding.recovery_intro

Кнопки:
  - onboarding.btn_enter_phrase → открывает WebApp (ввод ключа)
  - onboarding.btn_create_new_access → создаёт новый вход с новым ключом
❗ Дополнительные UX-механизмы:
🔁 Повторный ввод после ошибки:
Все сценарии ошибок инвайта, PIN, WebApp действий → возвращают пользователя к началу с кнопкой onboarding.retry.

✅ Успешный вход:
После возврата из WebApp при успешном подключении, система:

проверяет наличие адреса

помечает инвайт как использованный (если применим)

регистрирует нового участника экосистемы

❌ Отмена:
На каждом этапе должна быть доступна команда /menu для ручного выхода или перезапуска.