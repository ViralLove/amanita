#!/usr/bin/env python3
"""
Скрипт для преобразования описания продукта к структуре из product-formatting-reference.md

Преобразования:
1. <h3>Описание</h3> → <h1>🔬 Активные компоненты</h1>
2. <h3>Эффекты</h3> → <h1>🌿 Целительное действие</h1>
3. <h3>Шаманская перспектива</h3> → <h1>Шаманская перспектива</h1>
4. <h3>Предупреждения</h3> → <h1>Предупреждения</h1>
5. Конвертация markdown **text** → <strong>text</strong>
6. Группировка списков в один <ul> для каждой подсекции
7. Удаление эмодзи 🔹 из списков
8. Преобразование <strong>text:</strong> в h2 заголовки
9. Удаление префикса <strong>component_id:</strong><br> из начала секций
"""

import re
from typing import List, Tuple


def convert_markdown_to_html(text: str) -> str:
    """Конвертирует markdown **text** в HTML <strong>text</strong>"""
    pattern = r'\*\*(.+?)\*\*'
    replacement = r'<strong>\1</strong>'
    return re.sub(pattern, replacement, text)


def remove_component_prefix(text: str) -> str:
    """Удаляет префикс <strong>component_id:</strong><br> из начала текста"""
    # Паттерн: <strong>component_id:</strong><br> или <strong>component_id:</strong><br>
    pattern = r'<strong>[^<]+:</strong><br>\s*'
    text = re.sub(pattern, '', text, count=1)
    return text


def group_lists_in_section(text: str) -> str:
    """
    Группирует отдельные <ul><li>...</li></ul> блоки в один <ul> блок.
    
    Алгоритм:
    1. Найти все последовательные <ul><li>...</li></ul> блоки
    2. Объединить их в один <ul> блок
    """
    lines = text.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Если это начало <ul> блока
        if line.strip() == '<ul>':
            # Собираем все элементы списка до закрывающего </ul>
            ul_items = []
            ul_items.append(line)  # <ul>
            i += 1
            
            # Собираем все <li> элементы
            while i < len(lines) and lines[i].strip().startswith('<li>'):
                ul_items.append(lines[i])
                i += 1
            
            # Пропускаем закрывающий </ul>
            if i < len(lines) and lines[i].strip() == '</ul>':
                i += 1
            
            # Добавляем собранные элементы
            result_lines.extend(ul_items)
            result_lines.append('</ul>')
        else:
            result_lines.append(line)
            i += 1
    
    return '\n'.join(result_lines)


def merge_consecutive_ul_blocks(text: str) -> str:
    """
    Объединяет последовательные <ul><li>...</li></ul> блоки в один.
    """
    # Паттерн для поиска последовательных ul блоков
    # Ищем: </ul>\n<ul> или </ul>\n<strong>text:</strong>\n<ul>
    pattern = r'</ul>\s*\n\s*<ul>'
    
    # Заменяем последовательные </ul><ul> на просто перенос строки
    text = re.sub(pattern, '\n', text)
    
    # Теперь нужно объединить элементы списков
    # Ищем паттерн: <ul>\n<li>...</li>\n</ul>\n<ul>\n<li>...</li>\n</ul>
    # Но уже обработали </ul><ul>, теперь нужно обработать структуру
    
    # Более простой подход: найти все <ul>...</ul> блоки и объединить последовательные
    lines = text.split('\n')
    result_lines = []
    i = 0
    in_ul = False
    ul_items = []
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped == '<ul>':
            if not in_ul:
                # Начало нового списка
                in_ul = True
                ul_items = ['<ul>']
            else:
                # Пропускаем дублирующий <ul>
                pass
        elif stripped == '</ul>':
            if in_ul:
                ul_items.append('</ul>')
                result_lines.extend(ul_items)
                ul_items = []
                in_ul = False
        elif in_ul and stripped.startswith('<li>'):
            ul_items.append(line)
        else:
            if in_ul:
                # Закрываем текущий список перед новым контентом
                if ul_items:
                    ul_items.append('</ul>')
                    result_lines.extend(ul_items)
                    ul_items = []
                in_ul = False
            result_lines.append(line)
        
        i += 1
    
    # Если список остался открытым
    if in_ul and ul_items:
        ul_items.append('</ul>')
        result_lines.extend(ul_items)
    
    return '\n'.join(result_lines)


