# Deployment and Operation

## Operating model

This is a local CLI tool executed through Docker. There is no server or background worker requirement for the MVP.

## Expected environments

- Agência workstation on macOS or Windows
- Docker Desktop or Docker Engine with Compose support

## Release model

- versioned through git tags or releases
- distributed as source code plus Docker image build recipe
- operated manually by a technician through `docker compose run`

## Backup and recovery

- back up `data/registry.json` and `data/batches.jsonl`
- regenerate PDFs only with explicit `--force` when business-approved
- keep the generated PDF as the final printable artifact for each batch

## Operational safeguards

- `code39 generate` acquires a local lock before checking duplicates and writing state
- if the process reports a storage error, inspect `data/registry.json` and `data/batches.jsonl` before retrying
- if a crash leaves `data/registry.json.lock` behind, confirm that no generation is still running and then remove the stale lock file manually
