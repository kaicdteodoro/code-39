# Performance Model

## Targets

- Generate the full batch of 500 references in under 30 seconds on a standard workstation
- Produce a final PDF with layout stability suitable for print

## Verifiable criteria

- the automated suite must render a full 500-reference PDF in under 30 seconds in the project runtime
- PDFs must include deterministic page footers so pagination regressions are detectable in tests
- a batch with up to 10 labels must fit on one page; 11 labels must spill to a second page
- the rendered artifact must contain the expected textual reference markers for sampled labels

## Workload

- Main workload is batch generation of up to 500 references
- Typical usage is infrequent and operator-triggered
- Duplicate checks are local and in-memory after reading a small JSON file

## Bottlenecks

- PDF rendering is the dominant operation
- File-system writes are small and should not be significant
- Barcode rendering density may affect generation speed more than business logic

## Mitigations

- Keep batch planning pure and lightweight
- Persist only minimal local state
- Avoid network or external-service dependencies entirely
- Keep PDF output deterministic enough for smoke-level byte/content assertions in tests
- Catch storage corruption and lock contention early so failed runs do not silently distort timings or state
