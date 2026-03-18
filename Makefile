.PHONY: help build install test generate generate-sample status history shell clean

help:
	@echo "code-39 commands:"
	@echo "  make build            # build Docker image"
	@echo "  make install          # install project locally with dev dependencies"
	@echo "  make test             # run unit tests in Docker"
	@echo "  make generate         # generate the full ATL001..ATL500 batch in Docker"
	@echo "  make generate-sample  # generate first 5 references in Docker"
	@echo "  make status           # inspect registry state in Docker"
	@echo "  make history          # inspect batch history in Docker"
	@echo "  make shell            # open a shell inside the image"
	@echo "  make clean            # remove generated outputs"

build:
	mkdir -p output data
	docker compose build

install:
	python3 -m pip install -e .[dev]

test:
	mkdir -p output data
	docker compose run --rm --entrypoint python code39 -m pytest tests

generate: build
	docker compose run --rm code39 generate

generate-sample: build
	docker compose run --rm code39 generate --limit 5

status: build
	docker compose run --rm code39 status

history: build
	docker compose run --rm code39 history

shell: build
	docker compose run --rm --entrypoint /bin/sh code39

clean:
	rm -rf output data/registry.json data/batches.jsonl .pytest_cache
