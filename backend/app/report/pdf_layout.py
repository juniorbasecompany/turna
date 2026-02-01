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


def _build_header_elements(doc, styles, header_title: str | None = None):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase.pdfmetrics import stringWidth

    header_text = header_title or REPORT_HEADER_TITLE

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
    turna_text_w = stringWidth(header_text, header_font, header_font_size)
    turna_col_w = turna_text_w + 8  # 8pt de folga
    bar_col_w = doc.width - turna_col_w  # barra ocupa o resto até "Turna"
    header_table = Table(
        [["", Paragraph(header_text, header_style)]],
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
    from reportlab.platypus import Flowable, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase.pdfmetrics import stringWidth

    label_style = ParagraphStyle(
        name="FiltersLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor="#111827",
    )
    value_style = ParagraphStyle(
        name="FiltersValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor="#111827",
    )
    # Cada filtro vira uma caixa; as caixas fluem e quebram de linha automaticamente
    block_bg = colors.HexColor("#E5E7EB")
    block_border = colors.HexColor("#D1D5DB")
    text_color = colors.HexColor("#111827")
    value_color = colors.HexColor("#2563EB")
    block_gap_x = 8
    block_gap_y = 6
    gap_between_label_value = 8
    padding_x = 6
    padding_y = 4

    class FiltersBlockFlowable(Flowable):
        def __init__(self, filter_list: list[tuple[str, str]]):
            super().__init__()
            self.filter_list = filter_list
            self._layout: list = []
            self._height = 0
            self._avail_width = 0

        def _truncate_text(self, text: str, font_name: str, font_size: int, max_width: float) -> str:
            if max_width <= 0:
                return ""
            if stringWidth(text, font_name, font_size) <= max_width:
                return text
            ellipsis = "..."
            ellipsis_width = stringWidth(ellipsis, font_name, font_size)
            if ellipsis_width > max_width:
                return ""
            low, high = 0, len(text)
            while low < high:
                mid = (low + high) // 2
                if stringWidth(text[:mid], font_name, font_size) + ellipsis_width <= max_width:
                    low = mid + 1
                else:
                    high = mid
            cut = max(0, low - 1)
            return f"{text[:cut]}{ellipsis}"

        def _build_layout(self, avail_width: float) -> tuple[list, float]:
            row_list: list = []
            row_item_list: list = []
            row_width = 0.0
            content_height = max(label_style.fontSize, value_style.fontSize)
            box_height = content_height + (padding_y * 2)

            for label, value in self.filter_list:
                label_text = str(label).strip()
                value_text = str(value).strip()
                label_width = stringWidth(label_text, label_style.fontName, label_style.fontSize)
                value_width = stringWidth(value_text, value_style.fontName, value_style.fontSize)
                content_width = label_width + gap_between_label_value + value_width
                box_width = content_width + (padding_x * 2)
                gap = gap_between_label_value

                if box_width > avail_width:
                    available_content_width = max(0, avail_width - (padding_x * 2))
                    label_width = min(label_width, available_content_width)
                    label_text = self._truncate_text(
                        label_text, label_style.fontName, label_style.fontSize, label_width
                    )
                    label_width = stringWidth(label_text, label_style.fontName, label_style.fontSize)
                    remaining_width = max(0, available_content_width - label_width)
                    gap = min(gap_between_label_value, remaining_width)
                    value_available = max(0, remaining_width - gap)
                    value_text = self._truncate_text(
                        value_text, value_style.fontName, value_style.fontSize, value_available
                    )
                    value_width = stringWidth(value_text, value_style.fontName, value_style.fontSize)
                    content_width = label_width + gap + value_width
                    box_width = content_width + (padding_x * 2)

                required_width = box_width if row_width == 0 else row_width + block_gap_x + box_width
                if required_width > avail_width and row_item_list:
                    row_list.append(row_item_list)
                    row_item_list = []
                    row_width = 0.0

                row_item_list.append(
                    {
                        "label": label_text,
                        "value": value_text,
                        "label_width": label_width,
                        "value_width": value_width,
                        "gap": gap,
                        "box_width": box_width,
                        "box_height": box_height,
                    }
                )
                row_width = box_width if row_width == 0 else row_width + block_gap_x + box_width

            if row_item_list:
                row_list.append(row_item_list)

            total_height = (len(row_list) * box_height) + (max(0, len(row_list) - 1) * block_gap_y)
            return row_list, total_height

        def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
            self._layout, self._height = self._build_layout(avail_width)
            self._avail_width = avail_width
            return avail_width, self._height

        def draw(self) -> None:
            if not self._layout:
                return
            canvas = self.canv
            y = self._height
            for row_item_list in self._layout:
                row_height = row_item_list[0]["box_height"]
                y -= row_height
                row_total_width = 0.0
                for idx, item in enumerate(row_item_list):
                    if idx > 0:
                        row_total_width += block_gap_x
                    row_total_width += item["box_width"]
                x = max(0.0, self._avail_width - row_total_width)
                for item in row_item_list:
                    box_width = item["box_width"]
                    canvas.setFillColor(block_bg)
                    canvas.setStrokeColor(block_border)
                    canvas.rect(x, y, box_width, row_height, stroke=1, fill=1)

                    label_y = y + padding_y + (row_height - (padding_y * 2) - label_style.fontSize) / 2
                    value_y = y + padding_y + (row_height - (padding_y * 2) - value_style.fontSize) / 2
                    canvas.setFillColor(text_color)
                    canvas.setFont(label_style.fontName, label_style.fontSize)
                    canvas.drawString(x + padding_x, label_y, item["label"])

                    value_x = x + padding_x + item["label_width"] + item["gap"]
                    canvas.setFillColor(value_color)
                    canvas.setFont(value_style.fontName, value_style.fontSize)
                    canvas.drawString(value_x, value_y, item["value"])

                    x += box_width + block_gap_x
                y -= block_gap_y

    flowable = FiltersBlockFlowable(filters)
    return [flowable, Spacer(1, 10)]


def _build_table_elements(
    headers: list[str],
    rows: list[list[str]],
    doc,
    styles,
    col_widths: list[float] | None = None,
):
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
    # Largura total = doc.width; col_widths opcional (frações 0-1 que somam 1)
    n = len(headers)
    if col_widths is not None and len(col_widths) == n:
        widths = [doc.width * w for w in col_widths]
    else:
        widths = [doc.width / n] * n
    table = Table(data, colWidths=widths)
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
    pagesize=None,
    header_title: str | None = None,
    col_widths: list[float] | None = None,
) -> bytes:
    """
    Gera PDF com layout padrão: cabeçalho Turna, título do relatório,
    seção de filtros (quando existir) e opcionalmente uma tabela (headers + rows).
    pagesize: tamanho da página (ex.: A4, landscape(A4)); None = A4.
    """
    _ensure_reportlab()
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    size = pagesize if pagesize is not None else A4
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=size,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.extend(_build_header_elements(doc, styles, header_title=header_title))
    elements.append(Spacer(1, 4))
    elements.extend(_build_title_elements(report_title, styles, doc))

    normalized_filters = _normalize_filters(filters)
    if normalized_filters:
        elements.extend(_build_filters_elements(normalized_filters, doc, styles))

    if headers and rows is not None:
        elements.extend(_build_table_elements(headers, rows, doc, styles, col_widths=col_widths))

    doc.build(elements)
    return buf.getvalue()


