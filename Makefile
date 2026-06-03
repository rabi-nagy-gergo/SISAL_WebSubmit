.PHONY: debug release down logs

debug:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d --build

release:
	docker compose -f docker-compose.yml -f docker-compose.release.yml up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api