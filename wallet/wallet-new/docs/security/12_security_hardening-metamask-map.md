// docs/reference/12_security_hardening-metamask-map.md

# 12_security_hardening — MetaMask reference map

## Что подсматривать
- LavaMoat allowScripts дисциплина.
- Патчи зависимостей как сигнал “где болит”.

## Где искать
- `lavamoat` в package.json и конфиги
- `@lavamoat/react-native-lockdown`
- `allowScripts`
- `patches`/`resolutions`

## Не копировать
- Их конкретный allowScripts список без анализа.
- Их внутренние инструменты сборки.

## Перевод
- Ввести своё правило: запрет postinstall по умолчанию.
- Пинить ключевые крипто/кошелёк зависимости.
- Добавить статические проверки на утечки.