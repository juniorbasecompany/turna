"""
Estratégia ambiciosa: função de resolução usada pelo app (orquestrador).
"""

from .allocate import greedy_allocate


def solve_greedy(
    *,
    demands: list[dict],
    pros_by_sequence: list[dict],
    days: int,
    unassigned_penalty: int,
    ped_unassigned_extra_penalty: int,
    base_shift: int = 0,
) -> tuple[list[dict], int]:
    """
    Retorna:
      - per_day: lista de dicts com campos necessários para impressão (mesmo layout)
      - total_cost_all_days: custo agregado (int)
    """
    total_cost_all_days = 0
    n_pros = len(pros_by_sequence)
    per_day: list[dict] = []

    for day in range(days):
        day_num = day + 1
        demands_day = [d for d in demands if d["day"] == day_num]

        start_idx = (base_shift + day) % n_pros
        pros_for_day = pros_by_sequence[start_idx:] + pros_by_sequence[:start_idx]

        assigned_by_demand, assigned_demands_by_pro, _used_count = greedy_allocate(demands_day, pros_for_day)
        _ = _used_count

        unassigned_count = sum(1 for di in range(len(demands_day)) if assigned_by_demand.get(di) is None)
        ped_unassigned_count = sum(
            1
            for di, d in enumerate(demands_day)
            if d["is_pediatric"] and assigned_by_demand.get(di) is None
        )
        total_cost = (
            unassigned_penalty * unassigned_count
            + ped_unassigned_extra_penalty * ped_unassigned_count
        )
        total_cost_all_days += total_cost

        assigned_pids = [assigned_by_demand.get(i) for i in range(len(demands_day))]
        per_day.append(
            {
                "day_number": day_num,
                "pros_for_day": pros_for_day,
                "assigned_demands_by_pro": assigned_demands_by_pro,
                "demands_day": demands_day,
                "assigned_pids": assigned_pids,
            }
        )

    return per_day, total_cost_all_days