def build_report_cover_only(
    report_title: str,
    filters: list[tuple[str, str]] | None = None,
    pagesize=None,
    header_title: str | None = None,
) -> bytes:
    """
    Gera apenas a página de capa (Turna + título + filtros), sem tabela.
    Usado para relatórios multi-página (demandas, escala) que já têm conteúdo gerado por outro módulo.
    pagesize: tamanho da página (ex.: landscape(A4) para escalas/demandas); None = A4.
    """
    return build_report_pdf(
        report_title=report_title,
        filters=filters,
        headers=None,
        rows=None,
        pagesize=pagesize,
        header_title=header_title,
    )


def get_report_cover_total_height(
    report_title: str,
    filters: list[tuple[str, str]] | None = None,
    pagesize=None,
    header_title: str | None = None,
) -> float:
    """
    Calcula a altura total da capa (topMargin + conteúdo) em pontos.
    Usado para reservar espaço da capa na 1ª página do corpo.
    """
    _ensure_reportlab()
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    size = pagesize if pagesize is not None else A4
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=size,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements: list = []

    elements.extend(_build_header_elements(doc, styles, header_title=header_title))
    elements.append(Spacer(1, 4))
    elements.extend(_build_title_elements(report_title, styles, doc))

    normalized_filters = _normalize_filters(filters)
    if normalized_filters:
        elements.extend(_build_filters_elements(normalized_filters, doc, styles))

    total_h = 0.0
    for el in elements:
        _, h = el.wrap(doc.width, doc.height)
        total_h += h

    # Somar topMargin, porque o conteúdo começa abaixo da margem superior.
    return float(total_h + doc.topMargin)


