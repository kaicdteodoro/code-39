from pathlib import Path
from time import perf_counter

from code39.pdf import render_batch_pdf
from code39.service import build_batch_plan


def test_full_batch_pdf_generation_stays_within_operational_budget(tmp_path: Path) -> None:
    plan = build_batch_plan()
    output_path = tmp_path / "full-batch.pdf"

    started_at = perf_counter()
    render_batch_pdf(plan.references, output_path)
    elapsed_seconds = perf_counter() - started_at

    assert output_path.exists()
    assert elapsed_seconds < 30
