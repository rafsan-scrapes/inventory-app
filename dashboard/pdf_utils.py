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

PDF_ROWS_PER_PAGE = 5
COMPANY_NAME = "Inventory Management"
IMG_SIZE = 83
ROW_HEIGHT = 95
HEADER_ROW_H = 22
NOTES_MAX_CHARS = 240

C_HEADER_BG = colors.HexColor("#1e3a3a")
C_ROW_ODD = colors.white
C_ROW_EVEN = colors.HexColor("#f0f7f7")
C_BORDER = colors.HexColor("#b0cccc")
C_FOOTER_TEXT = colors.HexColor("#888888")
C_MUTED = colors.HexColor("#888888")

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

_COL_WIDTHS_FIXED = [22, 92, 85, 58, 72, 32, 32, 40, 72, 58]


def _col_widths(usable_width: float) -> list:
    notes_w = usable_width - sum(_COL_WIDTHS_FIXED)
    return _COL_WIDTHS_FIXED + [max(notes_w, 80)]


def _cell(value) -> Paragraph:
    text = str(value) if value not in (None, "") else "\u2014"
    return Paragraph(text, _CELL)


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return "\u2014"
    text = str(text)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\u2026"
    return text


def _image_cell(part):
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
    name = str(part.product_type)
    if part.product_model:
        return Paragraph(
            f"{name}<br/>"
            f"<font size='6.5' color='#888888'>({part.product_model})</font>",
            _CELL,
        )
    return Paragraph(name, _CELL)


def _location_cell(part) -> Paragraph:
    return _cell(f"{part.shelf_number}-{part.row_number}-{part.column_number}")


def _model_number_cell(part) -> Paragraph:
    mns = list(part.model_numbers.values_list("value", flat=True))
    if not mns:
        return _cell(None)
    if len(mns) == 1:
        return _cell(mns[0])
    html = "<br/>".join(mns)
    return Paragraph(html, _CELL)


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
        _model_number_cell(part),
        _location_cell(part),
        Paragraph(_truncate(part.notes, NOTES_MAX_CHARS), _CELL),
    ]


def _make_table(rows: list, col_widths: list) -> Table:
    header_row = [Paragraph(label, _HEADER_CELL) for label in _HEADER_LABELS]
    table_data = [header_row] + rows

    bg_commands = [
        ("BACKGROUND", (0, i), (-1, i), C_ROW_ODD if i % 2 == 1 else C_ROW_EVEN)
        for i in range(1, len(rows) + 1)
    ]

    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("LEADING", (0, 0), (-1, -1), 10.5),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("VALIGN", (1, 1), (1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (5, 0), (7, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            *bg_commands,
        ]
    )

    row_heights = [HEADER_ROW_H] + [ROW_HEIGHT] * len(rows)

    t = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    t.setStyle(style)
    return t


def generate_parts_pdf(parts_queryset) -> BytesIO:
    parts = list(parts_queryset)
    total_parts = len(parts)
    page_size = landscape(A4)
    page_w, page_h = page_size
    margin = 36
    usable_w = page_w - margin * 2

    chunks = [
        parts[i : i + PDF_ROWS_PER_PAGE]
        for i in range(0, total_parts, PDF_ROWS_PER_PAGE)
    ]
    total_pages = len(chunks)
    col_widths = _col_widths(usable_w)
    export_dt = datetime.now().strftime("%d %b %Y, %H:%M")

    def draw_header_footer(canvas, doc):
        canvas.saveState()

        canvas.setFillColor(C_HEADER_BG)
        canvas.rect(0, page_h - 38, page_w, 38, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(margin, page_h - 24, COMPANY_NAME)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(page_w - margin, page_h - 24, f"Exported: {export_dt}")

        canvas.setFillColor(C_FOOTER_TEXT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(margin, 14, f"Total parts exported: {total_parts}")
        canvas.drawRightString(page_w - margin, 14, f"Page {doc.page} of {total_pages}")

        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=46,
        bottomMargin=30,
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
