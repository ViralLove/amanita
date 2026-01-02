#!/usr/bin/env python3
"""
Реюзабельный скрипт для форматирования описаний всех продуктов в CSV
согласно структуре из data/docs/product-formatting-reference.md.

Особенности:
- Обрабатывает все строки с валидными SKU, Description, meta:business_id
- Форматирует описание, объединяет списки, сохраняет в CSV
- Создаёт/обновляет html_description.html в папке продукта
- Логирует прогресс, пропуски и ошибки
"""

import csv
import re
import shutil
from pathlib import Path
from typing import List, Tuple


def format_description_section(section_text: str) -> str:
    """
    Форматирует секцию описания согласно референсу.
    Объединяет последовательные <ul><li>...</li></ul> блоки в один <ul> блок.
    """
    # Сначала защищаем <strong>Важно:</strong> от преобразования
    section_text = re.sub(r"<strong>Важно:</strong>", "__IMPORTANT_MARKER__", section_text)

    # Затем обрабатываем все остальные <strong>text:</strong> в h2
    section_text = re.sub(r"<strong>([^<]+):</strong>", r"<h2>\1</h2>", section_text)

    # Возвращаем <strong>Важно:</strong> обратно
    section_text = section_text.replace("__IMPORTANT_MARKER__", "<strong>Важно:</strong>")

    # Исправляем случай, если <h2>Важно</h2> все же был создан
    section_text = re.sub(r"<h2>Важно</h2>", "<strong>Важно:</strong>", section_text)

    # Теперь объединяем списки между h2 заголовками
    lines = section_text.split("\n")
    result_lines: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Если это h2 заголовок
        if stripped.startswith("<h2>"):
            result_lines.append(line)
            i += 1

            # Собираем все последовательные <ul><li>...</li></ul> блоки до следующего заголовка
            list_items: List[str] = []
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()

                # Останавливаемся на следующем заголовке или <strong>Важно:</strong>
                if (
                    next_stripped.startswith("<h2>")
                    or next_stripped.startswith("<h1>")
                    or next_stripped.startswith("<strong>Важно:")
                ):
                    break

                # Если это <ul>, собираем его содержимое
                if next_stripped == "<ul>":
                    i += 1
                    # Ищем <li> внутри этого <ul>
                    while i < len(lines):
                        li_line = lines[i]
                        li_stripped = li_line.strip()

                        if li_stripped == "</ul>":
                            i += 1
                            break
                        elif li_stripped.startswith("<li>"):
                            # Извлекаем содержимое <li>
                            content = re.sub(r"^<li>", "", li_stripped)
                            content = re.sub(r"</li>.*$", "", content)
                            # Удаляем эмодзи 🔹 если есть
                            content = re.sub(r"^\s*🔹\s*", "", content)
                            list_items.append(f"<li>{content}</li>")
                        i += 1
                elif not next_stripped:
                    # Пустая строка - пропускаем
                    i += 1
                else:
                    # Не список, останавливаемся
                    break

            # Если собрали элементы списка, добавляем их как один <ul> блок
            if list_items:
                result_lines.append("<ul>")
                result_lines.extend([f"\t{item}" for item in list_items])
                result_lines.append("</ul>")

        # Если это <strong>Важно:</strong> - оставляем как есть
        elif stripped.startswith("<strong>Важно:"):
            # Удаляем лишние теги </p> если есть, но сохраняем текст после <strong>Важно:</strong>
            match = re.search(r"<strong>Важно:</strong>\s*(.+)", stripped)
            if match:
                important_text = match.group(1)
                # Удаляем </p> из конца
                important_text = re.sub(r"</p>.*$", "", important_text)
                result_lines.append(f"<strong>Важно:</strong> {important_text}")
            else:
                cleaned = re.sub(r"</p>.*$", "", stripped)
                result_lines.append(cleaned)
            i += 1
        # Если это h2 Важно - преобразуем обратно в <strong>Важно:</strong>
        elif stripped == "<h2>Важно</h2>":
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = re.sub(r"</p>.*$", "", next_line.strip())
                result_lines.append(f"<strong>Важно:</strong> {next_stripped}")
                i += 2
            else:
                result_lines.append("<strong>Важно:</strong>")
                i += 1
        # Обычный текст (не в списке и не заголовок)
        else:
            if stripped:
                # Удаляем лишние теги <p> и <br>
                cleaned = re.sub(r"</?p>", "", stripped)
                cleaned = re.sub(r"<br>", "", cleaned)
                # Удаляем закрывающие </p> в конце
                cleaned = re.sub(r"</p>.*$", "", cleaned)
                if cleaned.strip():
                    result_lines.append(cleaned)
            i += 1

    return "\n".join(result_lines)


