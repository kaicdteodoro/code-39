# AGENTS.md — code-39

This file guides agents when working on the project.

## Main context source

- `README.md` — overview, commands, and local workflow
- `.pnp/context.json` — product scope, business rules, and non-goals

## Key rules

- Preserve the numbering rule from `ATL001` to `ATL500`
- Keep Code 39 generation without checksum
- Never silently regenerate an already-issued reference without explicit `--force`
- Treat the PDF output as print-ready and stable in layout

## Documentation

- `docs/foundation/vision.md` — product vision and boundaries
- `docs/architecture/` — architecture, flows, and repository structure
- `docs/testing/testing-strategy.md` — testing approach
- `docs/operations/deployment.md` — local operation model
