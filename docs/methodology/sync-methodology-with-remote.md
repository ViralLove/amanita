# Синхронизация docs/methodology с папкой methodology в репо cursor-rules

Источник истины: **docs/methodology** (Amanita). Папка привязана к удалённой папке **methodology/** внутри репо https://github.com/eslinko/cursor-rules — без отдельного репо.

---

## 1. Создать папку methodology в cursor-rules (один раз)

Выполнять из корня Amanita. Репо rules уже подключён как `.cursor/rules` с remote `origin` = cursor-rules.

```bash
# Перейти в клон cursor-rules
cd .cursor/rules

# Создать папку (git не хранит пустые директории — нужен хотя бы один файл)
mkdir -p methodology
touch methodology/.gitkeep

# Закоммитить и запушить
git add methodology/
git commit -m "chore: add empty methodology folder"
git push origin main
```

После этого на GitHub в репо cursor-rules есть ветка `main` с папкой `methodology/` (пока только `.gitkeep`).

---

## 2. Подключить docs/methodology к этой удалённой папке (один раз)

Используем **git subtree**: контент из `docs/methodology` попадёт в `methodology/` в cursor-rules. Не делаем `git pull` в docs/methodology до первого пуша — иначе можно потерять локальные файлы.

### 2.1. Сделать docs/methodology отдельным git-репо и запушить в cursor-rules отдельной веткой

Из корня Amanita:

```bash
cd docs/methodology

# Свой репо только для этой папки
git init
git add .
git commit -m "chore(methodology): initial methodology docs"

# Ремоут = cursor-rules (тот же репо, что и .cursor/rules)
git remote add origin https://github.com/eslinko/cursor-rules.git

# Пушим на ветку methodology-src (файлы методики в корне ветки). Не делать pull.
git push -u origin main:methodology-src
```

Так в cursor-rules появляется ветка `methodology-src` с файлами методики в корне (не в подпапке).

### 2.2. В cursor-rules подтянуть эту ветку в папку methodology/ (subtree add)

Из корня Amanita:

```bash
cd .cursor/rules

# Подтянуть ветку methodology-src в папку methodology/
git subtree add --prefix=methodology origin methodology-src

# Отправить обновлённый main
git push origin main
```

После этого в cursor-rules на `main` папка `methodology/` содержит все файлы из docs/methodology; локально в docs/methodology ничего не удалилось.

---

## 3. Дальнейшая работа (источник истины = docs/methodology)

- Редактируешь файлы в **docs/methodology**.
- Коммиты делаешь внутри **docs/methodology** (`git add .`, `git commit`).
- Чтобы обновить папку methodology в cursor-rules:

  ```bash
  # 1) Из docs/methodology — отправить изменения в ветку methodology-src
  cd docs/methodology
  git push origin main:methodology-src

  # 2) В .cursor/rules — подтянуть их в папку methodology/ и запушить main
  cd .cursor/rules
  git subtree pull --prefix=methodology origin methodology-src
  git push origin main
  ```

---

## Важно при первой привязке

При первом подключении docs/methodology к cursor-rules **не делайте `git pull`** в docs/methodology до первого пуша. Порядок: **init → add → commit → remote → push** (в ветку methodology-src). Так пустой ремоут не перезапишет локальные файлы.

---

## Краткий чеклист

- [ ] В .cursor/rules создана папка methodology (с .gitkeep), закоммичена и запушена (п. 1).
- [ ] В docs/methodology выполнен init → add → commit → remote → push в ветку methodology-src, **без pull** (п. 2.1).
- [ ] В .cursor/rules выполнен subtree add и push main (п. 2.2).
- [ ] Дальше правки в docs/methodology, затем push в methodology-src и subtree pull в .cursor/rules (п. 3).
