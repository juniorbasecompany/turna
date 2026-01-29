"""
Layout reutilizável para relatórios PDF: cabeçalho "Turna", título do relatório,
seção "Filtros utilizados" e conteúdo (tabela). Todas as páginas de relatório
usam este layout para manter padrão visual único.
"""

from __future__ import annotations

import io


def _ensure_reportlab():
    try:
        from reportlab.lib import colors  # noqa: F401
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError as e:
        raise RuntimeError(
            "Dependência ausente para gerar PDF. Instale com: pip install reportlab"
        ) from e


REPORT_HEADER_TITLE = "Turna"


def build_report_pdf(
    report_title: str,
    filters_text: str,
    headers: list[str] | None = None,
    rows: list[list[str]] | None = None,
) -> bytes:
    """
    Gera PDF com layout padrão: cabeçalho Turna, título do relatório,
    "Filtros utilizados: ..." e opcionalmente uma tabela (headers + rows).

    Se headers/rows forem None ou vazios, apenas o cabeçalho, título e filtros são exibidos.
    """
    _ensure_reportlab()
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # Cabeçalho fixo: Turna
    header_style = ParagraphStyle(
        name="ReportHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        spaceAfter=6,
    )
    elements.append(Paragraph(REPORT_HEADER_TITLE, header_style))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Título do relatório
    elements.append(Paragraph(report_title, styles["Title"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Filtros utilizados
    filters_label = "Filtros utilizados: "
    filters_display = filters_text.strip() if filters_text else "Nenhum"
    elements.append(Paragraph(filters_label + filters_display, styles["Normal"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Tabela (conteúdo) se fornecida
    if headers and rows is not None:
        data = [headers] + rows
        col_count = len(headers)
        table = Table(data, colWidths=[None] * col_count)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ]
            )
        )
        elements.append(table)

    doc.build(elements)
    return buf.getvalue()


def build_report_cover_only(report_title: str, filters_text: str) -> bytes:
    """
    Gera apenas a página de capa (Turna + título + filtros), sem tabela.
    Usado para relatórios multi-página (demandas, escala) que já têm conteúdo gerado por outro módulo.
    """
    return build_report_pdf(report_title=report_title, filters_text=filters_text, headers=None, rows=None)


def format_filters_text(parts: list[tuple[str, str]]) -> str:
    """
    Monta texto legível dos filtros a partir de lista (rótulo, valor).
    Ex.: [("Nome", "x"), ("Desde", "01/01/2026")] -> "Nome: x | Desde: 01/01/2026"
    """
    if not parts:
        return ""
    return " | ".join(f"{label}: {value}" for label, value in parts if value)


def merge_pdf_with_cover(cover_bytes: bytes, content_bytes: bytes) -> bytes:
    """
    Concatena PDF de capa (primeira página) com o PDF de conteúdo.
    Usado para relatórios multi-página (demandas, escala) que já têm conteúdo gerado por output/day.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise RuntimeError("PyMuPDF (fitz) necessário para mesclar PDFs. Instale com: pip install pymupdf") from e
    doc_cover = fitz.open(stream=cover_bytes, filetype="pdf")
    doc_content = fitz.open(stream=content_bytes, filetype="pdf")
    doc_cover.insert_pdf(doc_content)
    out = doc_cover.tobytes()
    doc_cover.close()
    doc_content.close()
    return out
