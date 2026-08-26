.PHONY: debug release down logs test lint format clean-cache

debug:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d --build
	docker builder prune -f --filter "label=project=sisal_websubmit"
	docker image prune -f --filter "label=project=sisal_websubmit"

release:
	docker compose -f docker-compose.yml -f docker-compose.release.yml up -d --build
	docker builder prune -f --filter "label=project=sisal_websubmit"
	docker image prune -f --filter "label=project=sisal_websubmit"

clean-cache:
	docker builder prune -f --filter "label=project=sisal_websubmit"
	docker image prune -f --filter "label=project=sisal_websubmit"

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml run --rm \
		-v $(CURDIR)/coverage-output:/app/coverage-output \
		api pytest --cov=src --cov-config=.coveragerc \
		--cov-report=term-missing \
		--cov-report=xml:coverage-output/coverage.xml \
		tests/

lint:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml run --rm \
		api ruff check src tests --exclude "src/services/wb_check_v15.py"
	docker compose -f docker-compose.yml -f docker-compose.debug.yml run --rm \
		api ruff format --diff src tests --exclude "src/services/wb_check_v15.py"

format:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml run --rm \
		api ruff check --fix src tests --exclude "src/services/wb_check_v15.py"
	docker compose -f docker-compose.yml -f docker-compose.debug.yml run --rm \
		api ruff format src tests --exclude "src/services/wb_check_v15.py"