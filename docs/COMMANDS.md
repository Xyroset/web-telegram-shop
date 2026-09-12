# Makefile Commands Reference

This project utilizes a `Makefile` to encapsulate and standardize complex Docker Compose commands, Python scripts, and QA checks. Using these commands ensures that your environment matches the CI/CD pipeline and adheres to the project's architecture rules.

## Table of Contents
1. [Variables](#variables)
2. [Initialization & Building](#1-initialization--building)
3. [Starting, Stopping & Restarts](#2-starting-stopping--restarts)
4. [Quality Assurance (Checks, Linters, Tests)](#3-quality-assurance-checks-linters-tests)
5. [Logs & Shell Access](#4-logs--shell-access)
6. [Django Management & Database](#5-django-management--database)
7. [Translations & Locales](#6-translations--locales)
8. [Frontend Specific Commands](#7-frontend-specific-commands)

---

## Variables
Some commands accept variables to customize their behavior:
- `ARGS="--build"`: Passes extra arguments to Docker Compose or underlying scripts (e.g., specific test paths for Pytest).
- `CONTAINER="frontend"`: Specifies the target service for logs, shells, or builds. Defaults to `backend`.
- `LANG="es"`: Specifies the target language for translation commands.

---

## 1. Initialization & Building

Before starting the project for the first time, you must initialize the environment and build the Docker images. These commands **do not** require Docker containers to be running.

- `make init` - Runs the Python initialization script (`backend/scripts/init_project.py`) to generate `.env` files from templates and create secure keys.
- `make build-dev` - Builds or rebuilds the Docker images for the development profile.
- `make build-prod` - Builds or rebuilds the Docker images for the production profile.
- `make build-standalone` - Builds or rebuilds the Docker images for the standalone profile.

---

## 2. Starting, Stopping & Restarts

These commands manage the lifecycle of your Docker containers based on your selected deployment profile.

### Start (Foreground with logs)
- `make start-dev` - Starts the development environment and attaches to the logs.
- `make start-prod` - Starts the production environment and attaches to the logs.
- `make start-standalone` - Starts the standalone environment and attaches to the logs.

### Start (Background / Detached)
- `make up-dev` - Starts the dev containers in the background (`-d`).
- `make up-prod` - Starts the prod containers in the background (`-d`).
- `make up-standalone` - Starts the standalone containers in the background (`-d`).

### Stop & Teardown
- `make stop` - Gracefully stops all running Docker containers without removing them.
- `make down` - Stops and removes all Docker containers, networks, and orphaned volumes.

### Restarts
- `make restart-stop-dev` / `prod` / `standalone` - Stops the containers and immediately starts them again, following logs.
- `make restart-down-dev` / `prod` / `standalone` - Completely brings down the containers (removing them) and starts them fresh, following logs.

---

## 3. Quality Assurance (Checks, Linters, Tests)

**Requirement:** The respective containers (backend/frontend) must be running to execute these commands.

- `make check` - Runs the full QA suite (linters, type checkers, and tests) for both Backend and Frontend. Always run this before submitting a Pull Request.
- `make check-backend` - Runs Ruff (linter), Mypy (type checker), and Pytest (tests) for the Django backend.
- `make check-frontend` - Runs Prettier (formatter) and ESLint (linter) for the React frontend.
- `make lint-backend` - Runs the `ruff` linter on the backend code to enforce style rules.
- `make typecheck-backend` - Runs `mypy` on the backend code to ensure strict typing compliance.
- `make lint-frontend` - Runs `npm run format` and `npm run lint` on the frontend codebase.
- `make test-backend` - Executes the Pytest test suite. *Example with args: `make test-backend ARGS="apps/orders/tests/"`*

---

## 4. Logs & Shell Access

**Requirement:** Containers must be running.

- `make logs` - Streams the logs of the target container. Defaults all containers. *Example: `make logs CONTAINER=frontend`*
- `make shell` - Opens an interactive bash shell inside the target container. Defaults to the backend. *Example: `make shell CONTAINER=celery`*

---

## 5. Django Management & Database

**Requirement:** The backend container must be running.

- `make django-shell` - Opens an interactive Django Python shell (`manage.py shell`) loaded with the project's context.
- `make create-superuser` - Prompts for credentials to create a new Django superuser (admin).
- `make promote-superuser` - Grants superuser privileges to an existing user via Telegram ID or Username.
- `make migrate` - Generates new database migrations (`makemigrations`) and applies them (`migrate`).
- `make load-backup` - Loads database state from a JSON backup file. *Example: `make load-backup ARGS="custom_backup.json"`*
- `make save-backup` - Dumps the current database state to `backend/db_backup.json`.
- `make reload-config` - Reloads the dynamic shop configuration from the database into the active cache.

---

## 6. Translations & Locales

**Requirement:** The backend container must be running. The `LANG` variable is mandatory for `translate-*` commands.

👉 **For detailed information on how translation files (`en.json`), AI auto-translation logic, and manual overrides work, please refer to the [Configuration Guide (CONFIG.md#3-localization--translations-json)](CONFIG.md#3-localization--translations-json).**

- `make translate-frontend LANG=es` - Translates frontend localization files into the specified language (e.g., Spanish) using the auto-translation script.
- `make translate-backend LANG=es` - Generates Django `.po` files, translates them, and compiles them into `.mo` files.
- `make translate-all LANG=es` - Executes both frontend and backend translation pipelines in a single command.
- `make update-locales-frontend` - Updates and synchronizes translation keys in the frontend without running the auto-translator.
- `make update-locales-backend` - Updates and synchronizes translation keys in the backend.
- `make update-locales-all` - Synchronizes localization keys across the entire monorepo.

---

## 7. Frontend Specific Commands

**Requirement:** The frontend container must be running.

- `make sync-api-schema` - Fetches the latest OpenAPI schema from the backend and updates the frontend API clients accordingly.
