"""
Gera um PDF (1 dia) com visual de "escala" em grade de horário.

Uso (recomendado):
  py -m output.day --in day.json --out day.pdf

Gerar um JSON de exemplo:
  py -m output.day --make-example example_day.json

Formato do JSON (exemplo):
{
  "title": "Escala - 12/01/2026",
  "day_start": "06:00",
  "day_end": "22:00",
  "rows": [
    {
      "name": "Augusto, Joao",
      "events": [
        {
          "start": "06:00",
          "end": "07:45",
          "title": "Adenoidecto;HUBC6",
          "subtitle": "Marques de O",
          "color": "#4CAF50"
        }
      ],
      "vacations": [
        {"start": "07:00", "end": "22:00", "label": "FÉRIAS"}
      ]
    }
  ]
}

Notas:
- Horários aceitam "HH:MM" ou inteiros (hora cheia, ex.: 7).
- Se "color" não vier, uma cor é escolhida determinísticamente pelo título.

Dependência:
  pip install reportlab
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _require_reportlab():
    try:
        from reportlab.lib import colors  # noqa: F401
        from reportlab.lib.pagesizes import A4, landscape  # noqa: F401
        from reportlab.pdfbase import pdfmetrics  # noqa: F401
        from reportlab.pdfgen.canvas import Canvas  # noqa: F401
    except Exception as e:
        print("Erro: dependência ausente para gerar PDF.")
        print("Instale com: pip install reportlab")
        raise SystemExit(2) from e


def _parse_time_to_minutes(value: Any) -> int:
    if value is None:
        raise ValueError("horário ausente")

    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"horário inválido: {value}")
        # Inteiros/floats representam hora cheia.
        minutes = int(round(float(value) * 60))
        if minutes % 60 != 0:
            # Mantém compatível com "7.5" = 07:30, etc.
            return minutes
        return minutes

    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            raise ValueError("horário vazio")
        if ":" in txt:
            hh, mm = txt.split(":", 1)
            h = int(hh)
            m = int(mm)
            if h < 0 or h > 23 or m < 0 or m > 59:
                raise ValueError(f"horário fora do intervalo: {value}")
            return h * 60 + m
        # String numérica "7" / "7.5"
        minutes = int(round(float(txt) * 60))
        return minutes

    raise TypeError(f"tipo de horário não suportado: {type(value).__name__}")


def _fmt_minutes(m: int) -> str:
    h = (m // 60) % 24
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


# Constante para aproximação de arco circular por Bezier (quarter circle)
_BEZIER_KAPPA = 0.5522847498


def _draw_rect_top_rounded(c, x_left: float, y_bot: float, width: float, height: float, radius: float) -> None:
    """
    Desenha um retângulo preenchido com apenas os cantos superiores arredondados.
    Usado na faixa colorida do event para coincidir com o roundRect do contorno.
    """
    if width <= 0 or height <= 0:
        return
    if radius <= 0 or height < radius or width < 2 * radius:
        c.rect(x_left, y_bot, width, height, fill=1, stroke=0)
        return
    x_right = x_left + width
    y_top = y_bot + height
    r = min(radius, width / 2.0, height)
    k = _BEZIER_KAPPA
    try:
        c.saveState()
        c.moveTo(x_left, y_bot)
        c.lineTo(x_right, y_bot)
        c.lineTo(x_right, y_top - r)
        c.curveTo(x_right, y_top - r + r * k, x_right - r + r * k, y_top, x_right - r, y_top)
        c.lineTo(x_left + r, y_top)
        c.curveTo(x_left + r - r * k, y_top, x_left, y_top - r + r * k, x_left, y_top - r)
        c.closePath()
        c.fill()
    except Exception:
        c.rect(x_left, y_bot, width, height, fill=1, stroke=0)
    finally:
        try:
            c.restoreState()
        except Exception:
            pass


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    txt = value.strip().lstrip("#")
    if len(txt) == 3:
        txt = "".join(ch * 2 for ch in txt)
    if len(txt) != 6:
        raise ValueError(f"cor hex inválida: {value}")
    r = int(txt[0:2], 16) / 255.0
    g = int(txt[2:4], 16) / 255.0
    b = int(txt[4:6], 16) / 255.0
    return (r, g, b)


def _pick_color_from_text(s: str) -> tuple[float, float, float]:
    # Paleta "calma" inspirada em agendas: azul/verde/ciano/roxo/laranja.
    palette = [
        "#3B82F6",  # blue
        "#10B981",  # emerald
        "#06B6D4",  # cyan
        "#8B5CF6",  # violet
        "#F59E0B",  # amber
        "#22C55E",  # green
        "#0EA5E9",  # sky
    ]
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return _hex_to_rgb(palette[h % len(palette)])


@dataclass(frozen=True)
class Interval:
    start_min: int
    end_min: int

    def overlaps(self, other: Interval) -> bool:
        return self.start_min < other.end_min and other.start_min < self.end_min


@dataclass(frozen=True)
class Event:
    interval: Interval
    title: str
    subtitle: str | None = None
    color_rgb: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class Vacation:
    interval: Interval
    label: str = "FÉRIAS"


@dataclass(frozen=True)
class Row:
    name: str
    events: list[Event]
    vacations: list[Vacation]


@dataclass(frozen=True)
class DaySchedule:
    title: str
    day_start_min: int
    day_end_min: int
    rows: list[Row]


def _load_schedule(path: Path) -> DaySchedule:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("JSON raiz deve ser um objeto")

    title = str(raw.get("title") or "Escala (1 dia)")
    day_start_min = _parse_time_to_minutes(raw.get("day_start", "06:00"))
    day_end_min = _parse_time_to_minutes(raw.get("day_end", "22:00"))
    if day_end_min <= day_start_min:
        raise ValueError("day_end deve ser maior que day_start")

    rows_raw = raw.get("rows") or []
    if not isinstance(rows_raw, list):
        raise ValueError('"rows" deve ser uma lista')

    rows: list[Row] = []
    for r in rows_raw:
        if not isinstance(r, dict):
            raise ValueError("cada item de rows deve ser um objeto")
        name = str(r.get("name") or "").strip()
        if not name:
            raise ValueError("row.name é obrigatório")

        events: list[Event] = []
        events_raw = r.get("events") or []
        if not isinstance(events_raw, list):
            raise ValueError("row.events deve ser uma lista")
        for ev in events_raw:
            if not isinstance(ev, dict):
                raise ValueError("cada item de events deve ser um objeto")
            s = _parse_time_to_minutes(ev.get("start"))
            e = _parse_time_to_minutes(ev.get("end"))
            if e <= s:
                raise ValueError(f"evento com end <= start em {name}: {ev}")
            title_ev = str(ev.get("title") or "").strip()
            if not title_ev:
                raise ValueError(f"evento sem title em {name}: {ev}")
            subtitle_ev = ev.get("subtitle")
            subtitle_txt = str(subtitle_ev).strip() if subtitle_ev is not None else None
            color_txt = ev.get("color")
            if color_txt is None:
                rgb = _pick_color_from_text(title_ev)
            else:
                rgb = _hex_to_rgb(str(color_txt))
            events.append(
                Event(
                    interval=Interval(s, e),
                    title=title_ev,
                    subtitle=subtitle_txt if subtitle_txt else None,
                    color_rgb=rgb,
                )
            )

        vacations: list[Vacation] = []
        vacations_raw = r.get("vacations") or []
        if not isinstance(vacations_raw, list):
            raise ValueError("row.vacations deve ser uma lista")
        for v in vacations_raw:
            if not isinstance(v, dict):
                raise ValueError("cada item de vacations deve ser um objeto")
            s = _parse_time_to_minutes(v.get("start"))
            e = _parse_time_to_minutes(v.get("end"))
            if e <= s:
                raise ValueError(f"férias com end <= start em {name}: {v}")
            label = str(v.get("label") or "FÉRIAS").strip() or "FÉRIAS"
            vacations.append(Vacation(interval=Interval(s, e), label=label))

        rows.append(Row(name=name, events=events, vacations=vacations))

    return DaySchedule(
        title=title,
        day_start_min=day_start_min,
        day_end_min=day_end_min,
        rows=rows,
    )


def _truncate_to_width(pdfmetrics, text: str, font_name: str, font_size: float, max_width: float) -> str:
    """Trunca texto para caber em max_width (em pontos), removendo caracteres do fim."""
    if not text or max_width <= 0:
        return ""
    if pdfmetrics.stringWidth(text, font_name, font_size) <= max_width:
        return text
    for i in range(len(text) - 1, 0, -1):
        candidate = text[:i]
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            return candidate
    return text[0] if text else ""


def _font_size_to_fit(
    pdfmetrics, text: str, font_name: str, max_width: float,
    initial_size: float = 7.5, min_size: float = 1.0, step: float = 0.25,
) -> tuple[float, str]:
    """
    Reduz tamanho da fonte até o texto caber em max_width.
    Retorna (font_size, text). Se não couber nem em min_size, trunca.
    """
    if not text or max_width <= 0:
        return (initial_size, "")
    margin = 2  # folga para evitar corte por arredondamento
    usable = max(5, max_width - margin)
    font_size = initial_size
    while font_size >= min_size:
        if pdfmetrics.stringWidth(text, font_name, font_size) <= usable:
            return (font_size, text)
        font_size -= step
    truncated = _truncate_to_width(pdfmetrics, text, font_name, min_size, max_width)
    return (min_size, truncated)


def _wrap_text(pdfmetrics, text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        candidate = (" ".join(cur + [w])).strip()
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                # palavra muito longa: trunca por largura e não adiciona resto
                lines.append(_truncate_to_width(pdfmetrics, w, font_name, font_size, max_width))
                cur = []  # evita re-adicionar no fim do loop
    if cur:
        lines.append(" ".join(cur))
    return lines


def render_pdf(schedule: DaySchedule, out_path: Path) -> None:
    _require_reportlab()
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen.canvas import Canvas

    page_w, page_h = landscape(A4)
    c = Canvas(str(out_path), pagesize=(page_w, page_h))

    _render_pdf_to_canvas(c, schedule, page_w=page_w, page_h=page_h, colors=colors, pdfmetrics=pdfmetrics)
    c.save()


def render_pdf_bytes(schedule: DaySchedule) -> bytes:
    """
    Renderiza um PDF em memória e retorna bytes.

    Observação: mantém `render_pdf()` para o uso via CLI.
    """
    _require_reportlab()
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen.canvas import Canvas

    page_w, page_h = landscape(A4)
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(page_w, page_h))
    _render_pdf_to_canvas(c, schedule, page_w=page_w, page_h=page_h, colors=colors, pdfmetrics=pdfmetrics)
    c.save()
    return buf.getvalue()


# Cor da barra do cabeçalho da grade (título do dia + horários)
_REPORT_BAR_BLUE = "#2563EB"

# Dimensões do layout da grade (usado em _render e no Flowable)
_GRID_MARGIN = 0  # margem interna em volta do canvas (grade); reduzida para evitar faixa em branco
_GRID_HEADER_H = 42
_GRID_EVENT_BOX_H = 64
_GRID_EVENT_V_PAD = 4
_GRID_ROW_H = _GRID_EVENT_BOX_H + 2 * _GRID_EVENT_V_PAD
_GRID_NAME_COL_W = 100


def get_day_schedule_natural_size(
    schedule: DaySchedule,
    box_width: float | None = None,
) -> tuple[float, float]:
    """
    Retorna (largura, altura) natural da grade para um DaySchedule.
    box_width: se informado, usa como largura (para ocupar 100% da largura disponível no flowable).
    """
    from reportlab.lib.pagesizes import A4, landscape
    if box_width is not None and box_width > 0:
        width = box_width
    else:
        width, _ = landscape(A4)
    margin = _GRID_MARGIN
    header_h = _GRID_HEADER_H
    row_h = _GRID_ROW_H
    n_rows = len(schedule.rows)
    height = margin + header_h + n_rows * row_h + margin
    return (width, height)


def _draw_day_schedule_in_rect(
    c,
    schedule: DaySchedule,
    box_w: float,
    box_h: float,
    colors,
    pdfmetrics,
) -> None:
    """
    Desenha a grade de um dia no retângulo (0, 0) a (box_w, box_h).
    Sem paginação (showPage). Usado pelo DayGridFlowable.
    """
    margin = _GRID_MARGIN
    header_h = _GRID_HEADER_H
    event_box_h = _GRID_EVENT_BOX_H
    event_v_pad = _GRID_EVENT_V_PAD
    row_h = _GRID_ROW_H
    name_col_w = _GRID_NAME_COL_W

    grid_x0 = margin + name_col_w
    grid_x1 = box_w - margin
    grid_w = grid_x1 - grid_x0
    if grid_w <= 100:
        return

    day_start = schedule.day_start_min
    day_end = schedule.day_end_min
    day_span = max(1, day_end - day_start)
    y_top = box_h - margin

    def x_at(minute: int) -> float:
        minute = max(day_start, min(day_end, minute))
        frac = (minute - day_start) / day_span
        return grid_x0 + frac * grid_w

    # Cabeçalho da grade (faixa azul + título do dia + marcas de hora)
    y_grid_top = y_top - header_h
    bar_blue = colors.HexColor(_REPORT_BAR_BLUE)
    c.setFillColor(bar_blue)
    c.rect(margin, y_grid_top, box_w - 2 * margin, header_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y_top - 16, schedule.title)
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.25)
    c.line(margin, y_grid_top, box_w - margin, y_grid_top)
    c.line(grid_x0, y_grid_top, grid_x0, margin)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.white)
    start_hour = day_start // 60
    end_hour = min(23, int(math.ceil(day_end / 60)))
    for h in range(start_hour, end_hour + 1):
        m = h * 60
        x = x_at(m)
        major = m % 60 == 0
        c.setStrokeColor(colors.lightgrey)
        c.line(x, y_grid_top, x, margin)
        if major and (day_start <= m <= day_end):
            c.drawString(x + 2, y_top - header_h + 4, f"{h:02d}")
    c.setDash([])

    # Linhas (nomes + eventos/férias)
    y = y_grid_top
    for row in schedule.rows:
        y -= row_h
        y0 = y
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.25)
        c.line(margin, y0, box_w - margin, y0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin + 2, y0 + event_v_pad + 6, row.name)

        _corner_radius = 3
        for vac in row.vacations:
            xs = x_at(vac.interval.start_min)
            xe = x_at(vac.interval.end_min)
            if xe <= xs:
                continue
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(0.25)
            c.setDash(0, 2)
            c.roundRect(xs, y0 + event_v_pad, xe - xs, event_box_h, _corner_radius, stroke=1, fill=0)
            c.setDash([])

        for ev in row.events:
            xs = x_at(ev.interval.start_min)
            xe = x_at(ev.interval.end_min)
            if xe <= xs:
                continue
            has_color = ev.color_rgb is not None
            if has_color:
                r, g, b = ev.color_rgb
                c.setFillColorRGB(r, g, b)
                c.setStrokeColor(colors.white)
                c.setLineWidth(0)
                c.roundRect(xs, y0 + event_v_pad, xe - xs, event_box_h, _corner_radius, stroke=0, fill=1)
                c.setFillColor(colors.white)
                _procedure_bar_h = 10
                c.rect(xs, y0 + event_v_pad, xe - xs, event_box_h - _procedure_bar_h, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.25)
            c.roundRect(xs, y0 + event_v_pad, xe - xs, event_box_h, _corner_radius, stroke=1, fill=0)

            pad = 2
            box_left = xs
            box_right = xe
            box_bot = y0 + event_v_pad
            box_top = y0 + event_v_pad + event_box_h
            block_w = max(10, (box_right - box_left) - 2 * pad)
            content_left = box_left + pad
            content_right = box_right - pad
            content_top = box_top - pad
            line_gap = 8
            y1 = content_top - 6
            y2 = y1 - line_gap
            y3 = y2 - line_gap
            y4 = box_bot + 2
            c.setFillColor(colors.black)

            proc_size, proc_text = _font_size_to_fit(pdfmetrics, ev.title, "Helvetica", block_w, 7.5, 5.0)
            if proc_text:
                c.setFont("Helvetica", proc_size)
                c.drawString(content_left, y1, proc_text)
            if ev.subtitle:
                room_size, room_text = _font_size_to_fit(pdfmetrics, ev.subtitle.strip(), "Helvetica", block_w, 7.5, 5.0)
                if room_text:
                    c.setFont("Helvetica", room_size)
                    c.drawRightString(content_right, y2, room_text)
            start_str = _fmt_minutes(ev.interval.start_min)
            end_str = _fmt_minutes(ev.interval.end_min)
            start_size, start_text = _font_size_to_fit(pdfmetrics, start_str, "Helvetica", block_w, 6.5, 5.0)
            end_size, end_text = _font_size_to_fit(pdfmetrics, end_str, "Helvetica", block_w, 6.5, 5.0)
            if start_text:
                c.setFont("Helvetica", start_size)
                c.drawString(content_left, y3, start_text)
            if end_text:
                c.setFont("Helvetica", end_size)
                c.drawRightString(content_right, y4, end_text)


def _get_flowable_base():
    from reportlab.platypus.flowables import Flowable
    return Flowable


class DayGridFlowable(_get_flowable_base()):
    """
    Flowable Platypus que desenha a grade de um dia (Canvas) no espaço alocado.
    Usa o espaço disponível (availWidth x availHeight) e escala a grade para caber.
    """

    def __init__(self, schedule: DaySchedule) -> None:
        super().__init__()
        self._schedule = schedule
        self._width: float = 0
        self._height: float = 0

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:
        self._width = availWidth
        self._height = availHeight
        return (availWidth, availHeight)

    def draw(self) -> None:
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics

        canvas = self.canv
        # Usar largura disponível para ocupar 100% da largura; altura natural
        nat_w, nat_h = get_day_schedule_natural_size(self._schedule, box_width=self._width)
        if nat_w <= 0 or nat_h <= 0:
            return
        # Escala só na vertical se necessário; largura já é self._width
        scale_x = 1.0
        scale_y = min(self._height / nat_h, 1.0) if nat_h > 0 else 1.0
        canvas.saveState()
        canvas.scale(scale_x, scale_y)
        _draw_day_schedule_in_rect(
            canvas,
            self._schedule,
            nat_w,
            nat_h,
            colors,
            pdfmetrics,
        )
        canvas.restoreState()


def render_multi_day_pdf_body_bytes(
    schedules: list[DaySchedule],
    first_page_content_top_y: float | None = None,
) -> bytes:
    """
    Renderiza apenas o corpo (grades de dias) no PDF, sem cabeçalho (Turna, título, filtros).
    Uma página landscape por dia; quebra de página dentro do mesmo dia quando não cabe.
    Usado junto com capa Platypus (build_report_cover_only + merge_pdf_cover_with_body_first_page).
    first_page_content_top_y: se informado, reserva o topo da primeira página para a capa
    (corpo começa logo abaixo na mesma página).
    """
    if not schedules:
        raise ValueError("schedules vazio")

    _require_reportlab()
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen.canvas import Canvas

    page_w, page_h = landscape(A4)
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(page_w, page_h))

    for i, schedule in enumerate(schedules):
        # Só a primeira página do corpo usa content_top_y (espaço reservado para a capa).
        content_top_y = first_page_content_top_y if i == 0 else None
        _render_pdf_to_canvas(
            c,
            schedule,
            page_w=page_w,
            page_h=page_h,
            colors=colors,
            pdfmetrics=pdfmetrics,
            content_top_y=content_top_y,
        )
        if i != len(schedules) - 1:
            c.showPage()

    c.save()
    return buf.getvalue()


def expand_schedule_rows_for_test(
    schedules: list[DaySchedule],
    factor: int = 3,
) -> list[DaySchedule]:
    """
    Replica cada linha (member) N vezes no mesmo dia, para forçar quebra de página em testes.
    Apenas para uso com TURNA_TEST_TRIPLE_SCHEDULE_ROWS=1.
    """
    result: list[DaySchedule] = []
    for s in schedules:
        new_rows: list[Row] = []
        for row in s.rows:
            for _ in range(factor):
                new_rows.append(row)
        result.append(
            DaySchedule(
                title=s.title,
                day_start_min=s.day_start_min,
                day_end_min=s.day_end_min,
                rows=new_rows,
            )
        )
    return result


def render_multi_day_pdf_bytes(
    schedules: list[DaySchedule],
    *,
    report_title: str | None = None,
    filters: list[tuple[str, str]] | None = None,
) -> bytes:
    """
    Renderiza múltiplos `DaySchedule` no mesmo PDF (uma sequência de páginas) e retorna bytes.
    Sem título/filtros: só as grades (body). Com título/filtros: use capa Platypus + body + merge nos chamadores.
    Mantido para compatibilidade (ex.: publish sem capa).
    """
    return render_multi_day_pdf_body_bytes(schedules)


def _render_pdf_to_canvas(
    c,
    schedule: DaySchedule,
    *,
    page_w: float,
    page_h: float,
    colors,
    pdfmetrics,
    content_top_y: float | None = None,
) -> None:
    from reportlab.lib.units import cm

    margin_x = 1 * cm
    margin_top = 1.5 * cm
    margin_bottom = 1.5 * cm
    header_h = 42
    # Altura do event fixa; espaço acima/abaixo do event = event_v_pad
    event_box_h = 34
    event_v_pad = 4
    row_h = event_box_h + 2 * event_v_pad
    name_col_w = 100

    grid_x0 = margin_x + name_col_w
    grid_x1 = page_w - margin_x
    grid_w = grid_x1 - grid_x0
    if grid_w <= 100:
        raise RuntimeError("Página pequena demais para o layout")

    day_start = schedule.day_start_min
    day_end = schedule.day_end_min
    day_span = max(1, day_end - day_start)

    # Topo da área de desenho: abaixo do header do relatório (1ª página) ou topo da página.
    # Após showPage() (continuação do mesmo dia), usar topo completo da nova página.
    current_top_y: list[float] = [
        content_top_y if content_top_y is not None else page_h - margin_top
    ]

    def x_at(minute: int) -> float:
        minute = max(day_start, min(day_end, minute))
        frac = (minute - day_start) / day_span
        return grid_x0 + frac * grid_w

    def draw_header() -> float:
        y_top = current_top_y[0]
        y_grid_top = y_top - header_h
        bar_blue = colors.HexColor(_REPORT_BAR_BLUE)

        # Faixa azul do cabeçalho (mesmo padrão do cabeçalho da tabela nos relatórios)
        c.setFillColor(bar_blue)
        c.rect(margin_x, y_grid_top, page_w - 2 * margin_x, header_h, fill=1, stroke=0)

        # Título do dia e marcas de hora em branco
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin_x, y_top - 16, schedule.title)

        # Linha base do cabeçalho da grade
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.25)
        c.line(margin_x, y_grid_top, page_w - margin_x, y_grid_top)

        # Coluna nomes (separador)
        c.line(grid_x0, y_grid_top, grid_x0, margin_bottom)

        # Marcas de hora; linhas verticais pontilhadas
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.white)
        start_hour = day_start // 60
        end_hour = min(23, int(math.ceil(day_end / 60)))
        for h in range(start_hour, end_hour + 1):
            m = h * 60
            x = x_at(m)
            major = (m % 60 == 0)
            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(0.25)
            c.line(x, y_grid_top, x, margin_bottom)
            if major and (day_start <= m <= day_end):
                c.drawString(x + 2, y_top - header_h + 4, f"{h:02d}")
        c.setDash([])

        return y_grid_top

    def draw_row(y_top: float, idx: int, row: Row) -> None:
        y0 = y_top - row_h
        # Linha horizontal
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.25)
        c.line(margin_x, y0, page_w - margin_x, y0)

        # Nome (sem numeração; alinhado à esquerda)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x + 2, y0 + event_v_pad + 6, row.name)

        # Férias (quadro vazio com borda pontilhada)
        _corner_radius = 3
        for vac in row.vacations:
            xs = x_at(vac.interval.start_min)
            xe = x_at(vac.interval.end_min)
            if xe <= xs:
                continue
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(0.25)
            c.setDash(0, 2)  # pontilhado
            c.roundRect(xs, y0 + event_v_pad, xe - xs, event_box_h, _corner_radius, stroke=1, fill=0)
            c.setDash([])  # restaura linha sólida

        # Eventos: cor de fundo apenas no topo (procedure); restante transparente
        _procedure_bar_h = 10  # altura da faixa colorida no topo
        for ev in row.events:
            xs = x_at(ev.interval.start_min)
            xe = x_at(ev.interval.end_min)
            if xe <= xs:
                continue
            has_color = ev.color_rgb is not None
            # Faixa colorida só no topo: preenche todo o event com a cor e cobre o resto com branco
            # Assim encosta nas bordas e os cantos superiores ficam idênticos ao roundRect do event
            if has_color:
                r, g, b = ev.color_rgb
                c.setFillColorRGB(r, g, b)
                c.setStrokeColor(colors.white)
                c.setLineWidth(0)
                c.roundRect(xs, y0 + event_v_pad, xe - xs, event_box_h, _corner_radius, stroke=0, fill=1)
                c.setFillColor(colors.white)
                y_band_bot = (y0 + event_v_pad + event_box_h) - _procedure_bar_h
                c.rect(xs, y0 + event_v_pad, xe - xs, event_box_h - _procedure_bar_h, stroke=0, fill=1)
            # Contorno do event (cinza mais escuro); fundo transparente no restante
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.25)
            c.roundRect(xs, y0 + event_v_pad, xe - xs, event_box_h, _corner_radius, stroke=1, fill=0)

            # 4 linhas: procedure (esq), room (dir), start (esq), end (dir)
            # Padding uniforme em todos os lados (2pt)
            pad = 2
            box_left = xs
            box_right = xe
            box_bot = y0 + event_v_pad
            box_top = y0 + event_v_pad + event_box_h
            block_w = max(10, (box_right - box_left) - 2 * pad)
            content_left = box_left + pad
            content_right = box_right - pad
            content_bot = box_bot + pad
            content_top = box_top - pad
            line_gap = 8
            y1 = content_top - 6
            y2 = y1 - line_gap
            y3 = y2 - line_gap
            y4 = content_bot + 2
            c.setFillColor(colors.black)

            proc_size, proc_text = _font_size_to_fit(pdfmetrics, ev.title, "Helvetica", block_w, 7.5, 5.0)
            if proc_text:
                c.setFont("Helvetica", proc_size)
                c.drawString(content_left, y1, proc_text)

            if ev.subtitle:
                room_size, room_text = _font_size_to_fit(pdfmetrics, ev.subtitle.strip(), "Helvetica", block_w, 7.5, 5.0)
                if room_text:
                    c.setFont("Helvetica", room_size)
                    c.drawRightString(content_right, y2, room_text)

            start_str = _fmt_minutes(ev.interval.start_min)
            end_str = _fmt_minutes(ev.interval.end_min)
            start_size, start_text = _font_size_to_fit(pdfmetrics, start_str, "Helvetica", block_w, 6.5, 5.0)
            end_size, end_text = _font_size_to_fit(pdfmetrics, end_str, "Helvetica", block_w, 6.5, 5.0)
            if start_text:
                c.setFont("Helvetica", start_size)
                c.drawString(content_left, y3, start_text)
            if end_text:
                c.setFont("Helvetica", end_size)
                c.drawRightString(content_right, y4, end_text)

    # Paginação simples: ao mudar de página, próximo cabeçalho usa topo completo
    y = draw_header()
    idx = 1
    for row in schedule.rows:
        if y - row_h < margin_bottom + 6:
            c.showPage()
            current_top_y[0] = page_h - margin_top
            y = draw_header()
        draw_row(y, idx, row)
        y -= row_h
        idx += 1


def _write_example(path: Path) -> None:
    example = {
        "title": "Escala - Exemplo (1 dia)",
        "day_start": "06:00",
        "day_end": "22:00",
        "rows": [
            {
                "name": "Augusto, Joao",
                "events": [
                    {
                        "start": "06:00",
                        "end": "07:45",
                        "title": "Adenoidecto",
                        "subtitle": "HUBC6 • Marques de O",
                        "color": "#22C55E",
                    },
                    {
                        "start": "09:50",
                        "end": "12:00",
                        "title": "Septoplastia; amig",
                        "subtitle": "HUBC6 • Marques de Oliveira",
                        "color": "#0EA5E9",
                    },
                ],
                "vacations": [],
            },
            {
                "name": "Stuker, Andre",
                "events": [],
                "vacations": [{"start": "07:00", "end": "22:00", "label": "FÉRIAS"}],
            },
            {
                "name": "Michelon, Bruno",
                "events": [
                    {
                        "start": "07:00",
                        "end": "08:45",
                        "title": "Protese de M",
                        "subtitle": "HUBC2 • Rafael M",
                        "color": "#10B981",
                    },
                    {
                        "start": "13:00",
                        "end": "20:00",
                        "title": "Prostatevesiculectomia Radical Robotica",
                        "subtitle": "HUBC6 • Perin Nunes",
                        "color": "#3B82F6",
                    },
                ],
                "vacations": [],
            },
        ],
    }
    path.write_text(json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gera PDF de escala (1 dia) a partir de JSON.")
    p.add_argument("--in", dest="in_path", help="Caminho do JSON de entrada.")
    p.add_argument("--out", dest="out_path", help="Caminho do PDF de saída.")
    p.add_argument("--make-example", dest="example_path", help="Gera um JSON de exemplo e sai.")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    if args.example_path:
        _write_example(Path(args.example_path))
        print(f"Exemplo gerado em: {args.example_path}")
        return 0

    if not args.in_path or not args.out_path:
        print("Erro: use --in e --out (ou --make-example).")
        return 2

    schedule = _load_schedule(Path(args.in_path))
    render_pdf(schedule, Path(args.out_path))
    print(f"PDF gerado em: {args.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

