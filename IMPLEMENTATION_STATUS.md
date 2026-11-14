# Статус реализации SMS Guard

Дата: 2026-11-14 · Среда разработки: Linux, Python 3.13, Django 5.2.19, DRF 3.18.3. Windows физически **не проверялся** (см. ниже).

## Аудит по ТЗ (ML-ядро и общие требования)
| Требование | Статус | Файл | Что осталось |
|---|---|---|---|
| ФТ-2.2 язык ru/kk/en/other | ✅ проверено | `ml/lang.py` (по алфавиту) | сверить с langdetect |
| ФТ-2.3 нормализация | ✅ 13 тестов | `ml/preprocessing.py` | — |
| ФТ-2.4 единый pipeline | ✅ | `ml/artifacts/sms_model.joblib` | — |
| ФТ-2.5 словарь ≥6 групп, ≥10 выражений ×3 языка | ✅ тест | `ml/rules.py` | ревью носителем kk |
| ФТ-2.6 P_sms | ✅ | `ml/predictor.py` | MNB даёт P≈0/1 (не откалибрована) |
| ФТ-2.7 до 3 URL → модуль ссылок | ✅ тесты | `ml/service.py` | — |
| ФТ-2.8 предупреждение о языке | ✅ | `ml/service.py` | — |
| ФТ-3.1–3.8 признаки URL (27) | ✅ 13 тестов | `ml/url_features.py` | tldextract не используется (нет сети) |
| ФТ-3.9 P_url, SAFE/SUSPICIOUS/DANGEROUS | ✅ | `predictor.url_category` | — |
| ФТ-3.10 ссылки неактивным текстом | ✅ UI (веб-часть) | `templates/checks/_result.html` | — |
| ФТ-3.11 внешний API репутации | не делалось (необязательно) | — | — |
| 2.5 Risk Score, причины, рекомендация, disclaimer | ✅ 15 тестов | `ml/risk.py`, `risk_config.yaml` | — |
| Калибровка Recall≥0.95 / safe-high≤3 % | ⚠️ **не достигнуто на test** | `ml/calibrate_risk.py`, `data/reports/risk_calibration.json` | больше данных |
| НФТ-1 ≤500 мс (SMS+3 URL) | ✅ без Django: медиана 10 мс; через Django: медиана 20 мс, p95 24 мс | — | — |
| НФТ-14 старт без модели | ✅ Predictor не падает; веб показывает ошибку, API отвечает 503 | тесты | — |
| ФТ-1.x регистрация/вход/CSRF/cookie | ✅ | `apps/accounts/` | восстановление пароля не делалось |
| REST API (4.4), throttling 30/мин, 503 | ✅ | `apps/checks/api.py` | drf-spectacular (схема OpenAPI) не подключён |
| БД, история, фильтры, удаление | ✅ | `apps/checks/models.py` | «маскирование» заменено политикой: без согласия текст и полные URL не хранятся |
| UI (вход, регистрация, панель, SMS, URL, история, детали, подтверждение удаления), Chart.js | ✅ | `templates/`, `static/` | — |
| pytest + coverage ≥60 % ml/ | ⚠️ `manage.py test`: 126 OK; coverage не измерен | `tests/`, `apps/*/tests/` | pytest-cov |
| Docs: Use Case, ER, диаграммы, матрица трассировки, отчёт | ⛔ не сделано | — | — |

## Что реализовано (веб-часть)

