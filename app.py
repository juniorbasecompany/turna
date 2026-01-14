"""
Aplicação principal.

Importante: a intenção é manter a MESMA lógica e a MESMA saída,
apenas separando em arquivos menores.
"""

import json
import sys
from pathlib import Path

from core import overlap
from output.console import (
    print_day_result,
    print_demands_overview,
    print_professionals_overview,
    print_total_cost,
)
from strategy.greedy.solve import solve_greedy

sys.stdout.reconfigure(encoding="utf-8")


def build_demands_from_by_day(demands_by_day: dict[int, list[dict]]) -> list[dict]:
    return [
        {"day": day, **d}
        for day, day_demands in demands_by_day.items()
        for d in day_demands
    ]


def _try_generate_day1_pdf(per_day: list[dict]) -> None:
    if not per_day:
        return

    item = next((it for it in per_day if it.get("day_number") == 1), None)
    if not item:
        return

    try:
        from output.day import (
            DaySchedule,
            Event,
            Interval,
            Row,
            Vacation,
            _pick_color_from_text,
            render_pdf,
        )
    except Exception as e:
        print(f"[pdf] Não consegui importar output.day: {e}", file=sys.stderr)
        return

    day_number = int(item["day_number"])
    pros_for_day: list[dict] = item["pros_for_day"]
    assigned_demands_by_pro: dict[str, list[dict]] = item["assigned_demands_by_pro"]
    demands_day: list[dict] = item["demands_day"]
    assigned_pids: list[str | None] = item["assigned_pids"]

    def to_minutes(h: int | float) -> int:
        return int(round(float(h) * 60))

    # Janela do dia (mantém um padrão parecido com 06–22 quando possível)
    min_h = min((d["start"] for d in demands_day), default=6)
    max_h = max((d["end"] for d in demands_day), default=22)
    for p in pros_for_day:
        for vs, ve in p.get("vacation", []):
            min_h = min(min_h, vs)
            max_h = max(max_h, ve)

    day_start_h = max(0, min(6, int(min_h)))
    day_end_h = min(24, max(22, int(max_h)))

    rows: list[Row] = []
    for p in pros_for_day:
        pid = p["id"]

        vacs: list[Vacation] = []
        for vs, ve in p.get("vacation", []):
            vacs.append(Vacation(interval=Interval(to_minutes(vs), to_minutes(ve)), label="FÉRIAS"))

        evs: list[Event] = []
        for d in assigned_demands_by_pro.get(pid, []):
            # CP-SAT guarda demandas de todos os dias; filtramos.
            if int(d.get("day", day_number)) != day_number:
                continue
            title = d["id"] + (" (PED)" if d.get("is_pediatric") else "")
            evs.append(
                Event(
                    interval=Interval(to_minutes(d["start"]), to_minutes(d["end"])),
                    title=title,
                    subtitle=None,
                    color_rgb=_pick_color_from_text(title),
                )
            )
        evs.sort(key=lambda e: (e.interval.start_min, e.interval.end_min, e.title))

        rows.append(Row(name=pid, events=evs, vacations=vacs))

    # Linha extra para demandas descobertas (quando ALLOW_UNASSIGNED=True).
    uncovered: list[Event] = []
    for d, ap in zip(demands_day, assigned_pids, strict=True):
        if ap is not None:
            continue
        title = d["id"] + (" (PED)" if d.get("is_pediatric") else "")
        uncovered.append(
            Event(
                interval=Interval(to_minutes(d["start"]), to_minutes(d["end"])),
                title=title,
                subtitle="DESC",
                color_rgb=(0.55, 0.14, 0.10),
            )
        )
    uncovered.sort(key=lambda e: (e.interval.start_min, e.interval.end_min, e.title))
    if uncovered:
        # Pode haver colisão de horários nas descobertas: quebramos em múltiplas linhas.
        lanes: list[list[Event]] = []
        for ev in uncovered:
            placed = False
            for lane in lanes:
                last = lane[-1]
                if last.interval.end_min <= ev.interval.start_min:
                    lane.append(ev)
                    placed = True
                    break
            if not placed:
                lanes.append([ev])

        for i, lane in enumerate(lanes):
            name = "Descobertas" if i == 0 else f"Descobertas {i + 1}"
            rows.append(Row(name=name, events=lane, vacations=[]))

    schedule = DaySchedule(
        title=f"Escala - Dia {day_number}",
        day_start_min=to_minutes(day_start_h),
        day_end_min=to_minutes(day_end_h),
        rows=rows,
    )

    out_path = Path("escala_dia1.pdf")
    try:
        render_pdf(schedule, out_path)
        print(f"[pdf] PDF gerado em: {out_path}", file=sys.stderr)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[pdf] Falha ao gerar PDF: {e}", file=sys.stderr)


