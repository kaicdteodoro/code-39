# code-39

Python CLI for generating Code 39 barcodes without checksum for Atlântico Gastrobar tabs (`ATL001` to `ATL500`).

The project creates a print-ready PDF batch, exports one PNG per reference, blocks accidental duplicates, and keeps a persistent local history of generated batches.

## Container-first workflow

This project is designed to run fully in Docker. Local Python is optional.

### Build the image

```bash
make build
```

### Run the full official batch

```bash
make generate
```

### Run a validation batch

```bash
make generate-sample
```

### Run tests

```bash
make test
```

The automated suite now covers:

- CLI happy-path and duplicate blocking/forcing
- registry/history corruption handling
- PDF pagination and footer rendering
- full-batch performance budget smoke check

### Inspect operational state

```bash
make status
make history
```

## Structure

- `.pnp/context.json` — source of truth for product, scope, constraints, and quality attributes
- `.pnp/ai-context.json` — AI-oriented derived context
- `src/code39/` — CLI, batch planning, PDF rendering, and persistence
- `tests/` — unit tests for numbering rules and registry behavior
- `docs/` — PNP-generated architecture and product documentation

## Quick start

```bash
make build
```

Generate the full official batch:

```bash
docker compose run --rm code39 generate
```

Generate only the first 5 tabs for validation:

```bash
docker compose run --rm code39 generate --limit 5
```

This command creates:

- a single PDF batch
- a sibling directory with one PNG per generated reference

Generate a single reference:

```bash
docker compose run --rm code39 generate --reference ATL125
```

Inspect local registry:

```bash
docker compose run --rm code39 status
docker compose run --rm code39 history
```

If the CLI reports a storage error, inspect and restore:

- `data/registry.json` when duplicate checks or status reads fail
- `data/batches.jsonl` when history reads fail
- `data/registry.json.lock` if a previous interrupted run left a stale lock behind

## Main outputs

- `output/code-39-batch.pdf` — print-ready PDF
- `output/code-39-batch-png/` — one PNG per generated reference
- `data/registry.json` — persistent registry of generated references
- `data/batches.jsonl` — append-only batch history

The repository is mounted into the container through Docker Compose, so generated artifacts remain available locally and Docker commands can also access `tests/`, `docs/`, and project files directly.

## Development

```bash
make build
make install
make test
make generate-sample
```

## Optional local Python workflow

If you still want to run the project without Docker:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m code39.cli generate --limit 5
python3 -m pytest
```