| Требование | Статус | Где | Чем проверено |
|---|---|---|---|
| Регистрация, вход, выход | ✅ | `apps/accounts/` | `apps/accounts/tests/test_auth.py` (11 тестов) |
| Dashboard: счётчики, график по дням, категории (Chart.js) | ✅ | `apps/checks/views.py:dashboard`, `static/js/dashboard.js` | тесты статистики + просмотр в Chromium |
| Проверка SMS: категория, вероятность, Risk Score, объяснение | ✅ | `apps/checks/views.py:sms_analyzer`, `templates/checks/_result.html` | `test_web.py` |
| Извлечение URL (до 3) и их оценка | ✅ | `ml.service.analyze_sms` + шаблон | `test_urls_extracted_and_analysed_separately` |
| Повторная проверка найденной ссылки отдельно | ✅ (POST-кнопка) | `_result.html` → `/url/` | тест (3 кнопки на 3 ссылки) |
| Отдельная форма проверки URL | ✅ | `url_analyzer` | `UrlAnalyzerTests` |
| История: фильтры (тип, категория, даты, риск), пагинация 10/стр. | ✅ | `history`, `HistoryFilterForm` | `HistoryTests` |
| Подробности проверки | ✅ | `detail` | `DetailAndDeleteTests` |
| Удаление своих записей (одной / всей истории) | ✅ | `delete`, `clear_history` | тесты, включая чужие записи и CSRF |
| REST API: analyze sms/url, checks, stats, health, токены | ✅ | `apps/checks/api.py` | `test_api.py` (21 тест) |
| Модели загружаются один раз | ✅ синглтон `Predictor.get()` + прогрев при старте | `apps/checks/apps.py` | `test_models_loaded_once` |
| Модель недоступна → понятная ошибка | ✅ веб: страница с 503; API: 503 | `views.py`, `api.py` | тесты с пустой папкой моделей |
| Без сети/DNS | ✅ | ML-ядро + Django-слой не делают запросов | тест с запретом `socket.getaddrinfo/connect` |
| Пользователь видит только свои данные | ✅ все запросы фильтруются по `user`, чужая запись → 404 | `views.py`, `api.py` | тесты web и API |
| CSRF | ✅ Django middleware, DRF SessionAuth | — | тесты с `enforce_csrf_checks` |
| XSS | ✅ автоэкранирование + CSP без `unsafe-inline` и без внешних ресурсов; данные графиков через `json_script` | `apps/core/middleware.py` | тест на `<script>`/`<img onerror>`; 0 ошибок CSP в консоли Chromium |
| SQL-инъекции | ✅ только ORM, фильтры проходят через формы | `services.filter_checks` | тест с `' OR 1=1 --` в параметрах |
| Валидация входа | ✅ длина (SMS ≤2000, URL ≤2048), схемы только http/https, без пробелов | `forms.py`, `serializers.py` | тесты web и API |
| Ограничение частоты | ✅ анализ: 30/мин на пользователя; вход/регистрация: 10/мин с IP; токен: 10/мин | `apps/core/ratelimit.py`, `throttles.py` | тесты (429 + Retry-After) |
| Текст SMS только по согласию | ✅ инвариант в `Check.save()`; без согласия не хранятся текст и полные URL (остаются домены) | `models.py`, `services.py` | тесты |
| SMS не пишется в логи | ✅ логируются только id, тип, итог | `services.py` | тест `test_sms_content_not_logged` |
| Ссылки не кликабельны | ✅ вывод как текст `hxxp://x[.]y`, нет `<a href>` | фильтр `defang` | тест на отсутствие `href="http…"` |
| ФТ-3.10 (ссылки неактивным текстом) | ✅ закрыто | — | — |
| Адаптивный интерфейс | ✅ проверен в Chromium 1280 px и 390 px (скриншоты) | `templates/`, `static/css/app.css` | визуально, вручную |

## Результаты тестирования (фактические)

Команды запускались **в чистом venv** (копия проекта без `__pycache__`, `pip install -r requirements.txt`, без системных пакетов):

```
python -m unittest discover -s tests -t .   ->  Ran 62 tests ... OK
python manage.py test                        ->  Ran 126 tests ... OK   (62 ML + 64 Django/API)
python manage.py check                       ->  System check identified no issues
python manage.py migrate                     ->  OK
runserver + curl: /accounts/login/ 200, / (аноним) 302, /api/v1/health/ 200 {"status":"ok",...}, статика 200
```

Установленные версии: Django 5.2.19, DRF 3.18.3, scikit-learn 1.9.1, pandas 3.0.5, numpy 2.5.3, joblib 1.6.0, PyYAML 6.0.3.