def main(allocation_mode: str = "greedy") -> None:
    # Carrega demandas do arquivo JSON
    json_path = Path(__file__).resolve().parent / "test" / "demandas.json"
    with json_path.open(encoding="utf-8") as f:
        json_data = json.load(f)

    # Converte chaves de string para int (JSON usa strings como chaves)
    DEMANDS_BY_DAY = {int(k): v for k, v in json_data.items()}

    # Carrega profissionais do arquivo JSON
    pros_path = Path(__file__).resolve().parent / "test" / "profissionais.json"
    with pros_path.open(encoding="utf-8") as f:
        pros_json = json.load(f)

    # Converte vacation de listas para tuplas (JSON usa listas, código espera tuplas)
    pros = [
        {**p, "vacation": [tuple(v) for v in p["vacation"]]} for p in pros_json
    ]

    demands = build_demands_from_by_day(DEMANDS_BY_DAY)

    days = max(DEMANDS_BY_DAY.keys(), default=0)

    # -------------------------
    # 2) ALOCAÇÃO (1 dia)
    # -------------------------
    ALLOCATION_MODE = allocation_mode  # "greedy" | "cp-sat"

    # Se True, permite demandas sem profissional (entra como "Descobertas")
    ALLOW_UNASSIGNED = True
    # Penalidade por demanda sem atendimento:
    # - pediátrica é ainda mais penalizada, para priorizar "não deixar pediátrica descoberta"
    UNASSIGNED_PENALTY = 1000
    PED_UNASSIGNED_EXTRA_PENALTY = 1000  # total ped = 2000

    # Penalidade (suave) para evitar usar pediatra em demanda não-pediátrica,
    # quando existir alternativa. Ajuda o CP-SAT a "reservar" pediatras.
    PED_PRO_ON_NON_PED_PENALTY = 1

    pros_by_sequence = sorted(pros, key=lambda p: p["sequence"])
    print_demands_overview(demands, days)
    print_professionals_overview(pros_by_sequence)

    if ALLOCATION_MODE == "greedy":
        per_day, total_cost = solve_greedy(
            demands=demands,
            pros_by_sequence=pros_by_sequence,
            days=days,
            unassigned_penalty=UNASSIGNED_PENALTY,
            ped_unassigned_extra_penalty=PED_UNASSIGNED_EXTRA_PENALTY,
            base_shift=0,
        )
    else:
        # Import lazy: CP-SAT depende de ortools (opcional em modo greedy).
        from strategy.cd_sat.solve import solve_cp_sat

        per_day, total_cost = solve_cp_sat(
            demands=demands,
            pros=pros,
            pros_by_sequence=pros_by_sequence,
            days=days,
            allow_unassigned=ALLOW_UNASSIGNED,
            unassigned_penalty=UNASSIGNED_PENALTY,
            ped_unassigned_extra_penalty=PED_UNASSIGNED_EXTRA_PENALTY,
            ped_pro_on_non_ped_penalty=PED_PRO_ON_NON_PED_PENALTY,
            base_shift=0,
        )

    for item in per_day:
        print_day_result(
            day_number=item["day_number"],
            pros_for_day=item["pros_for_day"],
            assigned_demands_by_pro=item["assigned_demands_by_pro"],
            demands_day=item["demands_day"],
            assigned_pids=item["assigned_pids"],
            overlap_fn=overlap,
        )

    print_total_cost(days, total_cost)
    sys.stdout.flush()
    _try_generate_day1_pdf(per_day)

