.PHONY: debug release down logs test test-new

debug:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d --build

release:
	docker compose -f docker-compose.yml -f docker-compose.release.yml up -d --build

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