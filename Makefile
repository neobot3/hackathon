.DEFAULT_GOAL := help

BACKEND      := backend
FRONTEND     := frontend
VENV         := $(BACKEND)/.venv
PY           := $(VENV)/bin/python
RUFF         := $(VENV)/bin/ruff
STAMP        := $(VENV)/.installed

DB_CONTAINER := postgres-db
DB_IMAGE     := postgres:18
DB_PASSWORD  ?= my_suP3r_secure_p@ssw0rd
API_IMAGE    := techrep-backend
WEB_IMAGE    := techrep-frontend
VITE_API_BASE_URL ?= http://localhost:8000

.PHONY: help install backend-install frontend-install dev backend frontend \
	    lint format backend-lint backend-format frontend-lint frontend-format \
	    db-up db-down db-reset db-shell docker-build docker-run \
            frontend-docker-build clean

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	    awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- Setup ----------

install: backend-install frontend-install ## Install backend and frontend dependencies

# Reinstalls only when requirements.txt changes.
$(STAMP): $(BACKEND)/requirements.txt
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r $< ruff
	touch $@

backend-install: $(STAMP) ## Create backend venv and install packages plus ruff

$(BACKEND)/.env:
	cp $(BACKEND)/.env.example $@

frontend-install: ## npm install in frontend/
	cd $(FRONTEND) && npm install

# ---------- Run ----------

dev: ## Run backend and frontend together (Ctrl-C stops both)
	$(MAKE) -j2 backend frontend

backend: $(STAMP) $(BACKEND)/.env ## Run FastAPI with reload on :8000
	cd $(BACKEND) && .venv/bin/uvicorn main:app --reload

frontend: ## Run the frontend dev server (npm run dev)
	cd $(FRONTEND) && npm run dev --if-present

# ---------- Lint and format ----------

lint: backend-lint frontend-lint ## Lint and check formatting (no changes)

format: backend-format frontend-format ## Auto-fix lint issues and format code

backend-lint: $(STAMP)
	$(RUFF) check $(BACKEND)
	$(RUFF) format --check $(BACKEND)

backend-format: $(STAMP)
	$(RUFF) check --fix $(BACKEND)
	$(RUFF) format $(BACKEND)

frontend-lint:
	cd $(FRONTEND) && npm run lint --if-present

frontend-format:
	cd $(FRONTEND) && npm run format --if-present

# ---------- Database ----------

db-up: ## Start Postgres in Docker (creates the container on first run)
	@docker start $(DB_CONTAINER) 2>/dev/null || docker run -d --name $(DB_CONTAINER) \
	    -e POSTGRES_USER=techrep \
	    -e POSTGRES_PASSWORD=$(DB_PASSWORD) \
	    -e POSTGRES_DB=techrep \
	    -p 5432:5432 \
	    -v "$(CURDIR)/db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
	    $(DB_IMAGE)

db-down: ## Stop the Postgres container
	docker stop $(DB_CONTAINER)

db-reset: ## Delete the container and recreate the schema from init.sql
	docker rm -f $(DB_CONTAINER)
	$(MAKE) db-up

db-shell: ## Open psql in the database container
	docker exec -it $(DB_CONTAINER) psql -U techrep -d techrep

# ---------- Docker (backend) ----------

docker-build: ## Build the backend image
	docker build -t $(API_IMAGE) $(BACKEND)

frontend-docker-build: ## Build the frontend image (override VITE_API_BASE_URL=...)
	docker build -t $(WEB_IMAGE) --build-arg VITE_API_BASE_URL=$(VITE_API_BASE_URL) $(FRONTEND)

docker-run: $(BACKEND)/.env ## Run the backend image against the local database
	docker run --rm -p 8000:8000 --env-file $(BACKEND)/.env \
	    -e DB_HOST=host.docker.internal $(API_IMAGE)

clean: ## Remove Python caches
	find $(BACKEND) -type d -name __pycache__ -not -path '*/.venv/*' -prune -exec rm -rf {} +
	rm -rf .ruff_cache $(BACKEND)/.ruff_cache