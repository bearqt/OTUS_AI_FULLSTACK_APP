# MiniTrello Architecture

## Overview

MiniTrello is a fullstack Kanban-style task board application with:

- `backend` (Django + Django REST Framework)
- `frontend` (React + Vite + Radix UI)
- `db` (PostgreSQL, via Docker Compose)

The system is split into API-first backend and SPA frontend. Authentication uses JWT (SimpleJWT).

## Backend Architecture

### Django project structure

- `backend/config` - Django settings/urls/wsgi/asgi
- `backend/apps/users` - custom user model and JWT-related auth endpoints
- `backend/apps/kanban` - domain models, serializers, filters, viewsets, seed data, tests

### Domain model (kanban)

Core entities:

- `Board`
- `BoardMembership`
- `BoardColumn`
- `Card`
- `Label`
- `CardLabel` (through table)
- `CardComment`
- `ActivityLog`

### API layer

DRF `ModelViewSet` is used for CRUD endpoints:

- `boards`
- `columns`
- `labels`
- `cards`
- `comments`
- `activity-logs` (read-only)

Auth endpoints:

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

### Validation strategy

Validation exists on both serializer and UI form level.

Backend-specific rules:

- card `assignee` must be a member of the card's board
- card labels must belong to the same board as the card
- cross-board card move is forbidden
- comment body / titles / names cannot be blank after trimming

### Ordering and drag-and-drop support

Columns and cards store `position`.

Reordering and movement are implemented through service functions:

- `place_column(...)`
- `place_card(...)`
- `normalize_board_columns(...)`
- `normalize_column_cards(...)`

This keeps ordering logic centralized and consistent for API calls and seed generation.

### Activity logging

All major mutations write records into `ActivityLog` with:

- actor user
- action enum
- optional related card/column/comment
- `details` JSON payload (structured metadata)

## Frontend Architecture

### Stack

- React SPA (Vite)
- React Router
- Radix UI primitives (`Dialog`, `Select`, `Tabs`)
- Native drag-and-drop (HTML5 DnD)

### Main pages

- `AuthPage` (`/login`, `/register`)
- `BoardsPage` (`/boards`)
- `BoardPage` (`/boards/:boardId`)

### State approach

- `AuthProvider` stores JWT tokens and current user in `localStorage`
- `authFetch` wraps API requests and refreshes access token automatically on `401`
- `BoardPage` keeps board details, filters, comments and activity in local component state

### UX flows

- Create/list boards
- Add columns and labels
- Create/edit/delete cards (dialog)
- Drag cards within and across columns
- Add comments to cards
- View board activity log
- Filter visible cards by priority/label/assignee/deadline

## API Documentation

OpenAPI schema and Swagger UI are generated using `drf-spectacular`:

- `GET /api/schema/`
- `GET /api/docs/`

## Deployment / Runtime

`docker-compose.yml` runs exactly 3 containers:

1. PostgreSQL
2. Django backend (migrations + seed on startup)
3. Frontend (Nginx serving built SPA and proxying `/api` to backend)

## Testing Strategy

Backend unit/integration tests cover:

- auth registration/login/me
- access scoping by board membership
- card validation rules
- filters
- card movement
- comments activity logging
- seed command counts

Frontend testing is currently manual smoke test oriented (Playwright step described in workflow/process docs).
