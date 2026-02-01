"""
Layout reutilizável para relatórios PDF: cabeçalho "Turna", título do relatório,
seção de filtros (quando aplicada) e conteúdo (tabela). Todas as páginas de relatório
usam este layout para manter padrão visual único.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Iterable, Mapping
from typing import Any

# Parâmetros de paginação que não devem aparecer na seção "Filtros aplicados"
PAGINATION_PARAM_NAMES = frozenset({"limit", "offset"})


def parse_filters_from_frontend(filters_json: str | None) -> list[tuple[str, str]] | None:
    """
    Parseia o param 'filters' enviado pelo painel (JSON array de {label, value}).
    Fonte única de verdade: o título e o valor exibidos no painel vão para o relatório.
    Retorna None se filters_json for None, vazio ou inválido.
    """
    if not filters_json or not filters_json.strip():
        return None
    import json
    try:
        raw = json.loads(filters_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, list):
        return None
    result: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        value = item.get("value")
        if label is None or value is None:
            continue
        label_str = str(label).strip()
        value_str = str(value).strip()
        if label_str and value_str:
            result.append((label_str, value_str))
    return result if result else None


def query_params_to_filter_parts(
    params: Mapping[str, Any],
    param_labels: dict[str, str],
    exclude: Iterable[str] | None = None,
    formatters: dict[str, Callable[[Any], str]] | None = None,
) -> list[tuple[str, str]]:
    """
    Constrói a lista (label, valor) para a seção "Filtros aplicados" do PDF
    a partir dos query params da requisição.

    Assim, ao adicionar um novo filtro no endpoint de listagem, basta incluir
    o mesmo param no relatório e uma entrada em param_labels (e em formatters
    se precisar formatar, ex: hospital_id -> nome do hospital).

    Args:
        params: mapeamento nome_do_param -> valor (ex: request.query_params ou dict)
        param_labels: nome_do_param -> label de exibição (ex: {"name": "Nome", "status_list": "Situação"})
        exclude: nomes de params a ignorar (default: limit, offset)
        formatters: nome_do_param -> função valor -> str para formatar (ex: datas, IDs -> nome)
    """
    exclude_set = set(exclude) if exclude is not None else set(PAGINATION_PARAM_NAMES)
    formatters = formatters or {}
    result: list[tuple[str, str]] = []
    for key, label in param_labels.items():
        if key in exclude_set:
            continue
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if key in formatters:
            try:
                display = formatters[key](value)
            except Exception:
                display = str(value)
        else:
            display = str(value).strip()
        if display:
            result.append((label, display))
    return result


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
REPORT_BAR_BLUE = "#2563EB"


def _normalize_filters(filters: list[tuple[str, str]] | None) -> list[tuple[str, str]]:
    if not filters:
        return []
    normalized: list[tuple[str, str]] = []
    for label, value in filters:
        if value is None:
            continue
        txt = str(value).strip()
        if not txt:
            continue
        normalized.append((label, txt))
    return normalized


def _build_header_elements(doc, styles):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase.pdfmetrics import stringWidth

    # Turna: barra azul da margem esquerda até "Turna"; "Turna" alinhado à direita da página
    header_font = "Helvetica-Bold"
    header_font_size = 18
    header_style = ParagraphStyle(
        name="ReportHeader",
        parent=styles["Normal"],
        fontName=header_font,
        fontSize=header_font_size,
        textColor="#111827",
    )
    # Largura da coluna "Turna" = largura do texto + pequeno espaço; depende da fonte e do texto
    turna_text_w = stringWidth(REPORT_HEADER_TITLE, header_font, header_font_size)
    turna_col_w = turna_text_w + 8  # 8pt de folga
    bar_col_w = doc.width - turna_col_w  # barra ocupa o resto até "Turna"
    header_table = Table(
        [["", Paragraph(REPORT_HEADER_TITLE, header_style)]],
        colWidths=[bar_col_w, turna_col_w],
    )
    header_table.setStyle(
        TableStyle([
            ("LINEBELOW", (0, 0), (0, 0), 2, colors.HexColor(REPORT_BAR_BLUE)),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    return [header_table, Spacer(1, 10)]


def _build_title_elements(report_title: str, styles, doc):
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle

    # Título do relatório: só o texto, sem barra azul
    title_style = ParagraphStyle(
        name="ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor="#111827",
    )
    title_table = Table(
        [[Paragraph(report_title, title_style)]],
        colWidths=[doc.width],
    )
    title_table.setStyle(
        TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return [title_table, Spacer(1, 6)]


def _build_filters_elements(filters: list[tuple[str, str]], doc, styles):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle

    label_style = ParagraphStyle(
        name="FiltersLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor="#111827",
    )
    value_style = ParagraphStyle(
        name="FiltersValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor="#111827",
    )
    data = [[Paragraph(label, label_style), Paragraph(value, value_style)] for label, value in filters]
    table = Table(data, colWidths=[doc.width * 0.25, doc.width * 0.75])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E5E7EB")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [table, Spacer(1, 10)]


def _build_table_elements(headers: list[str], rows: list[list[str]], doc, styles):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    header_style = ParagraphStyle(
        name="TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.whitesmoke,
    )
    cell_style = ParagraphStyle(
        name="TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#111827"),
    )
    data = [[Paragraph(h, header_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(cell), cell_style) for cell in row])
    # Largura total = doc.width para a linha do cabeçalho ficar colada às bordas
    col_width = doc.width / len(headers)
    table = Table(data, colWidths=[col_width] * len(headers))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(REPORT_BAR_BLUE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#111827")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [table]


def build_report_pdf(
    report_title: str,
    filters: list[tuple[str, str]] | None = None,
    headers: list[str] | None = None,
    rows: list[list[str]] | None = None,
) -> bytes:
    """
    Gera PDF com layout padrão: cabeçalho Turna, título do relatório,
    seção de filtros (quando existir) e opcionalmente uma tabela (headers + rows).
    """
    _ensure_reportlab()
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.extend(_build_header_elements(doc, styles))
    elements.append(Spacer(1, 4))
    elements.extend(_build_title_elements(report_title, styles, doc))

    normalized_filters = _normalize_filters(filters)
    if normalized_filters:
        elements.extend(_build_filters_elements(normalized_filters, doc, styles))

    if headers and rows is not None:
        elements.extend(_build_table_elements(headers, rows, doc, styles))

    doc.build(elements)
    return buf.getvalue()


def build_report_cover_only(report_title: str, filters: list[tuple[str, str]] | None = None) -> bytes:
    """
    Gera apenas a página de capa (Turna + título + filtros), sem tabela.
    Usado para relatórios multi-página (demandas, escala) que já têm conteúdo gerado por outro módulo.
    """
    return build_report_pdf(report_title=report_title, filters=filters, headers=None, rows=None)


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
