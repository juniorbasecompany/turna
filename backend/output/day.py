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


def _draw_report_header_on_canvas(
    c,
    page_w: float,
    page_h: float,
    report_title: str,
    filters: list[tuple[str, str]] | None,
    margin: float,
    colors,
) -> float:
    """
    Desenha cabeçalho do relatório (Turna + título + filtros) no topo da página em landscape.
    Retorna o y (coordenada ReportLab, origem embaixo) onde o conteúdo (grade) pode começar.
    """
    y = page_h - margin
    # Barra Turna
    bar_h = 28
    c.setFillColor(colors.HexColor("#111827"))
    c.rect(0, y - bar_h, page_w, bar_h, fill=1, stroke=0)
    c.setFillColor(colors.whitesmoke)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y - bar_h + 8, "Turna")
    y -= bar_h + 10
    # Título do relatório
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y - 14, report_title)
    y -= 20
    # Filtros (compacto)
    if filters:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#374151"))
        for label, value in filters[:8]:  # limite para caber na primeira página
            line = f"{label}: {value}"
            if len(line) > 100:
                line = line[:97] + "..."
            c.drawString(margin, y - 12, line)
            y -= 14
        y -= 6
    return y


def render_multi_day_pdf_bytes(
    schedules: list[DaySchedule],
    *,
    report_title: str | None = None,
    filters: list[tuple[str, str]] | None = None,
) -> bytes:
    """
    Renderiza múltiplos `DaySchedule` no mesmo PDF (uma sequência de páginas) e retorna bytes.
    Todas as páginas em landscape. Se report_title e filters forem passados, o título e filtros
    são desenhados no topo da primeira página e a grade do primeiro dia começa logo abaixo.
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

    first_page_header = report_title is not None and (report_title or filters)
    content_top_y: float | None = None
    if first_page_header and (report_title or filters):
        content_top_y = _draw_report_header_on_canvas(
            c, page_w, page_h, report_title or "", filters or [], 18, colors
        )

    for i, schedule in enumerate(schedules):
        top_y = content_top_y if (i == 0 and content_top_y is not None) else None
        _render_pdf_to_canvas(
            c, schedule, page_w=page_w, page_h=page_h, colors=colors, pdfmetrics=pdfmetrics, content_top_y=top_y
        )
        if i != len(schedules) - 1:
            c.showPage()
        content_top_y = None  # só na primeira página

    c.save()
    return buf.getvalue()


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
    margin = 18
    header_h = 42
    row_h = 22
    name_col_w = 210

    grid_x0 = margin + name_col_w
    grid_x1 = page_w - margin
    grid_w = grid_x1 - grid_x0
    if grid_w <= 100:
        raise RuntimeError("Página pequena demais para o layout")

    day_start = schedule.day_start_min
    day_end = schedule.day_end_min
    day_span = max(1, day_end - day_start)

    # Topo da área de desenho: abaixo do header do relatório (1ª página) ou topo da página.
    # Após showPage() (continuação do mesmo dia), usar topo completo da nova página.
    current_top_y: list[float] = [
        content_top_y if content_top_y is not None else page_h - margin
    ]

    def x_at(minute: int) -> float:
        minute = max(day_start, min(day_end, minute))
        frac = (minute - day_start) / day_span
        return grid_x0 + frac * grid_w

    def draw_header() -> float:
        y_top = current_top_y[0]
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y_top - 16, schedule.title)

        # Linha base do cabeçalho da grade
        y_grid_top = y_top - header_h
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(1)
        c.line(margin, y_grid_top, page_w - margin, y_grid_top)

        # Coluna nomes (separador)
        c.setStrokeColor(colors.grey)
        c.setLineWidth(1)
        c.line(grid_x0, y_grid_top, grid_x0, margin)

        # Marcas de hora
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        start_hour = day_start // 60
        end_hour = int(math.ceil(day_end / 60))
        for h in range(start_hour, end_hour + 1):
            m = h * 60
            x = x_at(m)
            major = (m % 60 == 0)
            c.setStrokeColor(colors.lightgrey if major else colors.whitesmoke)
            c.setLineWidth(1 if major else 0.5)
            c.line(x, y_grid_top, x, margin)
            if major and (day_start <= m <= day_end):
                c.drawString(x + 2, y_top - header_h + 4, f"{h:02d}")

        return y_grid_top

    def draw_row(y_top: float, idx: int, row: Row) -> None:
        y0 = y_top - row_h
        # Linha horizontal
        c.setStrokeColor(colors.whitesmoke)
        c.setLineWidth(1)
        c.line(margin, y0, page_w - margin, y0)

        # Nome
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawRightString(margin + 22, y0 + 6, f"{idx:02d}")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin + 28, y0 + 6, row.name)

        # Férias (quadro vazio com borda pontilhada)
        _corner_radius = 3
        for vac in row.vacations:
            xs = x_at(vac.interval.start_min)
            xe = x_at(vac.interval.end_min)
            if xe <= xs:
                continue
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.setDash(2, 2)  # pontilhado
            c.roundRect(xs, y0 + 2, xe - xs, row_h - 4, _corner_radius, stroke=1, fill=0)
            c.setDash([])  # restaura linha sólida

        # Eventos
        for ev in row.events:
            xs = x_at(ev.interval.start_min)
            xe = x_at(ev.interval.end_min)
            if xe <= xs:
                continue
            has_color = ev.color_rgb is not None
            if has_color:
                r, g, b = ev.color_rgb
                c.setFillColorRGB(r, g, b)
            else:
                # Sem cor: quadro sem preenchimento (fundo branco)
                c.setFillColor(colors.white)
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.25)
            c.roundRect(xs, y0 + 2, xe - xs, row_h - 4, _corner_radius, stroke=1, fill=1)

            # Linha 1: procedure à esquerda, room à direita (mesma linha)
            pad_x = 4
            block_w = max(10, (xe - xs) - 2 * pad_x)
            half_w = max(5, (block_w - 6) / 2)  # divide espaço, 6pt de folga entre
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 7.5)  # procedure sem negrito
            proc_ok = _truncate_to_width(pdfmetrics, ev.title, "Helvetica", 7.5, half_w)
            if proc_ok:
                c.drawString(xs + pad_x, y0 + 11, proc_ok)
            if ev.subtitle:
                room_ok = _truncate_to_width(pdfmetrics, ev.subtitle.strip(), "Helvetica", 7.5, half_w)
                if room_ok:
                    c.drawRightString(xe - pad_x, y0 + 11, room_ok)

            # Horário: início à esquerda, fim à direita; se não couber ambos, só o inicial
            # Trunca por largura para não extrapolar a caixa
            c.setFont("Helvetica", 6.5)
            c.setFillColor(colors.black)
            start_str = _fmt_minutes(ev.interval.start_min)
            end_str = _fmt_minutes(ev.interval.end_min)
            w_start = pdfmetrics.stringWidth(start_str, "Helvetica", 6.5)
            w_end = pdfmetrics.stringWidth(end_str, "Helvetica", 6.5)
            start_ok = _truncate_to_width(pdfmetrics, start_str, "Helvetica", 6.5, block_w)
            if start_ok:
                if w_start + 6 + w_end <= block_w:
                    c.drawString(xs + pad_x, y0 + 4, start_str)
                    c.drawRightString(xe - pad_x, y0 + 4, end_str)
                else:
                    c.drawString(xs + pad_x, y0 + 4, start_ok)

    # Paginação simples: ao mudar de página, próximo cabeçalho usa topo completo
    y = draw_header()
    idx = 1
    for row in schedule.rows:
        if y - row_h < margin + 6:
            c.showPage()
            current_top_y[0] = page_h - margin
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

