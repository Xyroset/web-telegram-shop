.DEFAULT_GOAL := help

SHELL := /bin/bash
MAKEFLAGS += --no-print-directory

ifeq ($(OS),Windows_NT)
	PYTHON_CMD := python
else
	PYTHON_CMD := python3
endif

define DRAW_LINE
	@$(PYTHON_CMD) -c "import shutil; w = shutil.get_terminal_size((80, 20)).columns; text = ' $(1) '; side = max(0, (w - len(text)) // 2); print('\033[96m' + '-' * side + text + '-' * (w - side - len(text)) + '\033[0m')"
endef

define DRAW_LINE_TITLE
	@$(PYTHON_CMD) -c "import shutil; w = shutil.get_terminal_size((80, 20)).columns; text = ' $(1) '; side = max(0, (w - len(text)) // 2); print('\033[92m' + '=' * side + text + '=' * (w - side - len(text)) + '\033[0m')"
endef

.PHONY: help init build-dev build-prod build-standalone \
	start-dev start-prod start-standalone \
	up-dev up-prod up-standalone \
	stop down \
	restart-stop-dev restart-stop-prod restart-stop-standalone \
	restart-down-dev restart-down-prod restart-down-standalone \
	check check-backend check-frontend \
	lint-backend typecheck-backend lint-frontend test-backend \
	logs shell \
	translate-frontend translate-backend translate-all \
	update-locales-frontend update-locales-backend update-locales-all \
	sync-api-schema \
	django-shell create-superuser promote-superuser migrate load-backup save-backup reload-config

# --- Helpers ---

help:
	@echo "Available commands:"
	@echo "  make init                     - Initialize project (scripts/init_project.py) (No Docker running needed)"
	@echo "  make build-dev                - Build or rebuild dev Docker images (No Docker running needed)"
	@echo "  make build-prod               - Build or rebuild prod Docker images (No Docker running needed)"
	@echo "  make build-standalone         - Build or rebuild standalone Docker images (No Docker running needed)"
	@echo "  make start-dev                - Start development environment and follow logs"
	@echo "  make start-prod               - Start production environment and follow logs"
	@echo "  make start-standalone         - Start standalone environment and follow logs"
	@echo "  make up-dev                   - Start dev containers in background"
	@echo "  make up-prod                  - Start prod containers in background"
	@echo "  make up-standalone            - Start standalone containers in background"
	@echo "  make stop                     - Stop Docker containers"
	@echo "  make down                     - Stop and remove Docker containers"
	@echo "  make restart-stop-dev         - Stop containers, start dev containers and follow logs"
	@echo "  make restart-stop-prod        - Stop containers, start prod containers and follow logs"
	@echo "  make restart-stop-standalone  - Stop containers, start standalone containers and follow logs"
	@echo "  make restart-down-dev         - Bring down, start dev containers and follow logs"
	@echo "  make restart-down-prod        - Bring down, start prod containers and follow logs"
	@echo "  make restart-down-standalone  - Bring down, start standalone containers and follow logs"
	@echo "  make logs                     - View output from containers (Require - Containers must be running)"
	@echo "  make check                    - Quick run linters, type checkers and tests (Require - Containers running)"
	@echo "  make check-backend            - Run backend lint, typecheck, and tests (Require - Backend running)"
	@echo "  make check-frontend           - Run frontend lint and formatter (Require - Frontend running)"
	@echo "  make lint-backend             - Run backend linter [Ruff] (Require - Backend running)"
	@echo "  make typecheck-backend        - Run backend type checker [Mypy] (Require - Backend running)"
	@echo "  make lint-frontend            - Run frontend formatter and linter [Eslint and Prettier] (Require - Frontend running)"
	@echo "  make test-backend             - Run backend tests [Pytest] (Require - Backend running)"
	@echo "  make shell                    - Open a bash shell in a container (Require - Container running)"
	@echo "  make translate-frontend       - Run auto-translation script for frontend (Require: LANG=es, Backend running)"
	@echo "  make translate-backend        - Run auto-translation script for backend (Require: LANG=es, Backend running)"
	@echo "  make translate-all            - Run auto-translation for both backend and frontend (Require: LANG=es, Backend running)"
	@echo "  make update-locales-frontend  - Run locale update script for frontend (Require - Backend running)"
	@echo "  make update-locales-backend   - Run locale update script for backend (Require - Backend running)"
	@echo "  make update-locales-all       - Run locale update script for both (Require - Backend running)"
	@echo "  make sync-api-schema          - Sync frontend API schema (Require - Frontend running)"
	@echo "  make django-shell             - Open a Django shell in the backend container (Require - Backend running)"
	@echo "  make create-superuser         - Create a new Django superuser (Require - Backend running)"
	@echo "  make promote-superuser        - Grant superuser to an existing user (Require - Backend running)"
	@echo "  make migrate                  - Make and apply Django migrations (Require - Backend running)"
	@echo "  make load-backup              - Load database data from a JSON backup (Require - Backend running)"
	@echo "  make save-backup              - Dump current database data to JSON (Require - Backend running)"
	@echo "  make reload-config            - Reload shop configuration (Require - Backend running)"
	@echo ""
	@echo "Variables:"
	@echo "  ARGS='args'                   - Extra args passed to docker compose or scripts (logs, up, down, stop, pytest)"
	@echo "  CONTAINER='name'              - Target service for logs/shell/builds (default: backend)"

