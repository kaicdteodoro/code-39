# Testing Strategy

## Goals

The main objective is to protect business invariants:

- valid numbering from `ATL001` to `ATL500`
- no accidental duplicate issuance
- no overlapping generation runs against the same local registry
- append-only batch history
- predictable PDF generation orchestration
- explicit failure when registry/history files are corrupted

## Test layers

- Unit tests for formatting/parsing rules
- Unit tests for batch planning and duplicate detection
- Unit tests for local registry persistence behavior, rollback, and locking
- CLI tests for `generate`, `status`, `history`, and `version`
- PDF smoke tests for content markers, pagination, and empty-batch rejection
- Performance smoke test for full-batch generation within the documented budget

## Environment

- Python 3.11+
- `pytest`
- Local file-system based fixtures using `tmp_path`

## Automation

- `make test`
- `python3 -m pytest`

## CI

CI is already present in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) and runs the test suite in Docker on pushes and pull requests against `main`.

## Operational notes

- Corrupted `data/registry.json` or `data/batches.jsonl` should fail fast with a clear storage error instead of being ignored
- A lock file prevents overlapping `generate` executions from issuing the same reference range concurrently
- The performance smoke test is a budget check, not a precise benchmark; it exists to catch gross regressions
