"""
Aplicação principal.

Importante: a intenção é manter a MESMA lógica e a MESMA saída,
apenas separando em arquivos menores.
"""

import sys

from core import overlap
from data import DEMANDS_BY_DAY, PROS
from output import (
    print_day_result,
    print_demands_overview,
    print_professionals_overview,
    print_total_cost,
)
from strategy.cp_sat import solve_cp_sat
from strategy.greedy import solve_greedy

sys.stdout.reconfigure(encoding="utf-8")


def build_demands_from_by_day(demands_by_day: dict[int, list[dict]]) -> list[dict]:
    return [
        {"day": day, **d}
        for day, day_demands in demands_by_day.items()
        for d in day_demands
    ]


def main(allocation_mode: str = "greedy") -> None:
    demands = build_demands_from_by_day(DEMANDS_BY_DAY)
    pros = list(PROS)

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
        per_day, total_cost_all_days = solve_greedy(
            demands=demands,
            pros_by_sequence=pros_by_sequence,
            days=days,
            unassigned_penalty=UNASSIGNED_PENALTY,
            ped_unassigned_extra_penalty=PED_UNASSIGNED_EXTRA_PENALTY,
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

        print_total_cost(days, total_cost_all_days)
        return

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