# --- Starts & Builds ---

init:
	@cd backend/scripts && $(PYTHON_CMD) init_project.py

build-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build $(CONTAINER)
build-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build $(CONTAINER)
build-standalone:
	docker compose -f docker-compose.yml -f docker-compose.standalone.yml build $(CONTAINER)

start-dev: up-dev logs
start-prod: up-prod logs
start-standalone: up-standalone logs

up-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --remove-orphans $(ARGS) 

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans $(ARGS)

up-standalone:
	docker compose -f docker-compose.yml -f docker-compose.standalone.yml up -d --remove-orphans $(ARGS)

# --- Restarts & Stops ---

stop:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.prod.yml -f docker-compose.standalone.yml stop $(CONTAINER)

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.prod.yml -f docker-compose.standalone.yml down $(CONTAINER)

restart-stop-dev: stop up-dev logs
restart-stop-prod: stop up-prod logs
restart-stop-standalone: stop up-standalone logs
restart-down-dev: down up-dev logs
restart-down-prod: down up-prod logs
restart-down-standalone: down up-standalone logs

# --- Checks ---

check:
	@$(call DRAW_LINE_TITLE,Backend)
	@echo ""
	@$(MAKE) check-backend
	@echo ""
	@$(call DRAW_LINE_TITLE,Frontend)
	@echo ""
	@$(MAKE) check-frontend

check-backend:
	@$(call DRAW_LINE,Ruff)
	@$(MAKE) lint-backend
	@echo ""
	@$(call DRAW_LINE,Mypy)
	@$(MAKE) typecheck-backend
	@echo ""
	@$(call DRAW_LINE,Tests)
	@$(MAKE) test-backend

check-frontend:
	@$(call DRAW_LINE,Lint & Format)
	@$(MAKE) lint-frontend

# --- Lints & Formatters ---

lint-backend:
	docker compose exec backend ruff check .

typecheck-backend: ARGS ?= .
typecheck-backend:
	docker compose exec backend mypy $(ARGS) --show-traceback

lint-frontend:
	docker compose exec frontend npm run format && docker compose exec frontend npm run lint

# --- QA ---

test-backend:
	docker compose exec backend pytest -v -s $(ARGS)

# --- Settings & View ---

logs:
	docker compose logs -f $(CONTAINER)

shell: CONTAINER ?= backend
shell:
	docker compose exec $(CONTAINER) bash

# --- Translation & Locales ---

translate-frontend:
	$(if $(LANG),,$(error LANG is not set. Use: make translate-frontend LANG=es))
	docker compose exec backend python scripts/auto_translate.py $(LANG) --type frontend
	@$(MAKE) reload-config

translate-backend:
	$(if $(LANG),,$(error LANG is not set. Use: make translate-backend LANG=es))
	docker compose exec backend python manage.py makemessages -l $(LANG)
	docker compose exec backend python scripts/auto_translate.py $(LANG) --type backend
	docker compose exec backend python manage.py compilemessages

translate-all:
	$(if $(LANG),,$(error LANG is not set. Use: make translate-all LANG=es))
	@$(call DRAW_LINE_TITLE,Backend)
	docker compose exec backend python manage.py makemessages -l $(LANG)
	docker compose exec backend python scripts/auto_translate.py $(LANG) --type backend
	docker compose exec backend python manage.py compilemessages
	@$(call DRAW_LINE_TITLE,Frontend)
	docker compose exec backend python scripts/auto_translate.py $(LANG) --type frontend
	@$(MAKE) reload-config

update-locales-frontend:
	docker compose exec backend python scripts/update_locales.py --type frontend
	@$(MAKE) reload-config

update-locales-backend:
	docker compose exec backend python scripts/update_locales.py --type backend
	docker compose exec backend python manage.py compilemessages

update-locales-all:
	@$(call DRAW_LINE_TITLE,Backend)
	docker compose exec backend python scripts/update_locales.py --type backend
	docker compose exec backend python manage.py compilemessages
	@$(call DRAW_LINE_TITLE,Frontend)
	docker compose exec backend python scripts/update_locales.py --type frontend
	@$(MAKE) reload-config

# --- Frontend Commands ---

sync-api-schema:
	docker compose exec frontend npm run api:sync

# --- Backend (Django) Commands ---

django-shell:
	docker compose exec backend python manage.py shell

create-superuser:
	docker compose exec backend python manage.py createsuperuser

promote-superuser:
	docker compose exec backend python manage.py promotesuperuser 

migrate:
	docker compose exec backend python manage.py makemigrations && docker compose exec backend python manage.py migrate

load-backup: ARGS ?= db_backup.json
load-backup:
	docker compose exec backend python manage.py loaddata $(ARGS)

save-backup: ARGS ?= backend/db_backup.json
save-backup:
	docker compose exec backend python manage.py dumpdata > $(ARGS)

reload-config:
	docker compose exec backend python manage.py reload_shop_config