def format_filters_text(parts: list[tuple[str, str]]) -> str:
    """
    Monta texto legível dos filtros a partir de lista (rótulo, valor).
    Ex.: [("Nome", "x"), ("Desde", "01/01/2026")] -> "Nome: x | Desde: 01/01/2026"
    """
    if not parts:
        return ""
    return " | ".join(f"{label}: {value}" for label, value in parts if value)


# Altura de fallback para a capa (em pontos) quando não for possível calcular dinamicamente.
COVER_HEIGHT_PT = 230


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


def merge_pdf_cover_with_body_first_page(
    cover_bytes: bytes,
    body_bytes: bytes,
    capa_height_pt: float,
) -> bytes:
    """
    Monta PDF com capa no topo da primeira página e corpo na mesma página logo abaixo.
    Página 1 = topo com capa (capa_height_pt) + conteúdo da primeira página do corpo;
    páginas 2, 3, ... = restantes páginas do corpo.
    Requer que o corpo tenha sido gerado com first_page_content_top_y reservando o topo.
    Capa: show_pdf_page com clip; fallback rasterizado sem flip para evitar espelhamento.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise RuntimeError("PyMuPDF (fitz) necessário para mesclar PDFs. Instale com: pip install pymupdf") from e
    doc_cover = fitz.open(stream=cover_bytes, filetype="pdf")
    doc_body = fitz.open(stream=body_bytes, filetype="pdf")
    if len(doc_cover) == 0 or len(doc_body) == 0:
        doc_cover.close()
        doc_body.close()
        return body_bytes if len(doc_body) > 0 else cover_bytes
    cover_page = doc_cover[0]
    body_first = doc_body[0]
    r_cover = cover_page.rect
    r_body = body_first.rect
    cover_h = min(float(capa_height_pt), float(r_cover.height))

    def _is_origin_top(page) -> bool:
        try:
            words = page.get_text("words") or []
        except Exception:
            return False
        if not words:
            return False
        for w in words:
            txt = (w[4] or "").strip().lower()
            if txt.startswith("turna") or txt.startswith("relatório"):
                return float(w[1]) < (page.rect.height / 2.0)
        return float(words[0][1]) < (page.rect.height / 2.0)

    origin_top = _is_origin_top(cover_page)
    if origin_top:
        # Origem no topo (y cresce para baixo): topo = y0 .. y0 + cover_h
        clip_cover = fitz.Rect(r_cover.x0, r_cover.y0, r_cover.x1, r_cover.y0 + cover_h)
        rect_top = fitz.Rect(r_body.x0, r_body.y0, r_body.x1, r_body.y0 + cover_h)
    else:
        # Origem no fundo (y cresce para cima): topo = y1 - cover_h .. y1
        clip_cover = fitz.Rect(r_cover.x0, r_cover.y1 - cover_h, r_cover.x1, r_cover.y1)
        rect_top = fitz.Rect(r_body.x0, r_body.y1 - cover_h, r_body.x1, r_body.y1)
    # Novo PDF: página 0 = cópia da primeira página do corpo.
    doc_out = fitz.open()
    doc_out.insert_pdf(doc_body, from_page=0, to_page=0)
    out_page = doc_out[0]
    # Desenhar a capa no topo: pixmap do topo da capa → PIL flip vertical → PNG → insert.
    # (PDF desenha a 1ª linha da imagem na base do rect; sem flip a capa sairia invertida.)
    try:
        out_page.show_pdf_page(
            rect_top, doc_cover, 0, clip=clip_cover, overlay=True
        )
    except Exception:
        # Fallback: rasterizar a capa sem flip para evitar espelhamento.
        pix = cover_page.get_pixmap(clip=clip_cover)
        out_page.insert_image(rect_top, pixmap=pix, overlay=True)
    # Anexar páginas 1 em diante do corpo.
    if len(doc_body) > 1:
        doc_out.insert_pdf(doc_body, from_page=1, to_page=len(doc_body) - 1)
    out = doc_out.tobytes()
    doc_out.close()
    doc_cover.close()
    doc_body.close()
    return out
