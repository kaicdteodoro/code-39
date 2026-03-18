# Onboarding

`code-39` is a local Python CLI used to generate the official barcode tabs for Atlântico Gastrobar.

## What matters most

- The only valid production range is `ATL001` through `ATL500`
- Barcodes must be Code 39 without checksum
- Duplicate issuance must be blocked unless `--force` is explicitly used
- The generated PDF is the final print artifact

## Core commands

```bash
make build
make generate
make status
make history
make test
```

## State files

- `data/registry.json` stores all issued references
- `data/batches.jsonl` stores append-only batch logs
- `output/code-39-batch.pdf` is the default output artifact

These directories are bind-mounted into Docker, so runtime artifacts remain on the host machine.

## Code map

- `src/code39/cli.py` orchestrates commands and terminal UX
- `src/code39/service.py` contains batch planning rules
- `src/code39/formatting.py` owns reference formatting/parsing
- `src/code39/pdf.py` renders printable labels
- `src/code39/registry.py` persists registry and batch history
