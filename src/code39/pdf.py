"""PDF rendering for Code 39 labels."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Callable

from barcode import Code39
from barcode.writer import ImageWriter
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from .formatting import PREFIX

ProgressCallback = Callable[[str], None] | None
BRAND_TEXT = "Atlantico Gastrobar"
PNG_BACKGROUND = "white"
PNG_FOREGROUND = "black"


def _chunks(values: list[str], size: int) -> list[list[str]]:
    """Split references into page-sized chunks."""
    return [values[index : index + size] for index in range(0, len(values), size)]


def _barcode_value(reference: str) -> str:
    """Extract the numeric part for barcode encoding.

    Business rule: the *encoded code* (bars) must be digits-only.
    """
    normalized = reference.strip().upper()
    if normalized.startswith(PREFIX):
        return normalized[len(PREFIX) :]
    return normalized


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a common truetype font with a bitmap fallback."""
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(font_name, size=size)
    except OSError:
        return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    center_x: int,
    baseline_y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw centered text using the provided baseline."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    height = bottom - top
    draw.text((center_x - (width / 2), baseline_y - height), text, fill=PNG_FOREGROUND, font=font)


def _code39_pattern(value: str) -> str:
    """Return the decomposed bar/space pattern for a Code 39 reference."""
    from reportlab.graphics.barcode import code39

    barcode = code39.Standard39(value, checksum=0, stop=1)
    barcode.validate()
    barcode.encode()
    return barcode.decompose()


def _render_barcode_image(reference: str, width_mm: float, height_mm: float) -> BytesIO:
    """Render Code 39 barcode to PNG buffer."""
    value = _barcode_value(reference)
    opts = {
        "module_width": 0.33,
        "module_height": height_mm,
        "quiet_zone": 2.0,
        "font_size": 6,
        "write_text": False,
        "dpi": 300,
    }
    buf = BytesIO()
    Code39(value, writer=ImageWriter(), add_checksum=False).write(buf, opts)
    buf.seek(0)
    return buf


def _draw_code39_bars(
    draw: ImageDraw.ImageDraw,
    *,
    barcode_value: str,
    x: int,
    y: int,
    bar_height: int,
    narrow_width: int,
    wide_ratio: int,
) -> int:
    """Draw the barcode bars and return the total rendered width."""
    pattern = _code39_pattern(barcode_value)
    cursor_x = x
    widths = {
        "b": narrow_width,
        "s": narrow_width,
        "i": narrow_width,
        "B": narrow_width * wide_ratio,
        "S": narrow_width * wide_ratio,
    }

    for token in pattern:
        width = widths[token]
        if token in {"b", "B"}:
            draw.rectangle(
                [(cursor_x, y), (cursor_x + width - 1, y + bar_height - 1)],
                fill=PNG_FOREGROUND,
            )
        cursor_x += width

    return cursor_x - x


def render_reference_png(reference: str, output_path: Path) -> Path:
    """Render a single label as a PNG image."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width = 1200
    height = 700
    outer_padding = 48
    header_gap = 26
    footer_gap = 24
    box_x = outer_padding
    box_y = 120
    box_width = width - (2 * outer_padding)
    box_height = 430
    box_bottom = box_y + box_height

    image = Image.new("RGB", (width, height), PNG_BACKGROUND)
    draw = ImageDraw.Draw(image)
    brand_font = _load_font(30)
    reference_font = _load_font(38, bold=True)

    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_width, box_bottom)],
        radius=26,
        outline=PNG_FOREGROUND,
        width=3,
    )

    _draw_centered_text(
        draw,
        BRAND_TEXT,
        center_x=width // 2,
        baseline_y=box_y - header_gap,
        font=brand_font,
    )

    narrow_width = 6
    wide_ratio = 3
    bar_height = 220
    barcode_value = _barcode_value(reference)
    barcode_width = sum(
        narrow_width * wide_ratio if token in {"B", "S"} else narrow_width
        for token in _code39_pattern(barcode_value)
    )
    barcode_x = box_x + max((box_width - barcode_width) // 2, 30)
    barcode_y = box_y + ((box_height - bar_height) // 2)
    _draw_code39_bars(
        draw,
        barcode_value=barcode_value,
        x=barcode_x,
        y=barcode_y,
        bar_height=bar_height,
        narrow_width=narrow_width,
        wide_ratio=wide_ratio,
    )

    _draw_centered_text(
        draw,
        reference,
        center_x=width // 2,
        baseline_y=box_bottom + footer_gap + 34,
        font=reference_font,
    )

    image.save(output_path, format="PNG")
    return output_path


def derive_png_output_dir(pdf_output_path: Path) -> Path:
    """Return the default PNG directory derived from the PDF path."""
    return pdf_output_path.with_name(f"{pdf_output_path.stem}-png")


def render_batch_pngs(
    references: list[str],
    output_dir: Path,
    *,
    progress_callback: ProgressCallback = None,
) -> Path:
    """Render one PNG per reference inside the target directory."""
    if not references:
        raise ValueError("At least one reference is required to render PNG files.")

    output_dir.mkdir(parents=True, exist_ok=True)
    for reference in references:
        render_reference_png(reference, output_dir / f"{reference}.png")
        if progress_callback:
            progress_callback(reference)
    return output_dir


def render_batch_pdf(
    references: list[str],
    output_path: Path,
    *,
    progress_callback: ProgressCallback = None,
) -> Path:
    """Render a print-ready A4 PDF with barcode labels."""
    if not references:
        raise ValueError("At least one reference is required to render a PDF.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(unit="mm")
    margin_x = 12
    margin_y = 14
    columns = 2
    rows = 5
    gap_x = 8
    gap_y = 6
    page_w = 210
    page_h = 297
    cell_width = (page_w - 2 * margin_x - gap_x) / columns
    cell_height = (page_h - 2 * margin_y - (rows - 1) * gap_y) / rows
    labels_per_page = columns * rows
    pages = _chunks(references, labels_per_page)
    barcode_h_mm = 14

    for page_references in pages:
        pdf.add_page(format="a4")
        for position, reference in enumerate(page_references):
            column = position % columns
            row = position // columns
            x = margin_x + column * (cell_width + gap_x)
            y = margin_y + row * (cell_height + gap_y)
            box_h = cell_height - 14
            box_y = y + 7

            pdf.rect(x, box_y, cell_width, box_h, round_corners=True, style="D")
            pdf.set_font("Helvetica", size=8)
            pdf.set_xy(x, y)
            pdf.cell(cell_width, 6, BRAND_TEXT, align="C")

            barcode_buf = _render_barcode_image(reference, cell_width - 12, barcode_h_mm)
            barcode_x = x + (cell_width - (cell_width - 12)) / 2
            barcode_y_mm = box_y + (box_h - barcode_h_mm) / 2
            pdf.image(barcode_buf, x=barcode_x, y=barcode_y_mm, w=cell_width - 12, h=barcode_h_mm)

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_xy(x, box_y + box_h - 4)
            pdf.cell(cell_width, 5, reference, align="C")

            if progress_callback:
                progress_callback(reference)

    pdf.output(str(output_path))
    return output_path
