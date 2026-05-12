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
)

# ── Configuration ──────────────────────────────────────────────────────────
PDF_ROWS_PER_PAGE = 5
COMPANY_NAME = "Inventory Management"

# ── Colour palette (light theme — PDFs are printed) ───────────────────────
C_HEADER_BG = colors.HexColor("#1e3a3a")  # dark teal header bar
C_ROW_ODD = colors.white
C_ROW_EVEN = colors.HexColor("#f0f7f7")  # very light teal tint
C_BORDER = colors.HexColor("#b0cccc")
C_FOOTER_TEXT = colors.HexColor("#888888")

# ── Paragraph styles ───────────────────────────────────────────────────────
_CELL = ParagraphStyle(
    "cell",
    fontName="Helvetica",
    fontSize=8,
    leading=11,
)
_HEADER_CELL = ParagraphStyle(
    "header_cell",
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=11,
    textColor=colors.white,
)

# Column header labels
_HEADER_ROW = [
    Paragraph(label, _HEADER_CELL)
    for label in [
        "#",
        "Product Type",
        "Brand",
        "Part Type",
        "New",
        "Used",
        "Shelf",
        "Col",
        "Row",
        "Model No.",
        "Notes",
    ]
]

# Column widths (points) — last column (Notes) is calculated from remainder
_FIXED_WIDTHS = [28, 88, 68, 88, 38, 38, 38, 34, 34, 90]  # 10 columns


def _col_widths(usable_width: float) -> list[float]:
    notes_col = usable_width - sum(_FIXED_WIDTHS)
    return _FIXED_WIDTHS + [max(notes_col, 60)]


def _build_data_row(part) -> list:
    """Convert a Part instance into a list of Paragraph cells."""

    def cell(value):
        return Paragraph(str(value) if value not in (None, "") else "—", _CELL)

    return [
        cell(part.id),
        cell(part.product_type),
        cell(part.brand),
        cell(part.part_type.name),
        cell(part.total_new),
        cell(part.total_used),
        cell(part.shelf_number),
        cell(part.column_number),
        cell(part.row_number),
        cell(part.model_number),
        cell(part.notes),
    ]


def _make_table(rows: list, col_widths: list[float]) -> Table:
    """Build and style a ReportLab Table from a list of data rows."""
    table_data = [_HEADER_ROW] + rows

    # Build alternating row background commands
    bg_commands = []
    for i, _ in enumerate(rows, start=1):  # data rows start at index 1
        bg = C_ROW_ODD if i % 2 == 1 else C_ROW_EVEN
        bg_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

    style = TableStyle(
        [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            # All cells
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 11),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            *bg_commands,
        ]
    )

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(style)
    return t


def generate_parts_pdf(parts_queryset) -> BytesIO:
    """
    Generate a landscape-A4 PDF for the given Part queryset.

    Layout
    ------
    - Sticky header bar: company name (left) + export datetime (right)
    - Data table with alternating row colours, max PDF_ROWS_PER_PAGE rows/page
    - Footer: total parts count (left) + "Page X of Y" (right)

    Returns a BytesIO buffer positioned at 0, ready to stream.
    """
    parts = list(parts_queryset)
    total_parts = len(parts)
    page_size = landscape(A4)  # 841.9 × 595.3 pt
    page_w, page_h = page_size
    margin = 40
    usable_w = page_w - margin * 2

    # Split parts into pages
    chunks = [
        parts[i : i + PDF_ROWS_PER_PAGE]
        for i in range(0, total_parts, PDF_ROWS_PER_PAGE)
    ]
    total_pages = len(chunks)
    col_widths = _col_widths(usable_w)
    export_dt = datetime.now().strftime("%d %b %Y, %H:%M")

    # ── Page template callbacks ────────────────────────────────────────────
    def draw_header_footer(canvas, doc):
        canvas.saveState()

        # Header band
        canvas.setFillColor(C_HEADER_BG)
        canvas.rect(0, page_h - 40, page_w, 40, fill=1, stroke=0)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(margin, page_h - 25, COMPANY_NAME)

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_w - margin, page_h - 25, f"Exported: {export_dt}")

        # Footer
        canvas.setFillColor(C_FOOTER_TEXT)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margin, 18, f"Total parts exported: {total_parts}")
        canvas.drawRightString(page_w - margin, 18, f"Page {doc.page} of {total_pages}")

        canvas.restoreState()

    # ── Build story ────────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=50,  # space for header band
        bottomMargin=36,  # space for footer
        title="Parts Export",
    )

    story = []
    for idx, chunk in enumerate(chunks):
        rows = [_build_data_row(p) for p in chunk]
        story.append(_make_table(rows, col_widths))
        if idx < total_pages - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    return buffer
