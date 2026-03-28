# Fixtures для интеграционных тестов upload (full cycle)

Для теста полного цикла с реальным arweave-uploader (маркер `real_arweave_uploader`) нужен подписанный Arweave Data Item в base64.

**По умолчанию** тест ищет файл:

- `full_cycle_signed_data_item.b64` — одна строка: base64 подписанного Data Item.

Положите сюда сгенерированный файл или задайте путь через env `FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64_FILE`, либо (устаревший вариант) переменную `FULL_CYCLE_TEST_SIGNED_DATA_ITEM_B64` в .env.

Подробнее: [data-upload-integration-tests.md](../../../docs/tests/data-upload-integration-tests.md).
