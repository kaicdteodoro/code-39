"""Card rendering (template-based) for Code 39 labels."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from barcode import Code39
from barcode.writer import ImageWriter
from fpdf import FPDF
from pypdf import PdfReader, PdfWriter
from reportlab.graphics.barcode import code39

from .card_template import BarcodeOptions, CardTemplate, RectMM
from .formatting import PREFIX

ProgressCallback = Callable[[str], None] | None

PNG_BACKGROUND = "white"
PNG_FOREGROUND = "black"


class CardRenderError(RuntimeError):
    """Raised when card rendering fails."""


def _barcode_value(reference: str) -> str:
    """Digits-only code value used by the barcode bars."""
    normalized = reference.strip().upper()
    if normalized.startswith(PREFIX):
        return normalized[len(PREFIX) :]
    return normalized


def _code39_pattern(value: str) -> str:
    """Return Code 39 decompose tokens for bars/spaces."""
    barcode = code39.Standard39(value, checksum=0, stop=1)
    barcode.validate()
    barcode.encode()
    return barcode.decompose()


def _load_font(size_px: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(font_name, size=size_px)
    except OSError:
        return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    center_x: int,
    center_y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    height = bottom - top
    draw.text(
        (center_x - width // 2, center_y - height // 2),
        text,
        fill=PNG_FOREGROUND,
        font=font,
    )


def _draw_code39_bars_pil(
    draw: ImageDraw.ImageDraw,
    *,
    barcode_value: str,
    rect_px: tuple[int, int, int, int],
) -> int:
    """Draw barcode bars inside a rectangle and return rendered width in px."""
    x_px, y_px, w_px, h_px = rect_px

    # We draw bars only for tokens 'b' and 'B' (wide bars).
    pattern = _code39_pattern(barcode_value)

    # Derive ratio from an instance so our "wide" proportions match.
    probe = code39.Standard39(barcode_value, checksum=0, stop=1)
    wide_ratio = float(getattr(probe, "ratio", 3.0)) or 3.0

    # Token width units: narrow for b/s/i, wide for B/S.
    total_units = 0.0
    for token in pattern:
        if token in {"B", "S"}:
            total_units += wide_ratio
        else:
            total_units += 1.0
    if total_units <= 0:
        return 0

    narrow_px = w_px / total_units
    narrow_px = max(narrow_px, 0.5)
    wide_px = narrow_px * wide_ratio

    cursor_x = x_px
    for token in pattern:
        width = wide_px if token in {"B", "S"} else narrow_px
        width_i = max(int(round(width)), 1)
        if token in {"b", "B"}:
            draw.rectangle(
                [(cursor_x, y_px), (cursor_x + width_i - 1, y_px + h_px - 1)],
                fill=PNG_FOREGROUND,
            )
        cursor_x += width_i

    return cursor_x - x_px


def _build_barcode_image(
    barcode_value: str,
    *,
    width_px: int,
    height_px: int,
    barcode_options: BarcodeOptions | None = None,
) -> Image.Image:
    """Create barcode image with bars and optional text below, with configurable gap."""
    opts = barcode_options or BarcodeOptions()
    dpi = opts.dpi
    px_per_mm = dpi / 25.4
    gap_px = int(round(opts.text_distance_mm * px_per_mm))
    font_size_px = max(6, int(round(opts.font_size_pt * dpi / 72)))

    # Render bars only (no text) for precise layout control
    bar_options = {
        "module_width": opts.module_width_mm,
        "module_height": opts.module_height_mm,
        "quiet_zone": opts.quiet_zone_mm,
        "font_size": opts.font_size_pt,
        "background": "white",
        "foreground": "black",
        "write_text": False,
        "dpi": dpi,
    }
    try:
        buffer = BytesIO()
        Code39(barcode_value, writer=ImageWriter(), add_checksum=False).write(buffer, bar_options)
        buffer.seek(0)
        bars_img = Image.open(buffer).convert("RGB")
    except Exception:
        bars_img = Image.new("RGB", (max(width_px, 1), max(height_px // 2, 1)), PNG_BACKGROUND)
        draw = ImageDraw.Draw(bars_img)
        _draw_code39_bars_pil(
            draw,
            barcode_value=barcode_value,
            rect_px=(0, 0, bars_img.width, bars_img.height),
        )

    if not opts.write_text:
        return bars_img.resize((max(width_px, 1), max(height_px, 1)), Image.LANCZOS)

    # Composite: bars + gap + text with controlled spacing
    text_h_px = int(font_size_px * 1.4)
    bars_h = max(1, height_px - gap_px - text_h_px)
    bars_scaled = bars_img.resize((max(width_px, 1), bars_h), Image.LANCZOS)

    out_h = bars_h + gap_px + text_h_px
    out = Image.new("RGB", (width_px, out_h), PNG_BACKGROUND)
    out.paste(bars_scaled, (0, 0))

    draw = ImageDraw.Draw(out)
    font = _load_font(font_size_px)
    text = barcode_value
    _draw_centered_text(
        draw,
        text,
        center_x=width_px // 2,
        center_y=bars_h + gap_px + text_h_px // 2,
        font=font,
    )

    if out_h != height_px:
        out = out.resize((width_px, max(height_px, 1)), Image.LANCZOS)
    return out


def _build_composed_card_image(
    reference: str,
    template: CardTemplate,
    *,
    dpi: int = 300,
) -> Image.Image:
    """Compose full card image: white base + barcode + top art PNG with hole."""
    if template.background_png is None:
        raise CardRenderError("background_png is required for PNG layered composition.")
    if not template.background_png.exists():
        raise CardRenderError(f"background_png not found: {template.background_png}")

    art = Image.open(template.background_png).convert("RGBA")
    card_w_px, card_h_px = art.size

    px_per_mm = dpi / 25.4
    r = template.barcode_rect_mm
    rect_x = int(round(r.x * px_per_mm))
    rect_y = int(round(r.y * px_per_mm))
    rect_w = int(round(r.w * px_per_mm))
    rect_h = int(round(r.h * px_per_mm))

    base = Image.new("RGBA", (card_w_px, card_h_px), (255, 255, 255, 255))

    if template.barcode_zone_mm is not None:
        zone = template.barcode_zone_mm
        zx = int(round(zone.x * px_per_mm))
        zy = int(round(zone.y * px_per_mm))
        zw = int(round(zone.w * px_per_mm))
        zh = int(round(zone.h * px_per_mm))
        zr = int(round(template.barcode_zone_radius_mm * px_per_mm))
        mask = Image.new("L", (zw, zh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, zw - 1, zh - 1], radius=max(zr, 0), fill=255)
        white_box = Image.new("RGBA", (zw, zh), (255, 255, 255, 255))
        white_box.putalpha(mask)
        base.paste(white_box, (zx, zy), white_box)

    barcode_value = _barcode_value(reference)
    barcode_img = _build_barcode_image(
        barcode_value,
        width_px=rect_w,
        height_px=rect_h,
        barcode_options=template.barcode_options,
    ).convert("RGBA")
    base.paste(barcode_img, (rect_x, rect_y), barcode_img)
    base.paste(art, (0, 0), art)
    return base


def render_batch_cards_pngs(
    references: list[str],
    output_dir: Path,
    template: CardTemplate,
    *,
    progress_callback: ProgressCallback = None,
    dpi: int = 300,
) -> Path:
    """Render one barcode-only PNG per reference using the card template."""
    if not references:
        raise ValueError("At least one reference is required to render PNG cards.")

    output_dir.mkdir(parents=True, exist_ok=True)

    for reference in references:
        if template.background_png is not None:
            image = _build_composed_card_image(reference, template, dpi=dpi).convert("RGB")
        else:
            px_per_mm = dpi / 25.4
            r = template.barcode_rect_mm
            barcode_w_px = int(round(r.w * px_per_mm))
            barcode_h_px = int(round(r.h * px_per_mm))
            barcode_value = _barcode_value(reference)
            image = _build_barcode_image(
                barcode_value,
                width_px=barcode_w_px,
                height_px=barcode_h_px,
                barcode_options=template.barcode_options,
            )

        output_path = output_dir / f"{reference}.png"
        image.save(output_path, format="PNG")

        if progress_callback:
            progress_callback(reference)

    return output_dir


def _mm_to_pt(mm_value: float) -> float:
    return mm_value * 72.0 / 25.4


def render_batch_cards_pdf(
    references: list[str],
    output_pdf_path: Path,
    template: CardTemplate,
    *,
    progress_callback: ProgressCallback = None,
) -> Path:
    """Render a print-ready PDF with cards placed using the template."""
    if not references:
        raise ValueError("At least one reference is required to render cards PDF.")

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    sheet = template.sheet_layout
    if template.background_pdf is not None and (
        sheet.cards_per_row != 1 or sheet.cards_per_col != 1
    ):
        raise CardRenderError(
            "background_pdf currently supports one card per page (cards_per_row=1 and cards_per_col=1)."
        )

    page_w_pts = _mm_to_pt(sheet.page_width_mm)
    page_h_pts = _mm_to_pt(sheet.page_height_mm)
    background_bytes: bytes | None = None
    if template.background_pdf is not None:
        background_path = template.background_pdf
        if not background_path.exists():
            raise CardRenderError(f"background_pdf not found: {background_path}")
        background_bytes = background_path.read_bytes()
        base_page_probe = PdfReader(BytesIO(background_bytes)).pages[0]
        page_w_pts = float(base_page_probe.mediabox.width)
        page_h_pts = float(base_page_probe.mediabox.height)
    elif template.background_png is not None:
        if not template.background_png.exists():
            raise CardRenderError(f"background_png not found: {template.background_png}")
        art = Image.open(template.background_png)
        dpi = 300
        page_w_pts = (art.size[0] / dpi) * 72.0
        page_h_pts = (art.size[1] / dpi) * 72.0

    pdf = FPDF(unit="pt")
    pdf.set_auto_page_break(False)
    per_page = sheet.cards_per_row * sheet.cards_per_col
    card_w_pts = _mm_to_pt(template.card_width_mm)
    card_h_pts = _mm_to_pt(template.card_height_mm)
    barcode_rect_pts = template.barcode_rect_mm

    for idx, reference in enumerate(references):
        position_in_page = idx % per_page
        if position_in_page == 0:
            pdf.add_page(format=(page_w_pts, page_h_pts))

        row = position_in_page // sheet.cards_per_row
        col = position_in_page % sheet.cards_per_row
        card_origin_x_pts = _mm_to_pt(sheet.margin_left_mm + col * (template.card_width_mm + sheet.gap_x_mm))
        card_origin_y_from_top_pts = _mm_to_pt(sheet.margin_top_mm + row * (template.card_height_mm + sheet.gap_y_mm))

        # Card outline placeholder is useful only without background template.
        if template.background_pdf is None:
            style = "D"
            radius = _mm_to_pt(template.card_style.border_radius_mm) if template.card_style.border_radius_mm > 0 else 0
            if radius > 0:
                pdf.rect(card_origin_x_pts, card_origin_y_from_top_pts, card_w_pts, card_h_pts, round_corners=True, style=style)
            else:
                pdf.rect(card_origin_x_pts, card_origin_y_from_top_pts, card_w_pts, card_h_pts, style=style)

        # Optional barcode zone overlay (white rounded box).
        if template.barcode_zone_mm is not None:
            zone = template.barcode_zone_mm
            zone_x_pts = card_origin_x_pts + _mm_to_pt(zone.x)
            zone_y_pts = card_origin_y_from_top_pts + _mm_to_pt(zone.y)
            zone_w_pts = _mm_to_pt(zone.w)
            zone_h_pts = _mm_to_pt(zone.h)
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(zone_x_pts, zone_y_pts, zone_w_pts, zone_h_pts, round_corners=True, style="F")

        if template.background_png is not None:
            composed = _build_composed_card_image(reference, template, dpi=300).convert("RGB")
            composed_buffer = BytesIO()
            composed.save(composed_buffer, format="PNG")
            composed_buffer.seek(0)
            pdf.image(composed_buffer, x=0, y=0, w=page_w_pts, h=page_h_pts)
        else:
            barcode_value = _barcode_value(reference)
            rect_x_pts = card_origin_x_pts + _mm_to_pt(barcode_rect_pts.x)
            rect_y_pts = card_origin_y_from_top_pts + _mm_to_pt(barcode_rect_pts.y)
            rect_w_pts = _mm_to_pt(barcode_rect_pts.w)
            rect_h_pts = _mm_to_pt(barcode_rect_pts.h)
            dpi = 300
            rect_w_px = int(round((rect_w_pts / 72.0) * dpi))
            rect_h_px = int(round((rect_h_pts / 72.0) * dpi))
            barcode_image = _build_barcode_image(
                barcode_value,
                width_px=rect_w_px,
                height_px=rect_h_px,
                barcode_options=template.barcode_options,
            )
            png_buffer = BytesIO()
            barcode_image.save(png_buffer, format="PNG")
            png_buffer.seek(0)
            pdf.image(png_buffer, x=rect_x_pts, y=rect_y_pts, w=rect_w_pts, h=rect_h_pts)

        if template.label_text_rect_mm is not None:
            tr = template.label_text_rect_mm
            text_center_x = card_origin_x_pts + _mm_to_pt(tr.x + tr.w / 2)
            text_y_pts = card_origin_y_from_top_pts + _mm_to_pt(tr.y)
            cell_w = _mm_to_pt(tr.w)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_xy(text_center_x - cell_w / 2, text_y_pts)
            pdf.cell(cell_w, 6, reference, align="C")

        if progress_callback:
            progress_callback(reference)

    overlay_stream = BytesIO(pdf.output())

    # When using composed image (background_png), output overlay directly to avoid
    # any footer (e.g. "Page 1/1") from the background PDF.
    if template.background_png is not None:
        output_pdf_path.write_bytes(overlay_stream.getvalue())
        return output_pdf_path

    if template.background_pdf is None:
        output_pdf_path.write_bytes(overlay_stream.getvalue())
        return output_pdf_path

    overlay_reader = PdfReader(overlay_stream)
    assert background_bytes is not None
    writer = PdfWriter()

    for overlay_page in overlay_reader.pages:
        base_page = PdfReader(BytesIO(background_bytes)).pages[0]
        base_page.merge_page(overlay_page)
        writer.add_page(base_page)

    with output_pdf_path.open("wb") as stream:
        writer.write(stream)
    return output_pdf_path


def interleave_front_verso(
    front_pdf_path: Path,
    verso_pdf_path: Path,
    output_path: Path,
    *,
    front_pages_per_verso: int = 1,
) -> Path:
    """Interleave front and verso PDFs. Pattern: [f0..f_{n-1}, v0, f_n..f_{2n-1}, v1, ...].
    With front_pages_per_verso=2: [f0,f1,v0,f2,f3,v1,...]."""
    front = PdfReader(str(front_pdf_path))
    verso = PdfReader(str(verso_pdf_path))
    writer = PdfWriter()
    n_verso = len(verso.pages)
    front_idx = 0
    for v in range(n_verso):
        for _ in range(front_pages_per_verso):
            if front_idx < len(front.pages):
                writer.add_page(front.pages[front_idx])
                front_idx += 1
        writer.add_page(verso.pages[v])
    while front_idx < len(front.pages):
        writer.add_page(front.pages[front_idx])
        front_idx += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)
    return output_path

