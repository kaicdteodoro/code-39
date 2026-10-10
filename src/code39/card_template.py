"""Card template model and validation (in millimeters)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RectMM:
    """A rectangle expressed in millimeters with origin at top-left."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class SheetLayout:
    """How to place cards on a printable sheet/page."""

    page_width_mm: float
    page_height_mm: float
    margin_left_mm: float
    margin_top_mm: float
    gap_x_mm: float
    gap_y_mm: float
    cards_per_row: int
    cards_per_col: int


@dataclass(frozen=True)
class CardStyle:
    """Optional style parameters for the card renderer."""

    border_radius_mm: float = 2.0
    border_width_pt: float = 0.5


@dataclass(frozen=True)
class BarcodeOptions:
    """Options for Code 39 barcode rendering (python-barcode ImageWriter)."""

    module_width_mm: float = 0.35
    module_height_mm: float = 10.0
    quiet_zone_mm: float = 3.5
    font_size_pt: float = 6.0
    text_distance_mm: float = 1.5
    write_text: bool = True
    dpi: int = 300


@dataclass(frozen=True)
class CardTemplate:
    """Template definition for a single card."""

    card_width_mm: float
    card_height_mm: float
    barcode_rect_mm: RectMM
    label_text_rect_mm: RectMM | None
    sheet_layout: SheetLayout
    card_style: CardStyle = CardStyle()
    background_pdf: Path | None = None
    # Some background PDFs are multi-page (e.g., front+verso in the same file).
    # The renderer can select which page to use as the base canvas.
    background_pdf_page_index: int = 0
    background_png: Path | None = None
    barcode_zone_mm: RectMM | None = None
    barcode_zone_radius_mm: float = 1.5
    barcode_options: BarcodeOptions = BarcodeOptions()