Ручная проверка в Chromium (Playwright): регистрация → проверка 5 SMS и 1 URL → панель, история с фильтром, детали; на десктопе и 390 px; **ошибок и предупреждений консоли (включая CSP) нет**. Скрипт проверки в репозиторий не включён.

Скорость (НФТ-1 ≤ 500 мс), SMS с 3 URL через Django test client, 100 запросов после прогрева моделей: **медиана 20 мс, p95 24 мс**. Первый запрос без прогрева занимал ≈1,1 с (загрузка моделей), поэтому добавлен прогрев при старте сервера.

### Windows
Физически на Windows **не запускалось** (среда разработки — Linux). Что сделано для совместимости: только `pathlib`; чтение конфигов и данных с `encoding="utf-8"` в рантайме; зависимости — чистые wheels; `tzdata` для Windows в `requirements.txt`; Bootstrap/Chart.js/шрифты лежат локально; инструкции в README — для PowerShell. Известный риск: `ml/calibrate_risk.py` пишет JSON через `open(..., "w")` без кодировки (только скрипт калибровки, не рантайм; ML-код по условию не менялся). Первую проверку на Windows нужно выполнить: `pip install -r requirements.txt` → `python manage.py test` → `python manage.py runserver`.

## Результаты ML-ядра (факты, без изменений)
- Тесты: `python -m unittest discover -s tests -t .` → **62 OK** (26 прежних + 36 новых).
- SMS-модель, test (train-only fit): Precision **0.594**, Recall 0.987, ROC-AUC 0.783 — **требование ТЗ не выполнено**.
- URL-модель, test: Precision 0.902, **Recall 0.848** (цель 0.85), ROC-AUC 0.958.
- Risk (test, веса с val): Recall «средний+» 1.00, но доля безопасных с «высоким» = **23 %** (цель ≤3 %); с исходными весами 47 %. Причина: в test безопасные шаблоны (коды, доставка, банковские уведомления), которых нет в train; на val их мало, поэтому val-калибровка не переносится.
- Правило смягчения «никому не сообщайте код» введено по ТЗ (демо-сообщение №4) после того, как та же ошибка была замечена на test: честнее считать test в этой части уже просмотренным.

## Оставшиеся задачи и ограничения

- **Windows**: прогнать установку, тесты и запуск на реальной машине (см. выше).
- **Качество ML не изменилось и остаётся слабым**: модели обучены на синтетике; Precision SMS-модели на test 0,594; требования ТЗ по калибровке Risk (safe-high ≤ 3 %) не выполнены. Интерфейс честно предупреждает об этом.
- **Ограничение частоты в веб-части** использует локальный кэш процесса (LocMem): при нескольких процессах/серверах нужен общий кэш (Redis/Memcached). Счётчик API (DRF) использует тот же кэш.
- **Нет продакшн-конфигурации**: статика раздаётся `runserver` (нужен WhiteNoise/nginx), HTTPS, gunicorn/waitress, PostgreSQL не настраивались.
- Нет: восстановления пароля, e-mail, удаления аккаунта, смены пароля, администрирования (`django.contrib.admin` не подключён), интерфейса на казахском/английском (UI только русский), экспорта истории.
- Панель показывает фиксированные 14 дней; пагинация и фильтры истории — без сортировки по столбцам.
- Автоматических браузерных (E2E) тестов в репозитории нет; визуальная проверка выполнена вручную только в Chromium.
- Покрытие кода (coverage) не измерялось; pytest не используется (тесты — `unittest`/Django).
- Внешний API репутации ссылок (ФТ-3.11, необязательно) не делался.
- Документы: Use Case, ER-диаграмма, матрица трассировки, отчёт — не созданы.
- Прежний список улучшения SMS-модели (ниже) остаётся актуальным.

## Как улучшить SMS-модель (реальные шаги)
1. Реальный UCI SMS Spam + PhiUSIIL (нужна сеть: `python -m ml.data.download_open`).
2. ≥6–8 независимых шаблонов на категорию, ручная проверка kk носителем.
3. Калибровка вероятностей (`CalibratedClassifierCV`) вместо сырого MNB.
4. Повторная калибровка Risk на большем val.
