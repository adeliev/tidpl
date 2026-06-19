# tidpl — Создатель плейлистов Tidal

Автоматически собирает треки из твоих миксов Tidal, выбирает случайную ежедневную подборку и создаёт **плейлист прямо в Tidal**.

Использует ту же авторизацию и API, что и [tiddl](https://github.com/oskvr37/tiddl), но работает как отдельный независимый проект.

---

## Быстрый старт

```bash
# Полный цикл: экспорт + создание плейлиста в Tidal
./run.sh run
```

---

## Команды

| Команда | Описание |
|---------|----------|
| `run`  | Полный цикл: выбор треков из миксов → отправка в плейлист Tidal |
| `export` | Только экспорт треков из миксов (создаёт `DailyTidal.txt`) |
| `push`  | Только поиск и заливка треков из текстового файла в Tidal |

### Параметры

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `-i, --input` | `data/mixes.txt` | Файл с URL миксов/плейлистов |
| `-b, --blocklist` | `data/artist_blocklist.txt` | Исполнители для исключения |
| `-d, --daily` | `data/DailyTidal.txt` | Выходной файл дневной подборки |
| `-o, --output` | `data/all_tracks.txt` | Все собранные треки |
| `--history` | `data/daily_history.json` | История выбранных треков |
| `-n, --count` | `100` | Количество треков в дневной подборке |
| `--history-days` | `3` | Сколько дней не повторять трек |
| `--name` | `Deli Mix` | Название плейлиста (по умолчанию в коде; задать через `--name "Ежедневный микс"`) |
| `--desc` | `...` | Описание плейлиста |

### Примеры

```bash
# Полный цикл, 50 треков
./run.sh run --count 50

# Только экспорт (не трогает плейлист)
./run.sh export --count 100

# Залить готовый файл в Tidal
./run.sh push path/to/tracks.txt --name "Мой Микс"
```

---

## Как это работает

1. **Экспорт** — читает URL миксов из `data/mixes.txt`, загружает все треки через Tidal API, удаляет дубликаты и исключённых исполнителей, учитывает историю, выбирает N случайных треков.
2. **Отправка** — ищет каждый трек на Tidal, удаляет старый плейлист (если есть), создаёт новый и добавляет все найденные треки батчами по 100 штук.

---

## Файлы данных

Всё хранится в `data/`:

| Файл | Назначение |
|------|------------|
| `auth.json` | Токен Tidal (обязателен, см. Установку) |
| `mixes.txt` | URL миксов, по одному на строку |
| `artist_blocklist.txt` | Заблокированные исполнители |
| `DailyTidal.txt` | Сгенерированная дневная подборка |
| `all_tracks.txt` | Все уникальные треки из миксов |
| `daily_history.json` | История для исключения повторов |
| `.last_run` | Метка планировщика |

### Пример mixes.txt

```
https://tidal.com/mix/002031a111d26d855f13df60ef8035
https://tidal.com/mix/0020a08efcb74f0b86c8363bf5efae
```

### Пример artist_blocklist.txt

```
Taylor Swift
Eminem
```

### Пример artist_aliases.txt (опционально, в `data/`)

Формат: `Имя = Псевдоним`, по одному на строку.

```
Electric Callboy = Eskimo Callboy
```

---

## Планировщик

Три варианта:

### Вариант 1 — launchd (рекомендуется для macOS)

1. Скопируйте `com.tidpl.scheduler.plist.example` → `com.tidpl.scheduler.plist`, отредактируйте пути.
2. Выполните:

```bash
./service.sh install
./service.sh status
./service.sh uninstall
```

Запускает `run-if-due.sh` каждые 6 часов. Скрипт запускает `run` только если прошло 2+ дня.

### Вариант 2 — Фоновый Python-скрипт

```bash
.venv/bin/python3 scheduler.py
```

Работает в консоли (Ctrl+C для остановки). Проверяет каждые 6 часов.

### Вариант 3 — Cron

```bash
crontab -e
0 */6 * * * /АБСОЛЮТНЫЙ/ПУТЬ/К/tidpl/run-if-due.sh
```

---

## Установка

### Требования

- Python 3.12+
- Подписка Tidal HiFi или выше
- `auth.json` в `data/` (сессионный токен Tidal)

### Получение auth.json

**Если установлен tiddl**, скопируйте:

```bash
cp /path/to/tiddl/data/tiddl/auth.json data/
```

**Иначе**, выполните авторизацию через tiddl:

```bash
pip install tiddl
tiddl auth login
cp ~/.tiddl/auth.json /path/to/tidpl/data/
```

### Первый запуск

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

# Создайте список миксов
cp data/mixes.txt.example data/mixes.txt    # затем отредактировать
cp data/artist_blocklist.txt.example data/artist_blocklist.txt  # опционально

# Тест
./run.sh run --count 10
```

---

## Структура проекта

```
tidpl/
├── run.sh                 # Быстрый запуск
├── run-if-due.sh          # Для cron/launchd — проверяет маркер
├── scheduler.py           # Фоновый планировщик
├── service.sh             # Управление launchd
├── com.tidpl.scheduler.plist.example  # Шаблон launchd
├── .gitignore
├── pyproject.toml
├── tidpl/
│   ├── cli.py             # CLI на Typer
│   ├── auth.py            # Авторизация
│   ├── playlist.py        # Экспорт + создание плейлиста
│   └── vendor/            # Вендорные модули (auth, API, модели)
└── data/
    ├── auth.json          # (в gitignore)
    ├── mixes.txt
    ├── artist_blocklist.txt
    ├── DailyTidal.txt
    ├── all_tracks.txt
    ├── daily_history.json
    └── scheduler.log
```

---

## Замечание

Только для личного использования. Не связано с Tidal. Соблюдайте условия использования Tidal.