def format_full_description(description: str) -> str:
    """
    Форматирует полное описание продукта.
    """
    # Находим границы секций
    desc_start = description.find("<h3>Описание</h3>")
    effects_start = description.find("<h3>Эффекты</h3>")
    shamanic_start = description.find("<h3>Шаманская перспектива</h3>")
    warnings_start = description.find("<h3>Предупреждения</h3>")

    # Сохраняем основную информацию (до секции Описание)
    main_info = description[:desc_start].rstrip() if desc_start >= 0 else description

    result_parts: List[str] = [main_info]

    # Обрабатываем секцию Описание
    if desc_start >= 0:
        desc_end = (
            effects_start
            if effects_start >= 0
            else (shamanic_start if shamanic_start >= 0 else (warnings_start if warnings_start >= 0 else len(description)))
        )
        desc_section = description[desc_start:desc_end]

        # Удаляем <h3>Описание</h3>
        desc_section = desc_section.replace("<h3>Описание</h3>", "")

        # Удаляем префикс <p><strong>component_id:</strong><br>🔬 Активные компоненты:
        desc_section = re.sub(r"<p><strong>[^<]+:</strong><br>🔬 Активные компоненты:\s*", "", desc_section)

        # Форматируем секцию
        formatted_desc = format_description_section(desc_section)
        result_parts.append("<h1>🔬 Активные компоненты</h1>")
        result_parts.append(formatted_desc)

    # Обрабатываем секцию Эффекты
    if effects_start >= 0:
        effects_end = shamanic_start if shamanic_start >= 0 else (warnings_start if warnings_start >= 0 else len(description))
        effects_section = description[effects_start:effects_end]

        # Удаляем <h3>Эффекты</h3>
        effects_section = effects_section.replace("<h3>Эффекты</h3>", "")

        # Удаляем префикс <p><strong>component_id:</strong><br>🌿 Целительное действие:
        effects_section = re.sub(r"<p><strong>[^<]+:</strong><br>🌿 Целительное действие:\s*", "", effects_section)

        # Форматируем секцию
        formatted_effects = format_description_section(effects_section)
        result_parts.append("<h1>🌿 Целительное действие</h1>")
        result_parts.append(formatted_effects)

    # Обрабатываем секцию Шаманская перспектива
    if shamanic_start >= 0:
        shamanic_end = warnings_start if warnings_start >= 0 else len(description)
        shamanic_section = description[shamanic_start:shamanic_end]

        # Удаляем <h3>Шаманская перспектива</h3>
        shamanic_section = shamanic_section.replace("<h3>Шаманская перспектива</h3>", "")

        # Удаляем префикс <p><strong>component_id:</strong><br>🌀 Шаманская перспектива:
        shamanic_section = re.sub(r"<p><strong>[^<]+:</strong><br>🌀 Шаманская перспектива:\s*", "", shamanic_section)

        # Форматируем секцию
        formatted_shamanic = format_description_section(shamanic_section)
        result_parts.append("<h1>Шаманская перспектива</h1>")
        result_parts.append(formatted_shamanic)

    # Обрабатываем секцию Предупреждения
    if warnings_start >= 0:
        warnings_section = description[warnings_start:]

        # Удаляем <h3>Предупреждения</h3>
        warnings_section = warnings_section.replace("<h3>Предупреждения</h3>", "")

        # Удаляем префикс <p><strong>component_id:</strong><br>⚠️ Предостережения:
        warnings_section = re.sub(r"<p><strong>[^<]+:</strong><br>⚠️ Предостережения:\s*", "", warnings_section)

        # Форматируем секцию
        formatted_warnings = format_description_section(warnings_section)
        result_parts.append("<h1>Предупреждения</h1>")
        result_parts.append(formatted_warnings)

    return "\n".join(result_parts)


