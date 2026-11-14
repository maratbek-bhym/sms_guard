# SMS Guard

Учебное веб-приложение для проверки SMS и ссылок на признаки мошенничества.
ML-ядро (`ml/`) обучено и протестировано отдельно; веб-часть (Django 5.2 + Django REST Framework + Bootstrap 5 + Chart.js) вызывает его функции `analyze_sms` и `analyze_url` и ничего не дублирует.

> **Важно.** Модели обучены **только на синтетических данных** — реальное качество не подтверждено (см. `IMPLEMENTATION_STATUS.md`). Оценка вероятностная и не гарантирует безопасность. Проверяемые ссылки никогда не открываются, DNS-запросы не выполняются.

## Возможности

- Регистрация, вход, выход (выход только POST); у каждого пользователя своя история.
- **Панель**: число проверок, разбивка по категориям, график по дням, последние проверки.
- **Проверка SMS**: категория, вероятность, Risk Score 0–100, причины, рекомендация, найденные приёмы обмана; до 3 ссылок из текста извлекаются и оцениваются отдельно, каждую можно проверить повторно кнопкой «Проверить отдельно».
- **Проверка ссылки**: категория, вероятность, Risk Score, признаки адреса.
- **История**: фильтры (тип, категория, даты, минимальный риск), пагинация по 10, подробности, удаление записи и очистка всей истории.
- **REST API** `/api/v1/` с токенами, ограничением частоты (30 проверок в минуту) и ответом 503, если модель недоступна.
- Текст SMS сохраняется **только с галочкой согласия**. Без неё в базе остаются оценка и домены ссылок (полный адрес и текст — нет).
- Ссылки показываются как текст в «обезвреженном» виде (`hxxp://site[.]example`), а не как `<a href>`.

## Требования

- Python **3.12 или новее** (Windows, Linux, macOS)
- доступ к PyPI для `pip install` (Bootstrap, Chart.js и шрифты уже лежат в `static/vendor` и `static/fonts` — CDN не нужен)

## Установка и запуск (Windows PowerShell)

Откройте PowerShell в папке проекта (там, где лежит `manage.py`):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

Откройте http://127.0.0.1:8000/ , нажмите «Зарегистрируйтесь» и создайте аккаунт.

Если PowerShell запрещает активацию (`running scripts is disabled`), выполните один раз в этом окне:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Если команды `py` нет, используйте `python -m venv .venv` (Python должен быть 3.12+: `python --version`).

### Linux / macOS

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py runserver
```

## Тесты

Все тесты (62 теста ML-ядра + тесты Django и API) запускаются одной командой:

```powershell
python manage.py test
```

Только ML-ядро (прежняя команда):

```powershell
python -m unittest discover -s tests -t .
```

Что покрыто: регистрация и вход, ограничение попыток входа, проверка SMS/URL, согласие на хранение текста, извлечение ссылок, история (фильтры, пагинация), детали, удаление, доступ к чужим записям (404), CSRF, экранирование XSS, SQL-подобные значения в фильтрах, отсутствие SMS в логах, отсутствие сетевых обращений при анализе, единичная загрузка моделей, ответ 503 без модели, API (токены, валидация, throttling, права доступа).

## REST API

Токен: `POST /api/v1/auth/token/`. Дальше заголовок `Authorization: Token <токен>`.

```powershell
$r = Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/auth/token/ `
     -ContentType "application/json" -Body '{"username":"student","password":"ВАШ_ПАРОЛЬ"}'
$h = @{ Authorization = "Token $($r.token)" }

# SMS (save_text по умолчанию false: текст не сохраняется)
$body = @{ text = "Ваша карта заблокирована! Срочно: http://secure-bank.example/login"; save_text = $false } | ConvertTo-Json
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/analyze/sms/ -Headers $h -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))

# ссылка
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/analyze/url/ -Headers $h -ContentType "application/json" -Body '{"url":"http://192.168.4.5/login.php"}'
```

| Метод и путь | Назначение |
|---|---|
| `POST /api/v1/auth/token/` | получить токен (10 запросов/мин с IP) |
| `GET /api/v1/health/` | состояние моделей (без авторизации): 200 или 503 |
| `POST /api/v1/analyze/sms/` | `{text, save_text}` → 201; 400 при невалидных данных; 503 без модели |
| `POST /api/v1/analyze/url/` | `{url}` → 201 |
| `GET /api/v1/checks/` | свои проверки; фильтры `kind`, `category`, `date_from`, `date_to`, `min_score`, `page` |
| `GET` / `DELETE /api/v1/checks/<id>/` | одна своя запись (чужая — 404) |
| `GET /api/v1/stats/` | статистика для панели |

Анализ ограничен 30 запросами в минуту на пользователя (ответ 429).

## Настройки (переменные окружения, необязательные)

| Переменная | Значение по умолчанию |
|---|---|
| `DJANGO_DEBUG` | `1` (локальная разработка) |
| `DJANGO_SECRET_KEY` | встроенный dev-ключ; при `DJANGO_DEBUG=0` **обязателен** |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` |
| `DB_PATH` | `db.sqlite3` в корне проекта |
| `MODEL_DIR` | `ml/artifacts` |
| `ML_PRELOAD` | `1` — загрузить модели при старте сервера |

PowerShell: `$env:DJANGO_DEBUG = "0"; $env:DJANGO_SECRET_KEY = "длинная-случайная-строка"`.

## Структура

```
manage.py, config/        настройки и маршруты Django
apps/accounts/            регистрация, вход
apps/checks/              модель Check, сервисный слой над ml, веб-страницы, REST API
apps/core/                заголовки безопасности (CSP), ограничение частоты, фильтры шаблонов
templates/, static/       интерфейс (Bootstrap 5, Chart.js, IBM Plex — всё локально)
ml/                       ML-ядро (не менять): service.py, predictor.py, risk.py, rules.py, artifacts/
tests/                    62 теста ML-ядра
```

## ML-пайплайн (для воспроизведения обучения)

Нужен только для переобучения; для запуска приложения не требуется.

```powershell
python -m ml.data.generate_urls; python -m ml.data.generate_sms
python -m ml.data.build_datasets; python -m ml.train_sms; python -m ml.train_url
```

Подробности и честный аудит по ТЗ — в `IMPLEMENTATION_STATUS.md`. Отчёты по данным — `data/reports/`.
