"""PDF rendering for Code 39 labels."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont
from reportlab.graphics.barcode import code39
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ProgressCallback = Callable[[str], None] | None
BRAND_TEXT = "Atlantico Gastrobar"
PNG_BACKGROUND = "white"
PNG_FOREGROUND = "black"


def _chunks(values: list[str], size: int) -> list[list[str]]:
    """Split references into page-sized chunks."""
    return [values[index : index + size] for index in range(0, len(values), size)]


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


def _code39_pattern(reference: str) -> str:
    """Return the decomposed bar/space pattern for a Code 39 reference."""
    barcode = code39.Standard39(reference, checksum=0, stop=1)
    barcode.validate()
    barcode.encode()
    return barcode.decompose()


def _draw_code39_bars(
    draw: ImageDraw.ImageDraw,
    *,
    reference: str,
    x: int,
    y: int,
    bar_height: int,
    narrow_width: int,
    wide_ratio: int,
) -> int:
    """Draw the barcode bars and return the total rendered width."""
    pattern = _code39_pattern(reference)
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
    barcode_width = sum(
        narrow_width * wide_ratio if token in {"B", "S"} else narrow_width
        for token in _code39_pattern(reference)
    )
    barcode_x = box_x + max((box_width - barcode_width) // 2, 30)
    barcode_y = box_y + ((box_height - bar_height) // 2)
    _draw_code39_bars(
        draw,
        reference=reference,
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

    pdf = canvas.Canvas(str(output_path), pagesize=A4, pageCompression=0, invariant=1)
    pdf.setTitle("Code 39 batch")

    page_width, page_height = A4
    margin_x = 12 * mm
    margin_y = 14 * mm
    columns = 2
    rows = 5
    gap_x = 8 * mm
    gap_y = 6 * mm
    cell_width = (page_width - (2 * margin_x) - gap_x) / columns
    cell_height = (page_height - (2 * margin_y) - ((rows - 1) * gap_y)) / rows
    labels_per_page = columns * rows
    pages = _chunks(references, labels_per_page)
    total_pages = len(pages)

    for current_page, page_references in enumerate(pages, start=1):
        for position, reference in enumerate(page_references):
            column = position % columns
            row = position // columns

            x = margin_x + column * (cell_width + gap_x)
            y = page_height - margin_y - ((row + 1) * cell_height) - (row * gap_y)
            label_header_height = 7 * mm
            label_footer_height = 7 * mm
            box_height = cell_height - label_header_height - label_footer_height
            box_y = y
            brand_y = y + cell_height - 4.5 * mm
            barcode_y = box_y + ((box_height - (14 * mm)) / 2)
            footer_y = y + 4 * mm

            pdf.setLineWidth(0.5)
            pdf.roundRect(x, box_y, cell_width, box_height, 4 * mm)

            pdf.setFont("Helvetica", 8)
            pdf.drawCentredString(x + (cell_width / 2), brand_y, BRAND_TEXT)

            barcode = code39.Standard39(
                reference,
                barWidth=0.33 * mm,
                barHeight=14 * mm,
                checksum=0,
                stop=1,
            )
            barcode_width = barcode.width
            barcode_x = x + max((cell_width - barcode_width) / 2, 6 * mm)
            barcode.drawOn(pdf, barcode_x, barcode_y)

            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawCentredString(x + (cell_width / 2), footer_y, reference)

            if progress_callback:
                progress_callback(reference)

        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(
            page_width - margin_x,
            8 * mm,
            f"Page {current_page}/{total_pages}",
        )
        if current_page < total_pages:
            pdf.showPage()

    pdf.save()
    return output_path