def convert_strong_to_h2(text: str) -> str:
    """
    Преобразует <strong>text:</strong> в <h2>text</h2> если это подзаголовок секции.
    
    Правило: <strong>text:</strong> на отдельной строке или после переноса строки
    становится <h2>text</h2>
    """
    # Паттерн: <strong>text:</strong> на отдельной строке или после переноса
    pattern = r'<strong>([^<]+):</strong>'
    
    def replace_strong(match):
        text_content = match.group(1).strip()
        # Проверяем, что это не внутри параграфа или списка
        return f'<h2>{text_content}</h2>'
    
    # Заменяем <strong>text:</strong> на <h2>text</h2>
    # Но только если это не внутри <li> или <p>
    lines = text.split('\n')
    result_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Если строка содержит только <strong>text:</strong>
        if re.match(r'^\s*<strong>[^<]+:</strong>\s*$', line):
            text_content = re.search(r'<strong>([^<]+):</strong>', line).group(1).strip()
            result_lines.append(f'<h2>{text_content}</h2>')
        else:
            # Заменяем <strong>text:</strong> внутри строки, но не в тегах
            # Проверяем, что это не внутри <li> или <p>
            if '<li>' not in line and '<p>' not in line:
                line = re.sub(r'<strong>([^<]+):</strong>', r'<h2>\1</h2>', line)
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def remove_emoji_from_lists(text: str) -> str:
    """Удаляет эмодзи 🔹 из элементов списков"""
    lines = text.split('\n')
    result_lines = []
    
    for line in lines:
        # Если это элемент списка с 🔹 в начале
        if '<li>' in line and '🔹' in line:
            # Удаляем 🔹 из начала содержимого <li>
            line = re.sub(r'(<li>)\s*🔹\s*', r'\1', line)
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def group_lists_by_subsection(text: str) -> str:
    """
    Группирует списки по подсекциям (h2 заголовкам).
    
    Алгоритм:
    1. Найти все h2 заголовки
    2. Для каждого h2 найти все последующие <ul><li>...</li></ul> блоки
    3. Объединить их в один <ul> блок до следующего h2 или другого заголовка
    """
    lines = text.split('\n')
    result_lines = []
    i = 0
    current_subsection_items = []
    in_subsection = False
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Если это h2 заголовок
        if stripped.startswith('<h2>'):
            # Если были накопленные элементы списка, добавляем их
            if current_subsection_items:
                result_lines.extend(current_subsection_items)
                current_subsection_items = []
            
            result_lines.append(line)
            in_subsection = True
            i += 1
            
            # Собираем все списки до следующего заголовка
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                
                # Если встретили новый заголовок (h1, h2) или <strong>Важно:</strong>, останавливаемся
                if (next_stripped.startswith('<h1>') or 
                    next_stripped.startswith('<h2>') or 
                    next_stripped.startswith('<strong>Важно:') or
                    (next_stripped.startswith('<strong>') and ':' in next_stripped and not next_stripped.startswith('<strong>Важно'))):
                    break
                
                # Если это начало списка
                if next_stripped == '<ul>':
                    # Собираем весь список
                    if not current_subsection_items:
                        current_subsection_items.append('<ul>')
                    
                    i += 1
                    # Собираем все <li> элементы
                    while i < len(lines) and lines[i].strip().startswith('<li>'):
                        current_subsection_items.append(f'\t{lines[i].strip()}')
                        i += 1
                    
                    # Пропускаем закрывающий </ul>
                    if i < len(lines) and lines[i].strip() == '</ul>':
                        i += 1
                elif next_stripped.startswith('<strong>') and ':' in next_stripped:
                    # Это подзаголовок, который нужно преобразовать в h2
                    text_content = re.search(r'<strong>([^<]+):</strong>', next_stripped).group(1).strip()
                    result_lines.append(f'<h2>{text_content}</h2>')
                    i += 1
                else:
                    # Обычный текст
                    if current_subsection_items:
                        # Закрываем текущий список
                        current_subsection_items.append('</ul>')
                        result_lines.extend(current_subsection_items)
                        current_subsection_items = []
                    result_lines.append(next_line)
                    i += 1
        else:
            # Не заголовок h2
            if current_subsection_items:
                current_subsection_items.append('</ul>')
                result_lines.extend(current_subsection_items)
                current_subsection_items = []
            result_lines.append(line)
            i += 1
    
    # Если остались элементы
    if current_subsection_items:
        current_subsection_items.append('</ul>')
        result_lines.extend(current_subsection_items)
    
    return '\n'.join(result_lines)


