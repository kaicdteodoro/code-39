# API Specification

This project does not expose an HTTP or RPC API.

## Public interface

The supported public interface is the command-line interface:

- `code39 generate`
- `code39 status`
- `code39 history`
- `code39 version`

### `code39 generate`

Main flags:

- `--start` / `--end` to define a contiguous numeric range
- `--limit` for validation batches
- `--reference` for a single explicit reference such as `ATL125`
- `--output` to override the PDF path
- `--png-dir` to override the directory for per-reference PNG files
- `--registry` and `--history` to override persistence paths
- `--png` / `--no-png` to enable or disable PNG export
- `--force` to allow intentional regeneration of already-issued references

### `code39 status`

Shows the number of issued references, number of logged batches, last issued reference, next available reference, and the active persistence paths.

### `code39 history`

Shows the append-only batch log with timestamp, range, quantity, `force` usage, and output path.

## Error model

- invalid range or reference format: process exits with code `1`
- duplicate generation blocked: process exits with code `2`
- storage corruption, lock contention, or persistence failure: process exits with code `3`
- successful execution: process exits with code `0`

## Notes

If this project evolves in the future, any new API should preserve the same business invariants:

- no checksum digit
- default duplicate blocking
- range constrained to `ATL001` through `ATL500` unless the product scope changes explicitly
