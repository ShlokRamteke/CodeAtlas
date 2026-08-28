PODMAN ?= /opt/podman/bin/podman
COMPOSE ?= $(PODMAN) compose -f compose.yaml

.PHONY: up down restart build logs ps test health clean

up:
	$(COMPOSE) up -d

build:
	$(COMPOSE) build

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

health:
	@curl -s http://localhost:8000/api/v1/health | jq .
	@curl -s -I http://localhost:3000 | head -n 5

test:
	cd backend && source .venv/bin/activate && pytest -v

clean:
	$(COMPOSE) down -v