class CardTemplateError(ValueError):
    """Raised when the card template JSON is invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CardTemplateError(f"Could not read template file: {path}") from error
    except json.JSONDecodeError as error:
        raise CardTemplateError(
            f"Template file contains invalid JSON: {path}"
        ) from error

    if not isinstance(raw, dict):
        raise CardTemplateError("Template JSON must be an object at the top level.")
    return raw


def _require_number(value: Any, *, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise CardTemplateError(f"Field '{field}' must be a number.")
    number = float(value)
    if number <= 0:
        raise CardTemplateError(f"Field '{field}' must be > 0.")
    return number


def _require_non_negative_number(value: Any, *, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise CardTemplateError(f"Field '{field}' must be a number.")
    number = float(value)
    if number < 0:
        raise CardTemplateError(f"Field '{field}' must be >= 0.")
    return number


def _require_rect(value: Any, *, field: str) -> RectMM:
    if not isinstance(value, dict):
        raise CardTemplateError(f"Field '{field}' must be an object.")

    x = _require_non_negative_number(value.get("x"), field=f"{field}.x")
    y = _require_non_negative_number(value.get("y"), field=f"{field}.y")
    w = _require_number(value.get("w"), field=f"{field}.w")
    h = _require_number(value.get("h"), field=f"{field}.h")
    return RectMM(x=x, y=y, w=w, h=h)


def _require_sheet_layout(value: Any) -> SheetLayout:
    if not isinstance(value, dict):
        raise CardTemplateError("Field 'sheet_layout' must be an object.")

    page_width_mm = value.get("page_width_mm")
    page_height_mm = value.get("page_height_mm")
    if page_width_mm is None or page_height_mm is None:
        page_size = value.get("page_size_mm") or value.get("page_size")
        if not isinstance(page_size, dict):
            raise CardTemplateError(
                "sheet_layout must include either 'page_width_mm'+'page_height_mm' or 'page_size_mm'."
            )
        page_width_mm = page_size.get("width")
        page_height_mm = page_size.get("height")

    page_width_mm = _require_number(page_width_mm, field="sheet_layout.page_width_mm")
    page_height_mm = _require_number(page_height_mm, field="sheet_layout.page_height_mm")

    margin_left_mm = _require_non_negative_number(
        value.get("margin_left_mm"), field="sheet_layout.margin_left_mm"
    )
    margin_top_mm = _require_non_negative_number(
        value.get("margin_top_mm"), field="sheet_layout.margin_top_mm"
    )
    gap_x_mm = _require_non_negative_number(
        value.get("gap_x_mm"), field="sheet_layout.gap_x_mm"
    )
    gap_y_mm = _require_non_negative_number(
        value.get("gap_y_mm"), field="sheet_layout.gap_y_mm"
    )

    cards_per_row = value.get("cards_per_row")
    cards_per_col = value.get("cards_per_col")
    if not isinstance(cards_per_row, int) or not isinstance(cards_per_col, int):
        raise CardTemplateError("Fields 'cards_per_row' and 'cards_per_col' must be integers.")
    if cards_per_row <= 0 or cards_per_col <= 0:
        raise CardTemplateError("'cards_per_row' and 'cards_per_col' must be > 0.")

    return SheetLayout(
        page_width_mm=page_width_mm,
        page_height_mm=page_height_mm,
        margin_left_mm=margin_left_mm,
        margin_top_mm=margin_top_mm,
        gap_x_mm=gap_x_mm,
        gap_y_mm=gap_y_mm,
        cards_per_row=cards_per_row,
        cards_per_col=cards_per_col,
    )


def _parse_barcode_options(value: Any) -> BarcodeOptions:
    """Parse optional barcode_options from template JSON."""
    if value is None or not isinstance(value, dict):
        return BarcodeOptions()
    return BarcodeOptions(
        module_width_mm=float(value.get("module_width_mm", 0.35)),
        module_height_mm=float(value.get("module_height_mm", 10.0)),
        quiet_zone_mm=float(value.get("quiet_zone_mm", 3.5)),
        font_size_pt=float(value.get("font_size_pt", 6.0)),
        text_distance_mm=float(value.get("text_distance_mm", 1.5)),
        write_text=bool(value.get("write_text", True)),
        dpi=int(value.get("dpi", 300)),
    )


def _require_card_style(value: Any) -> CardStyle:
    if value is None:
        return CardStyle()
    if not isinstance(value, dict):
        raise CardTemplateError("Field 'card_style' must be an object if present.")

    border_radius_mm = float(value.get("border_radius_mm", 2.0))
    border_width_pt = float(value.get("border_width_pt", 0.5))
    if border_radius_mm < 0:
        raise CardTemplateError("Field 'card_style.border_radius_mm' must be >= 0.")
    if border_width_pt <= 0:
        raise CardTemplateError("Field 'card_style.border_width_pt' must be > 0.")
    return CardStyle(border_radius_mm=border_radius_mm, border_width_pt=border_width_pt)


def _optional_path(value: Any, *, base_dir: Path, field_name: str) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CardTemplateError(f"Field '{field_name}' must be a non-empty string path.")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate


def _require_non_negative_int(value: Any, *, field: str) -> int:
    if not isinstance(value, int):
        raise CardTemplateError(f"Field '{field}' must be an integer.")
    if value < 0:
        raise CardTemplateError(f"Field '{field}' must be >= 0.")
    return value


def load_card_template(path: Path) -> CardTemplate:
    """Load and validate the card template JSON (values in mm)."""
    data = _read_json(path)

    if "card_width_mm" in data and "card_height_mm" in data:
        card_width_mm = _require_number(data.get("card_width_mm"), field="card_width_mm")
        card_height_mm = _require_number(data.get("card_height_mm"), field="card_height_mm")
    else:
        card_size = data.get("card_size_mm") or data.get("card_size")
        if not isinstance(card_size, dict):
            raise CardTemplateError(
                "Template must include either 'card_width_mm'+'card_height_mm' or 'card_size_mm'."
            )
        card_width_mm = _require_number(card_size.get("width"), field="card_size_mm.width")
        card_height_mm = _require_number(card_size.get("height"), field="card_size_mm.height")

    barcode_rect_raw = data.get("barcode_rect_mm") or data.get("barcode_rect")
    barcode_rect_mm = _require_rect(barcode_rect_raw, field="barcode_rect_mm")
    label_text_rect_mm = None
    if "label_text_rect_mm" in data or "label_text_rect" in data:
        label_text_raw = data.get("label_text_rect_mm") or data.get("label_text_rect")
        label_text_rect_mm = _require_rect(label_text_raw, field="label_text_rect_mm")

    sheet_layout = _require_sheet_layout(data.get("sheet_layout"))
    card_style = _require_card_style(data.get("card_style"))
    background_pdf = _optional_path(
        data.get("background_pdf"), base_dir=path.parent, field_name="background_pdf"
    )
    background_pdf_page_index = 0
    if "background_pdf_page_index" in data:
        background_pdf_page_index = _require_non_negative_int(
            data.get("background_pdf_page_index"), field="background_pdf_page_index"
        )
    background_png = _optional_path(
        data.get("background_png"), base_dir=path.parent, field_name="background_png"
    )

    barcode_zone_mm = None
    barcode_zone_radius_mm = 1.5
    if "barcode_zone_mm" in data:
        barcode_zone_mm = _require_rect(data.get("barcode_zone_mm"), field="barcode_zone_mm")
        zone_payload = data.get("barcode_zone_mm")
        if isinstance(zone_payload, dict) and "border_radius_mm" in zone_payload:
            radius = zone_payload.get("border_radius_mm")
            if not isinstance(radius, (int, float)) or float(radius) < 0:
                raise CardTemplateError("barcode_zone_mm.border_radius_mm must be >= 0.")
            barcode_zone_radius_mm = float(radius)

    # Basic containment checks (origin at top-left inside the card)
    if barcode_rect_mm.x + barcode_rect_mm.w > card_width_mm:
        raise CardTemplateError("barcode_rect_mm must fit within the card width.")
    if barcode_rect_mm.y + barcode_rect_mm.h > card_height_mm:
        raise CardTemplateError("barcode_rect_mm must fit within the card height.")
    if label_text_rect_mm:
        if label_text_rect_mm.x + label_text_rect_mm.w > card_width_mm:
            raise CardTemplateError("label_text_rect_mm must fit within the card width.")
        if label_text_rect_mm.y + label_text_rect_mm.h > card_height_mm:
            raise CardTemplateError("label_text_rect_mm must fit within the card height.")
    if barcode_zone_mm:
        if barcode_zone_mm.x + barcode_zone_mm.w > card_width_mm:
            raise CardTemplateError("barcode_zone_mm must fit within the card width.")
        if barcode_zone_mm.y + barcode_zone_mm.h > card_height_mm:
            raise CardTemplateError("barcode_zone_mm must fit within the card height.")

    barcode_options = _parse_barcode_options(data.get("barcode_options"))

    return CardTemplate(
        card_width_mm=card_width_mm,
        card_height_mm=card_height_mm,
        barcode_rect_mm=barcode_rect_mm,
        label_text_rect_mm=label_text_rect_mm,
        sheet_layout=sheet_layout,
        card_style=card_style,
        background_pdf=background_pdf,
        background_pdf_page_index=background_pdf_page_index,
        background_png=background_png,
        barcode_zone_mm=barcode_zone_mm,
        barcode_zone_radius_mm=barcode_zone_radius_mm,
        barcode_options=barcode_options,
    )

