import os
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    PageBreak,
    Image as RLImage,
)

# ── Configuration ──────────────────────────────────────────────────────────
PDF_ROWS_PER_PAGE = 5
COMPANY_NAME = "Inventory Management"
IMG_SIZE = 83  # image display size in points (square), fits inside ROW_HEIGHT
ROW_HEIGHT = 95  # fixed height for every data row in points
HEADER_ROW_H = 22  # height of the column-header row
NOTES_MAX_CHARS = 240  # truncate notes beyond this; roughly matches image height

# ── Colour palette ─────────────────────────────────────────────────────────
C_HEADER_BG = colors.HexColor("#1e3a3a")
C_ROW_ODD = colors.white
C_ROW_EVEN = colors.HexColor("#f0f7f7")
C_BORDER = colors.HexColor("#b0cccc")
C_FOOTER_TEXT = colors.HexColor("#888888")
C_MUTED = colors.HexColor("#888888")

# ── Paragraph styles ───────────────────────────────────────────────────────
_CELL = ParagraphStyle(
    "cell",
    fontName="Helvetica",
    fontSize=7.5,
    leading=10.5,
)
_HEADER_CELL = ParagraphStyle(
    "header_cell",
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=10.5,
    textColor=colors.white,
)

# Column headers (matches _COL_WIDTHS_FIXED order + Notes at end)
_HEADER_LABELS = [
    "#",
    "Image",
    "Product Type",
    "Brand",
    "Part Type",
    "New",
    "Used",
    "Size (kg)",
    "Model No.",
    "Location",
    "Notes",
]

# Fixed column widths in points — Notes gets whatever is left
_COL_WIDTHS_FIXED = [22, 92, 85, 58, 72, 32, 32, 40, 72, 58]


def _col_widths(usable_width: float) -> list:
    notes_w = usable_width - sum(_COL_WIDTHS_FIXED)
    return _COL_WIDTHS_FIXED + [max(notes_w, 80)]


# ── Cell helpers ───────────────────────────────────────────────────────────


def _cell(value) -> Paragraph:
    text = str(value) if value not in (None, "") else "—"
    return Paragraph(text, _CELL)


def _truncate(text: str, max_chars: int) -> str:
    """Return text truncated to max_chars with a trailing ellipsis if needed."""
    if not text:
        return "—"
    text = str(text)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "…"
    return text


def _image_cell(part):
    """
    Return a ReportLab Image flowable for the part's image, or a "—" Paragraph
    if no image is present or the file is missing.
    """
    if not part.image:
        return _cell(None)
    try:
        path = part.image.path
        if not os.path.exists(path):
            return _cell(None)
        img = RLImage(path, width=IMG_SIZE, height=IMG_SIZE)
        img.hAlign = "CENTER"
        return img
    except Exception:
        return _cell(None)


def _product_type_cell(part) -> Paragraph:
    """
    Product type name with the product model in muted smaller text below,
    matching the index.html display:  ProductType\n(product_model)
    """
    name = str(part.product_type)
    if part.product_model:
        return Paragraph(
            f"{name}<br/>"
            f"<font size='6.5' color='#888888'>({part.product_model})</font>",
            _CELL,
        )
    return Paragraph(name, _CELL)


def _location_cell(part) -> Paragraph:
    """Shelf-Row-Column in a single cell."""
    return _cell(f"{part.shelf_number}-{part.row_number}-{part.column_number}")


# ── Row builder ────────────────────────────────────────────────────────────


def _build_data_row(part) -> list:
    return [
        _cell(part.id),
        _image_cell(part),
        _product_type_cell(part),
        _cell(part.brand),
        _cell(part.part_type.name),
        _cell(part.total_new),
        _cell(part.total_used),
        _cell(part.size_kg),
        _cell(part.model_number),
        _location_cell(part),
        Paragraph(_truncate(part.notes, NOTES_MAX_CHARS), _CELL),
    ]


# ── Table builder ──────────────────────────────────────────────────────────


def _make_table(rows: list, col_widths: list) -> Table:
    header_row = [Paragraph(label, _HEADER_CELL) for label in _HEADER_LABELS]
    table_data = [header_row] + rows

    # Alternating row backgrounds
    bg_commands = [
        ("BACKGROUND", (0, i), (-1, i), C_ROW_ODD if i % 2 == 1 else C_ROW_EVEN)
        for i in range(1, len(rows) + 1)
    ]

    style = TableStyle(
        [
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            # All cells
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("LEADING", (0, 0), (-1, -1), 10.5),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),  # header: vertically centred
            ("VALIGN", (0, 1), (-1, -1), "TOP"),  # data rows: top-aligned
            ("VALIGN", (1, 1), (1, -1), "MIDDLE"),  # image col: centred
            ("ALIGN", (1, 0), (1, -1), "CENTER"),  # image col: horizontally centred
            ("ALIGN", (5, 0), (7, -1), "CENTER"),  # New / Used / Size: centred
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            *bg_commands,
        ]
    )

    # Explicit row heights: short header + fixed-height data rows
    row_heights = [HEADER_ROW_H] + [ROW_HEIGHT] * len(rows)

    t = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    t.setStyle(style)
    return t


# ── Public entry point ─────────────────────────────────────────────────────


def generate_parts_pdf(parts_queryset) -> BytesIO:
    """
    Generate a landscape-A4 PDF for the given Part queryset.

    Per-page layout
    ---------------
    Header band  — company name (left) + export datetime (right)
    Table        — up to PDF_ROWS_PER_PAGE data rows, each with a square part image
    Footer band  — total parts count (left) + "Page X of Y" (right)
    """
    parts = list(parts_queryset)
    total_parts = len(parts)
    page_size = landscape(A4)  # 841.9 × 595.3 pt
    page_w, page_h = page_size
    margin = 36
    usable_w = page_w - margin * 2  # ≈ 769.9 pt

    chunks = [
        parts[i : i + PDF_ROWS_PER_PAGE]
        for i in range(0, total_parts, PDF_ROWS_PER_PAGE)
    ]
    total_pages = len(chunks)
    col_widths = _col_widths(usable_w)
    export_dt = datetime.now().strftime("%d %b %Y, %H:%M")

    # ── Header / footer drawn directly on every page ───────────────────────
    def draw_header_footer(canvas, doc):
        canvas.saveState()

        # Header band
        canvas.setFillColor(C_HEADER_BG)
        canvas.rect(0, page_h - 38, page_w, 38, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(margin, page_h - 24, COMPANY_NAME)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(page_w - margin, page_h - 24, f"Exported: {export_dt}")

        # Footer
        canvas.setFillColor(C_FOOTER_TEXT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(margin, 14, f"Total parts exported: {total_parts}")
        canvas.drawRightString(page_w - margin, 14, f"Page {doc.page} of {total_pages}")

        canvas.restoreState()

    # ── Build story ────────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=46,  # clears the 38 pt header band
        bottomMargin=30,  # clears the footer
        title="Parts Export",
    )

    story = []
    for idx, chunk in enumerate(chunks):
        story.append(_make_table([_build_data_row(p) for p in chunk], col_widths))
        if idx < total_pages - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    return buffer
