.PHONY: infra-up infra-down clean

# Start local infrastructure (Kafka, Redis, ClickHouse, Qdrant)
infra-up:
	docker-compose -f infrastructure/docker-compose.yml up -d

# Stop local infrastructure
infra-down:
	docker-compose -f infrastructure/docker-compose.yml down

# Clean build artifacts
clean:
	@echo "Cleaning up build and temporary directories..."
	@powershell -Command "Get-ChildItem -Recurse -Directory -Filter 'build' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Recurse -Directory -Filter 'target' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Recurse -Directory -Filter 'node_modules' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
