from pathlib import Path

import pytest
from pypdf import PdfReader

from code39.pdf import derive_png_output_dir, render_batch_pdf, render_batch_pngs, render_reference_png


def test_render_batch_pdf_creates_non_empty_file(tmp_path: Path) -> None:
    output_path = tmp_path / "batch.pdf"

    render_batch_pdf(["ATL001", "ATL002", "ATL003"], output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_render_batch_pdf_includes_references(tmp_path: Path) -> None:
    output_path = tmp_path / "batch.pdf"

    render_batch_pdf(["ATL001", "ATL002"], output_path)

    reader = PdfReader(str(output_path))
    text = "".join(p.extract_text() or "" for p in reader.pages)
    assert "ATL001" in text
    assert "ATL002" in text


def test_render_batch_pdf_paginates_after_ten_labels(tmp_path: Path) -> None:
    output_path = tmp_path / "batch.pdf"
    references = [f"ATL{number:03d}" for number in range(1, 12)]

    render_batch_pdf(references, output_path)

    reader = PdfReader(str(output_path))
    assert len(reader.pages) >= 2


def test_render_batch_pdf_rejects_empty_batches(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_batch_pdf([], tmp_path / "batch.pdf")


def test_render_reference_png_creates_non_empty_file(tmp_path: Path) -> None:
    output_path = tmp_path / "ATL001.png"

    render_reference_png("ATL001", output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_render_batch_pngs_creates_one_file_per_reference(tmp_path: Path) -> None:
    output_dir = tmp_path / "png"

    render_batch_pngs(["ATL001", "ATL002"], output_dir)

    assert (output_dir / "ATL001.png").exists()
    assert (output_dir / "ATL002.png").exists()


def test_derive_png_output_dir_matches_pdf_name(tmp_path: Path) -> None:
    output_path = tmp_path / "batch.pdf"

    assert derive_png_output_dir(output_path) == tmp_path / "batch-png"