def validate_formatted_html(html_content: str) -> Tuple[bool, List[str]]:
    """
    Валидирует отформатированный HTML.
    Returns: (is_valid, errors)
    """
    errors: List[str] = []
    required_sections = [
        "<h1>🔬 Активные компоненты</h1>",
        "<h1>🌿 Целительное действие</h1>",
        "<h1>Шаманская перспектива</h1>",
        "<h1>Предупреждения</h1>",
    ]

    for section in required_sections:
        if section not in html_content:
            errors.append(f"Отсутствует секция: {section}")

    # Проверка структуры списков
    ul_count = html_content.count("<ul>")
    ul_close_count = html_content.count("</ul>")
    if ul_count != ul_close_count:
        errors.append(f"Несоответствие тегов <ul>: открывающих {ul_count}, закрывающих {ul_close_count}")

    return len(errors) == 0, errors


def process_row(row: dict, row_num: int) -> Tuple[dict, str, List[str]]:
    """
    Обрабатывает одну строку CSV.
    Returns: (row, component_description, warnings)
    """
    warnings: List[str] = []
    sku = row.get("SKU", "").strip()
    if not sku:
        warnings.append(f"⚠️ Строка {row_num}: пропущена (нет SKU)")
        return row, "", warnings

    description = row.get("Description", "").strip()
    if not description:
        warnings.append(f"⚠️ Продукт {sku}: пропущен (нет описания)")
        return row, "", warnings

    business_id = row.get("meta:business_id", "").strip()
    if not business_id:
        warnings.append(f"⚠️ Продукт {sku}: пропущен (нет business_id)")
        return row, "", warnings

    formatted_desc = format_full_description(description)
    row["Description"] = formatted_desc

    # Извлекаем только секции описания компонентов (без основной информации)
    desc_start = formatted_desc.find("<h1>🔬 Активные компоненты</h1>")
    component_description = formatted_desc[desc_start:] if desc_start >= 0 else formatted_desc

    return row, component_description, warnings


def backup_csv(csv_path: Path) -> Path:
    """Создает резервную копию CSV."""
    backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
    shutil.copyfile(csv_path, backup_path)
    return backup_path


def main():
    csv_path = Path("bot/woocommerce_products.fixed.csv")
    if not csv_path.exists():
        print(f"❌ Файл не найден: {csv_path}")
        return

    # Резервная копия
    backup_path = backup_csv(csv_path)
    print(f"🛟 Backup создан: {backup_path}")

    rows_out: List[dict] = []
    processed_count = 0
    skipped_count = 0
    error_count = 0
    total_rows = 0

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("❌ Пустой CSV или нет заголовков")
            return

        for row_num, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                updated_row, component_description, warns = process_row(row, row_num)
                if warns:
                    skipped_count += 1
                    for w in warns:
                        print(w)
                    rows_out.append(row)  # сохраняем оригинал без изменений
                    continue

                # Валидация результата
                is_valid, errors = validate_formatted_html(updated_row["Description"])
                if not is_valid:
                    error_count += 1
                    print(f"❌ Валидация {updated_row.get('SKU','')}: {errors}")
                    rows_out.append(row)  # сохраняем оригинал
                    continue

                # Сохранение HTML файла
                business_id = updated_row["meta:business_id"].strip()
                output_dir = Path(f"data/sellers/iveta/products/{business_id}")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / "html_description.html"
                with open(output_file, "w", encoding="utf-8") as out_f:
                    out_f.write(component_description)

                processed_count += 1
                print(f"✅ [{processed_count}/{total_rows}] {updated_row['SKU']} → {business_id}")
                rows_out.append(updated_row)
            except Exception as e:
                error_count += 1
                print(f"❌ Ошибка обработки строки {row_num} ({row.get('SKU','')}): {e}")
                rows_out.append(row)  # сохраняем оригинал

    # Сохранение обновленного CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    # Итоговая статистика
    print("\n📊 Итоги:")
    print(f"   ✅ Обработано: {processed_count}")
    print(f"   ⚠️ Пропущено: {skipped_count}")
    print(f"   ❌ Ошибок: {error_count}")
    print(f"   📄 Всего строк: {total_rows}")
    print(f"✅ CSV файл обновлен: {csv_path}")


if __name__ == "__main__":
    main()

