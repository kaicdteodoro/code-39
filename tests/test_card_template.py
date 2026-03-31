from pathlib import Path

import pytest

from code39.card_template import CardTemplateError, load_card_template


def test_load_card_template_stub(tmp_path: Path) -> None:
    template_path = Path("tests/fixtures/card_template_stub.json")
    template = load_card_template(template_path)

    assert template.card_width_mm == 80.0
    assert template.card_height_mm == 50.0
    assert template.barcode_rect_mm.w > 0
    assert template.label_text_rect_mm is not None
    assert template.sheet_layout.cards_per_row == 2
    assert template.sheet_layout.cards_per_col == 4


def test_load_card_template_rejects_missing_card_size(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"barcode_rect_mm":{"x":0,"y":0,"w":10,"h":10},"sheet_layout":{}}',
        encoding="utf-8",
    )

    with pytest.raises(CardTemplateError):
        load_card_template(bad)


def test_load_production_template_with_background_path() -> None:
    template = load_card_template(Path("assets/templates/verso_template_marcado_v4.json"))

    assert template.card_width_mm == 70.0
    assert template.card_height_mm == 90.0
    assert template.background_pdf is not None
    assert template.background_pdf.name == "verso_template_marcado_v4.pdf"
    assert template.barcode_zone_mm is not None

