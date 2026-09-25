install:
	pip install .[dev]

lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest -q

docker-build:
	docker build -t earthquake-mqtt-fetcher:dev .

docker-run:
	docker compose up
