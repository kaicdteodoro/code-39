# System Architecture

## Topology

The system is a local Python CLI with a layered structure:

1. CLI layer: parses user input and presents progress/output
2. Application layer: validates range rules and plans the batch
3. Infrastructure layer: renders the PDF and persists registry/history files

## Main modules

- `code39.cli`: Typer commands and terminal UX
- `code39.service`: business rules for ranges, single-reference generation, and duplicate checks
- `code39.formatting`: canonical formatting/parsing of `ATL001` style references
- `code39.pdf`: barcode and PDF rendering through ReportLab
- `code39.registry`: append-only history and generated-reference registry

## Data flow

1. Operator calls `code39 generate`
2. CLI builds a `BatchPlan`
3. Existing references are read from `data/registry.json`
4. A local lock is acquired to prevent overlapping generation runs
5. If duplicates exist and `--force` is not set, generation stops
6. PDF is rendered to `output/code-39-batch.pdf`
7. Successful references are persisted in `data/registry.json`
8. Batch metadata is written to `data/batches.jsonl`, with rollback if the history update fails

## Cross-cutting concerns

- Deterministic numbering from `ATL001` to `ATL500`
- Duplicate prevention by default
- Local lock-based serialization for generation
- Print-oriented layout, not screen-oriented layout
- Local-only execution without network dependencies
