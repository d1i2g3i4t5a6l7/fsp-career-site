# «ФСП Карьера» — платформа подбора ИТ-специалистов ФСП

Кандидат подтверждает грейд рабочими задачами с разрешённым ИИ, работодатель находит его по подтверждённому профилю и сам отправляет приглашение с вилкой. Подробно: [анализ и алгоритм](docs/01-analysis-and-algorithm.md), [архитектура](docs/02-architecture.md).

## Демо

| Что | Адрес |
| --- | --- |
| Сайт | https://62-109-11-219.sslip.io |
| API бэкенда (Swagger) | https://62-109-11-219.sslip.io/api/workspace/docs |
| Swagger на локальном стенде | http://localhost:8010/docs |

Тестовый стенд закрыт общим паролем — браузер спросит его при первом входе:

| Логин | Пароль |
| --- | --- |
| `fsp` | `wtphrw3li5` |

Это вход на сам стенд (`SITE_PASSWORD`). После него — вход в кабинет тестовым аккаунтом ниже.

### Тестовые аккаунты

Вход — тестовые аккаунты, зашитые в сайт (на странице «Войти» они уже подставлены):

| Роль | Почта | Пароль |
| --- | --- | --- |
| Кандидат | a.korneev@mail.ru | fsp-test-2026 |
| Работодатель | i.volkova@severcode.ru | fsp-test-2026 |

### Что посмотреть за 5 минут

**Кандидат.** «Регистрация» → почта и пароль → опрос (направление, стек) → выбор грейда → тест: одна задача на 30 минут, рядом ИИ-ассистент, «Запустить тесты», «Отправить решение» → плашка «Решение на проверке» → результат: балл, разбор по критериям, грейд → кабинет: категория, место в ней, приглашения от компаний — «Принять» или «Отклонить» с причиной.

**Работодатель.** «Войти» → «Работодатель» → «Потребность»: направление, грейд, стек, вилка → «Подборка»: рейтинг 0–100 и причины у каждого кандидата → карточка кандидата → «Пригласить»: вилка обязательна → «Приглашения»: статусы и контакты после принятия → «Проверка оценок»: отчёт ИИ по критериям, можно исправить вердикт.

Без ключей моделей стенд работает на **заглушке LLM** — весь путь от старта теста до грейда проходит без сети.

## Что в репозитории

| Папка | Что это | Статус |
| --- | --- | --- |
| `frontend/` | Сайт: главная, вход, регистрация, кабинеты кандидата и работодателя. Тест на грейд, ассистент, результат, грейд и балл в профиле и подборках — с бэкенда (`workspace`), остальное пока на демо-данных. Подробно — [frontend/README.md](frontend/README.md), изменения — [docs/03-frontend-changes.md](docs/03-frontend-changes.md) | работает |
| `workspace/` | Рабочее место кандидата и оценка: попытка с таймером, ИИ-ассистент, банк и генерация задач, проверка LLM-судьёй по рубрике, грейд, шлюз к GigaChat. API — [workspace/README.md](workspace/README.md) | работает |
| `runner/` | Песочница для кода кандидата: API в формате Piston, контейнер без сети | работает |
| `docs/` | ТЗ, анализ, архитектура, журнал изменений фронта, нерешённые вопросы | — |
| core-api | Профиль, подбор, приглашения, вакансии | в работе |

## Запуск у себя

Нужен только Docker с Compose v2.24 или новее (Docker Desktop на Windows и macOS, Docker Engine на Linux). Node.js и Python ставить не нужно — всё собирается в контейнерах.

1. Склонировать репозиторий и перейти в папку:

   ```bash
   git clone https://github.com/d1i2g3i4t5a6l7/fsp-career-site.git
   cd fsp-career-site
   ```

2. Поднять стенд (первая сборка — несколько минут):

   ```bash
   docker compose up -d --build
   ```

3. Проверить, что всё запустилось:

   ```bash
   docker compose ps                     # web, workspace, runner, postgres — в состоянии running / healthy
   curl http://localhost:8010/health     # ответ бэкенда
   ```

4. Открыть:
   - сайт — http://localhost:8080;
   - API бэкенда (Swagger) — http://localhost:8010/docs.

Стенд сразу работает на **заглушке LLM**: ассистент и судья отвечают по шаблону, ключи не нужны.

### Подключить настоящие модели GigaChat

```bash
cp workspace/.env.example workspace/.env   # LLM_MODE=live и ключ GIGACHAT_AUTH_KEY или CLOUDRU_API_KEY
docker compose up -d                       # пересоздаст workspace с новыми настройками
```

Ключи — только в `workspace/.env`, он в `.gitignore`. Сертификаты НУЦ Минцифры для API Сбера уже в `workspace/certs/`. Что ещё настраивается (каналы моделей, число прогонов судьи, сроки пересдачи) — комментарии в `workspace/.env.example`.

### Частые проблемы

| Симптом | Что сделать |
| --- | --- |
| Порт 8080 или 8010 занят | `WEB_PORT=8081 WORKSPACE_PORT=8020 docker compose up -d` |
| После `git pull` сайт или API старые | `docker compose up -d --build` |
| Ошибки схемы БД после обновления | `docker compose down -v` и снова `up -d --build` — база пересоздастся (данные стенда удалятся) |
| Тест долго «на проверке» | `docker compose logs -f workspace`; в режиме `live` ответы GigaChat идут через очередь, у физлица — 1 запрос одновременно |

### Что поднимается

