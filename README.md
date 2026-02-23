# MiniTrello (Django + React)

Учебный fullstack-проект в стиле Trello (Kanban-доска задач) с JWT-авторизацией, карточками, комментариями, фильтрами, drag-and-drop и логом активности.

## Stack

### Backend

- Python / Django
- Django REST Framework
- PostgreSQL
- drf-spectacular (OpenAPI / Swagger)

### Frontend

- React
- Radix UI
- Vite
- ESLint + Prettier

### Deploy

- Docker Compose (3 контейнера: backend, frontend, db)
- GitHub Actions (lint + tests + build)

## Реализованный функционал

- JWT регистрация / авторизация
- Доски (`boards`)
- Колонки с кастомными названиями
- Карточки: title, markdown description, priority, deadline, labels
- Drag-and-drop карточек между колонками и внутри колонки
- Комментарии к карточкам (автор + время)
- Фильтры по priority / labels / assignee / deadline
- Лог активности доски
- Назначение карточки на пользователя (`assignee`)
- Swagger / OpenAPI (`/api/docs/`)

## Структура проекта

- `backend/` - Django backend
- `frontend/` - React frontend (Vite)
- `docs/schema.dbml` - согласованная DBML-схема
- `docker-compose.yml`
- `ARCHITECTURE.md`

## Быстрый запуск (Docker Compose)

```bash
docker-compose up --build
```

После запуска:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/`
- Swagger UI: `http://localhost:8000/api/docs/`

На старте backend выполняет:

1. `migrate`
2. `seed_data`

## Seed-данные

Seed-команда создает (на пустой БД):

- 2 пользователя
- 2 доски
- 4 колонки
- 20 карточек
- 10 комментариев

Пользователи (после `seed_data`):

- `alex` / `password123`
- `maria` / `password123`

## Локальный запуск без Docker

### Backend

```bash
pip install -r requirements.txt
cd backend
python manage.py makemigrations users kanban
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server работает на `http://localhost:5173` и проксирует `/api` на backend (`http://localhost:8000`).

## Backend tests

```bash
cd backend
python manage.py test
```

В проекте добавлено более 10 тестов для backend.

## Основные API endpoints

### Auth

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

### Domain

- `GET/POST /api/boards/`
- `GET/PATCH/DELETE /api/boards/{id}/`
- `GET/POST /api/boards/{id}/members/`
- `POST /api/boards/{id}/members/remove/`
- `GET /api/boards/{id}/activity/`
- `GET/POST/PATCH/DELETE /api/columns/`
- `POST /api/columns/reorder/`
- `GET/POST/PATCH/DELETE /api/labels/`
- `GET/POST/PATCH/DELETE /api/cards/`
- `POST /api/cards/{id}/move/`
- `GET/POST/PATCH/DELETE /api/comments/`
- `GET /api/activity-logs/`

## OpenAPI / Swagger

- Schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

## GitHub Actions pipeline

Файл: `.github/workflows/ci.yml`

Содержит:

- backend install + tests
- frontend install + lint + build
- docker compose build

## Ограничения текущей среды (для этой сессии)

В этой среде доступ к внешним пакетным репозиториям ограничен прокси, поэтому `pip install` / `npm install` / Docker build могут не выполниться локально до настройки сети/прокси. Код и конфигурация подготовлены под стандартное окружение.
