# Repository Structure

## Layout

```text
.
├── .pnp/                  # product context, ai-context, execution metadata
├── data/                  # local persistence files created at runtime
├── docs/                  # architecture and product documentation
├── output/                # generated PDF artifacts
├── src/code39/            # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── formatting.py
│   ├── pdf.py
│   ├── registry.py
│   └── service.py
├── tests/                 # unit, CLI, PDF, and performance smoke tests
├── Makefile
├── pyproject.toml
└── README.md
```

## Conventions

- Business rules live in `service.py` and `formatting.py`
- Side effects live in `pdf.py` and `registry.py`
- CLI orchestration stays inside `cli.py`
- Tests should target small deterministic units first, then cover public CLI flows and print-output smoke cases

## Evolution rules

- Keep the barcode range rules isolated from PDF rendering
- Keep persistence file formats backward compatible whenever possible
- Do not mix future integrations into the current local-first flow without updating `.pnp/context.json`