```text
localhost:8080 ──► web        (сайт: собран Vite, отдаёт nginx)
localhost:8010 ──► workspace ──unix-сокет──► runner   (без сети, код кандидата под отдельным uid)
                       │
                       └──────────────────► postgres (pgvector, том pgdata)
                       └── HTTPS ─────────► GigaChat: API Сбера / cloud.ru
```

- **web** — готовый сайт из `frontend/`, около 10 МБ памяти. Запросы сайта `api/workspace/…` пересылает в `workspace`, причём только те, которыми сайт пользуется; служебное (генерация задач, задачи с эталоном, одобрение задач, перепроверка, Swagger) — только напрямую на машине со стендом, http://localhost:8010. Для показа наружу можно поставить общий пароль на сайт: `SITE_PASSWORD=… docker compose up -d web`, логин `fsp`. Порт открыт только на `127.0.0.1`, другой порт — `WEB_PORT=8081 docker compose up -d`.
- **workspace** — один процесс uvicorn: очереди к моделям, события WebSocket и фоновые проверки живут в памяти. Не масштабировать копиями. Порт открыт только на `127.0.0.1`: авторизации пока нет, а `GET /tasks/{id}` отдаёт эталон.
- **runner** — `network_mode: none`, файловая система только для чтения, лимиты 1 ГБ памяти и 256 процессов, 20 с на запуск, 64 КБ вывода. Пакеты для кода кандидата (numpy, pandas…) — в `runner/requirements.txt`, тот же список — в `SANDBOX_PACKAGES` в `workspace/.env`.
- **postgres** — PostgreSQL 17 с pgvector. Таблицы workspace создаются при старте, миграций пока нет.

### Обслуживание

| Задача | Команда |
| --- | --- |
| Логи | `docker compose logs -f workspace` |
| Обновить после `git pull` | `docker compose up -d --build` — прерванные проверки и генерации начнутся заново, а текущий ответ ассистента оборвётся |
| Остановить | `docker compose down` (данные остаются в томе) |
| Сбросить базу | `docker compose down -v` — нужно и при смене схемы таблиц |
| Консоль БД | `docker compose exec postgres psql -U fsp workspace` |
| Бэкап БД | `docker compose exec postgres pg_dump -U fsp workspace > backup.sql` |
| Сохранить банк задач в репозиторий | `python workspace/scripts/export_tasks.py` — одобренные задачи из БД в `workspace/tasks/`, оттуда они загрузятся на любой машине |
| Другой порт | `WORKSPACE_PORT=8020 docker compose up -d` |

### На сервере

Тот же стенд плюс Caddy — наружу открыт только он (порты 80 и 443): сам получает сертификат https и пересылает запросы на сайт. Сайт и бэкенд по-прежнему слушают только `127.0.0.1`. Настройки сервера — `compose.server.yaml` и `deploy/Caddyfile`.

1. На сервере — Docker с Compose, папка проекта и `workspace/.env` с ключами (права `600`, только root).
2. Рядом с `compose.yaml` — файл `.env` (в `.gitignore`, права `600`):

   ```bash
   SITE_HOST=1-2-3-4.sslip.io   # адрес сайта с https; без своего домена — IP сервера через sslip.io
   SITE_IP=1.2.3.4              # запасной вход по IP, без https
   SITE_PASSWORD=…              # общий пароль на сайт, логин fsp; пусто — сайт открыт
   POSTGRES_PASSWORD=…
   ```

3. `export COMPOSE_FILE=compose.yaml:compose.server.yaml`, затем `docker compose up -d --build`. На слабом сервере собирать по одной части: `docker compose build web`, потом `workspace`, `runner`.

Песочнице на сервере — 1 ядро и 512 МБ памяти (`RUNNER_CPUS`, `RUNNER_MEM` в `.env`): на сервере с одним ядром Docker не запустит контейнер с лимитом в 2 ядра. Остальные команды — как в таблице выше, с тем же `COMPOSE_FILE`.

## Запуск без Docker

Для разработки: [workspace/README.md](workspace/README.md#запуск). Там SQLite и `SANDBOX=local` — код кандидата запускается прямо на машине, поэтому только для своих задач.

Сайт: `npm install` и `npm run dev` в `frontend/`, адрес http://localhost:5173 — см. [frontend/README.md](frontend/README.md#запуск).

Тесты: `pytest` в `workspace/` (на Postgres — с `TEST_DATABASE_URL=postgresql+asyncpg://…`), `python -m unittest test_server` в `runner/`.

## Компоненты и версии

| Компонент | Версия | Лицензия |
| --- | --- | --- |
| Python | 3.11 | PSF |
| FastAPI | 0.142.4 | MIT |
| Uvicorn | 0.54.0 | BSD |
| SQLAlchemy | 2.1.4 | MIT |
| asyncpg / aiosqlite | 0.32.0 / 0.22.1 | Apache-2.0 / MIT |
| Pydantic / pydantic-settings | 2.13.5 / 2.15.0 | MIT |
| HTTPX | 0.28.1 | BSD |
| PostgreSQL + pgvector | 17 (образ `pgvector/pgvector:pg17`) | PostgreSQL License |
| Vite (сборка сайта) | 6.4.4 | MIT |
| React (сайт) | 18.3.1 | MIT |
| nginx (раздача сайта) | 1.27 | BSD-2-Clause |
| Модели | GigaChat 3.x: API Сбера, cloud.ru, свой vLLM — [архитектура](docs/02-architecture.md#gigachat-3x-какие-модели-и-как-подключаем) | — |
