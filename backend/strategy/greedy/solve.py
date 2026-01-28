"""
Estratégia ambiciosa: função de resolução usada pelo app (orquestrador).
"""

import logging

from .allocate import greedy_allocate

logger = logging.getLogger(__name__)


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
    import time

    total_cost_all_days = 0
    n_pros = len(pros_by_sequence)
    per_day: list[dict] = []

    logger.info(f"[SOLVE_GREEDY] Iniciando processamento: {days} dias, {len(demands)} demandas totais, {n_pros} profissionais")

    for day in range(days):
        day_start_time = time.time()
        day_num = day + 1
        demand_list_day = [d for d in demands if d["day"] == day_num]

        logger.debug(f"[SOLVE_GREEDY] Dia {day_num}: {len(demand_list_day)} demandas")

        start_idx = (base_shift + day) % n_pros
        pros_for_day = pros_by_sequence[start_idx:] + pros_by_sequence[:start_idx]

        allocate_start_time = time.time()
        assigned_by_demand, assigned_demands_by_pro, _used_count = greedy_allocate(demand_list_day, pros_for_day)
        allocate_duration = time.time() - allocate_start_time
        _ = _used_count

        logger.debug(f"[SOLVE_GREEDY] Dia {day_num}: alocação concluída em {allocate_duration:.3f}s, {len(assigned_demands_by_pro)} profissionais com alocações")

        unassigned_count = sum(1 for di in range(len(demand_list_day)) if assigned_by_demand.get(di) is None)
        ped_unassigned_count = sum(
            1
            for di, d in enumerate(demand_list_day)
            if d["is_pediatric"] and assigned_by_demand.get(di) is None
        )
        total_cost = (
            unassigned_penalty * unassigned_count
            + ped_unassigned_extra_penalty * ped_unassigned_count
        )
        total_cost_all_days += total_cost

        assigned_pids = [assigned_by_demand.get(i) for i in range(len(demand_list_day))]
        per_day.append(
            {
                "day_number": day_num,
                "pros_for_day": pros_for_day,
                "assigned_demands_by_pro": assigned_demands_by_pro,
                "demands_day": demand_list_day,
                "assigned_pids": assigned_pids,
            }
        )

        day_duration = time.time() - day_start_time
        logger.info(f"[SOLVE_GREEDY] Dia {day_num}/{days} concluído em {day_duration:.3f}s: {len(demand_list_day)} demandas, {unassigned_count} não alocadas, {ped_unassigned_count} pediátricas não alocadas, custo: {total_cost}")

    logger.info(f"[SOLVE_GREEDY] Processamento completo: {days} dias processados, custo total: {total_cost_all_days}")
    return per_day, total_cost_all_days

