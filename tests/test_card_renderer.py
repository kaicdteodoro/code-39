from pathlib import Path

from code39.card_renderer import render_batch_cards_pdf, render_batch_cards_pngs
from code39.card_template import load_card_template
from pypdf import PdfReader
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def test_render_batch_cards_pdf_and_pngs_smoke(tmp_path: Path) -> None:
    template = load_card_template(Path("tests/fixtures/card_template_stub.json"))

    output_pdf = tmp_path / "cards.pdf"
    output_png_dir = tmp_path / "cards-png"

    references = ["ATL001", "ATL002"]

    render_batch_cards_pdf(references, output_pdf, template)
    render_batch_cards_pngs(references, output_png_dir, template)

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0
    assert (output_png_dir / "ATL001.png").exists()
    assert (output_png_dir / "ATL002.png").exists()


def test_render_batch_cards_pdf_with_background(tmp_path: Path) -> None:
    background_pdf = tmp_path / "bg.pdf"
    c = canvas.Canvas(str(background_pdf), pagesize=(70 * mm, 90 * mm))
    c.setFont("Helvetica", 10)
    c.drawString(5 * mm, 85 * mm, "Template")
    c.save()

    template_json = tmp_path / "template.json"
    template_json.write_text(
        """
{
  "card_width_mm": 70.0,
  "card_height_mm": 90.0,
  "barcode_zone_mm": {"x": 15.19, "y": 65.26, "w": 39.63, "h": 19.48, "border_radius_mm": 1.5},
  "barcode_rect_mm": {"x": 17.69, "y": 67.76, "w": 34.63, "h": 14.48},
  "sheet_layout": {
    "page_width_mm": 70.0,
    "page_height_mm": 90.0,
    "margin_left_mm": 0.0,
    "margin_top_mm": 0.0,
    "gap_x_mm": 0.0,
    "gap_y_mm": 0.0,
    "cards_per_row": 1,
    "cards_per_col": 1
  },
  "background_pdf": "bg.pdf"
}
""".strip(),
        encoding="utf-8",
    )

    template = load_card_template(template_json)
    output_pdf = tmp_path / "cards-with-bg.pdf"
    render_batch_cards_pdf(["ATL001"], output_pdf, template)

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0


def test_render_batch_cards_pdf_background_page_index(tmp_path: Path) -> None:
    background_pdf = tmp_path / "bg-multipage.pdf"

    c = canvas.Canvas(str(background_pdf), pagesize=(70 * mm, 90 * mm))
    c.setFont("Helvetica", 12)
    c.drawString(5 * mm, 85 * mm, "PAGE0")
    c.showPage()
    c.drawString(5 * mm, 85 * mm, "PAGE1")
    c.save()

    template_json = tmp_path / "template.json"
    template_json.write_text(
        """
{
  "card_width_mm": 70.0,
  "card_height_mm": 90.0,
  "barcode_zone_mm": {"x": 15.19, "y": 65.26, "w": 39.63, "h": 19.48, "border_radius_mm": 1.5},
  "barcode_rect_mm": {"x": 15.69, "y": 65.76, "w": 38.43, "h": 18.48},
  "sheet_layout": {
    "page_width_mm": 70.0,
    "page_height_mm": 90.0,
    "margin_left_mm": 0.0,
    "margin_top_mm": 0.0,
    "gap_x_mm": 0.0,
    "gap_y_mm": 0.0,
    "cards_per_row": 1,
    "cards_per_col": 1
  },
  "background_pdf": "bg-multipage.pdf",
  "background_pdf_page_index": 1
}
        """.strip(),
        encoding="utf-8",
    )

    template = load_card_template(template_json)
    output_pdf = tmp_path / "out.pdf"
    render_batch_cards_pdf(["ATL001"], output_pdf, template)

    assert output_pdf.exists()

    reader = PdfReader(str(output_pdf))
    text = "".join((page.extract_text() or "") for page in reader.pages)
    assert "PAGE1" in text
    assert "PAGE0" not in text