def format_description_section(text: str) -> str:
    """
    Форматирует секцию описания компонентов согласно референсу.
    
    Преобразования:
    1. Заменяет <h3>Описание</h3> на <h1>🔬 Активные компоненты</h1>
    2. Удаляет префикс <p><strong>component_id:</strong><br>🔬 Активные компоненты:
    3. Конвертирует markdown
    4. Преобразует <strong>text:</strong> в h2
    5. Группирует списки по подсекциям
    6. Удаляет эмодзи 🔹 из списков
    7. Добавляет табуляции для элементов списка
    """
    # Шаг 1: Заменяем заголовки h3 на h1
    text = text.replace('<h3>Описание</h3>', '<h1>🔬 Активные компоненты</h1>')
    text = text.replace('<h3>Эффекты</h3>', '<h1>🌿 Целительное действие</h1>')
    text = text.replace('<h3>Шаманская перспектива</h3>', '<h1>Шаманская перспектива</h1>')
    text = text.replace('<h3>Предупреждения</h3>', '<h1>Предупреждения</h1>')
    
    # Шаг 2: Удаляем префикс <p><strong>component_id:</strong><br>🔬 Активные компоненты:
    # Паттерн: <p><strong>component_id:</strong><br>🔬 Активные компоненты:
    text = re.sub(r'<p><strong>[^<]+:</strong><br>🔬 Активные компоненты:\s*', '', text)
    text = re.sub(r'<p><strong>[^<]+:</strong><br>🌿 Целительное действие:\s*', '', text)
    text = re.sub(r'<p><strong>[^<]+:</strong><br>🌀 Шаманская перспектива:\s*', '', text)
    text = re.sub(r'<p><strong>[^<]+:</strong><br>⚠️ Предостережения:\s*', '', text)
    
    # Шаг 3: Конвертируем markdown
    text = convert_markdown_to_html(text)
    
    # Шаг 4: Преобразуем <strong>text:</strong> в h2 (на отдельной строке)
    lines = text.split('\n')
    result_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Если строка содержит только <strong>text:</strong> (подзаголовок)
        if re.match(r'^<strong>[^<]+:</strong>\s*$', stripped):
            text_content = re.search(r'<strong>([^<]+):</strong>', stripped).group(1).strip()
            result_lines.append(f'<h2>{text_content}</h2>')
        else:
            result_lines.append(line)
    
    text = '\n'.join(result_lines)
    
    # Шаг 5: Группируем списки по подсекциям
    text = group_lists_by_subsection(text)
    
    # Шаг 6: Удаляем эмодзи 🔹 из списков (если есть)
    text = remove_emoji_from_lists(text)
    
    # Шаг 7: Убираем закрывающие </p> теги, которые остались
    text = re.sub(r'</p>\s*$', '', text, flags=re.MULTILINE)
    
    # Шаг 8: Убираем лишние пустые строки между элементами списка
    lines = text.split('\n')
    result_lines = []
    prev_was_ul_tag = False
    
    for line in lines:
        stripped = line.strip()
        is_ul_tag = stripped == '<ul>' or stripped == '</ul>' or stripped.startswith('<li>')
        
        if is_ul_tag and prev_was_ul_tag and not stripped:
            # Пропускаем пустую строку между элементами списка
            continue
        
        if stripped or not prev_was_ul_tag:
            result_lines.append(line)
        
        prev_was_ul_tag = is_ul_tag
    
    return '\n'.join(result_lines)


def format_full_description(description: str) -> str:
    """
    Форматирует полное описание продукта.
    
    Сохраняет основную информацию (до <h3>Описание</h3>),
    форматирует секции описания компонентов.
    """
    # Находим начало секции описания компонентов
    desc_idx = description.find('<h3>Описание</h3>')
    
    if desc_idx < 0:
        # Если секции нет, возвращаем как есть
        return description
    
    # Разделяем на основную информацию и секции описания
    main_info = description[:desc_idx].rstrip()
    component_sections = description[desc_idx:]
    
    # Форматируем секции описания
    formatted_sections = format_description_section(component_sections)
    
    # Объединяем
    result = main_info + '\n' + formatted_sections
    
    return result


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python format_product_description_to_reference.py <description_text>")
        sys.exit(1)
    
    description = sys.argv[1]
    formatted = format_full_description(description)
    print(formatted)

