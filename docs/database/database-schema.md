# Persistence Model

This project does not use a relational database. Persistence is file-based and local.

## Files

### `data/registry.json`

Stores the set of already-issued references.

```json
{
  "generated_references": [
    "ATL001",
    "ATL002"
  ]
}
```

### `data/batches.jsonl`

Append-only log, one JSON object per line.

```json
{"timestamp":"2026-03-18T12:00:00+00:00","quantity":5,"first_reference":"ATL001","last_reference":"ATL005","output_file":"output/code-39-batch.pdf","force":false}
```

## Design rationale

- `registry.json` is optimized for duplicate checks
- `batches.jsonl` is optimized for immutable historical traceability
- Both files are human-readable and easy to back up

## Failure handling

- `registry.json` is validated before reads; malformed JSON should stop the CLI with a storage error
- `batches.jsonl` is validated line by line; malformed records should stop the CLI with a storage error that points to the failing line
- batch registration updates `registry.json` and `batches.jsonl` with rollback if the history write fails after the registry write
- `registry.json.lock` is used during generation to prevent overlapping runs against the same local state
