"""
Estratégia CP-SAT (OR-Tools).
"""

from ortools.sat.python import cp_model

from core import overlap
from diagnose import diagnose_infeasibility


def solve_cp_sat(
    *,
    demands: list[dict],
    pros: list[dict],
    pros_by_sequence: list[dict],
    days: int,
    allow_unassigned: bool,
    unassigned_penalty: int,
    ped_unassigned_extra_penalty: int,
    ped_pro_on_non_ped_penalty: int,
    base_shift: int = 0,
) -> tuple[list[dict], float]:
    """
    Retorna:
      - per_day: lista de dicts com campos necessários para impressão (mesmo layout)
      - total_cost: objective do solver (float)
    """
    model = cp_model.CpModel()

    x = {}
    for p in pros:
        for di, d in enumerate(demands):
            x[(p["id"], di)] = model.NewBoolVar(f"x_{p['id']}_{d['id']}_{di}")

    u = {}
    if allow_unassigned:
        for di, d in enumerate(demands):
            u[di] = model.NewBoolVar(f"u_{d['id']}_{di}")

    # 3) REGRAS HARD
    for di, d in enumerate(demands):
        if allow_unassigned:
            model.Add(sum(x[(p["id"], di)] for p in pros) + u[di] == 1)
        else:
            model.Add(sum(x[(p["id"], di)] for p in pros) == 1)

    overlap_pairs = []
    for i in range(len(demands)):
        for j in range(i + 1, len(demands)):
            di, dj = demands[i], demands[j]
            if di["day"] != dj["day"]:
                continue
            if overlap(di["start"], di["end"], dj["start"], dj["end"]):
                overlap_pairs.append((i, j))

    for p in pros:
        pid = p["id"]
        for i, j in overlap_pairs:
            model.Add(x[(pid, i)] + x[(pid, j)] <= 1)

    for p in pros:
        if not p["can_peds"]:
            for di, d in enumerate(demands):
                if d["is_pediatric"]:
                    model.Add(x[(p["id"], di)] == 0)

    for p in pros:
        pid = p["id"]
        for (vs, ve) in p["vacation"]:
            for di, d in enumerate(demands):
                if d["day"] is None:
                    continue
                if overlap(vs, ve, d["start"], d["end"]):
                    model.Add(x[(pid, di)] == 0)

    # 4) OBJETIVO
    costs = []
    if allow_unassigned:
        costs.extend(unassigned_penalty * u[di] for di in range(len(demands)))

    for p in pros:
        for di, d in enumerate(demands):
            if p["can_peds"] and (not d["is_pediatric"]):
                costs.append(ped_pro_on_non_ped_penalty * x[(p["id"], di)])

    if allow_unassigned:
        costs.extend(
            ped_unassigned_extra_penalty * u[di]
            for di, d in enumerate(demands)
            if d["is_pediatric"]
        )

    model.Minimize(sum(costs))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    if status == cp_model.INFEASIBLE:
        print("Sem solução viável com as regras hard (inviável).")
        print("Isso significa que as restrições obrigatórias entram em conflito entre si.")
        diagnose_infeasibility(demands, pros)
        raise RuntimeError("CP-SAT infeasible")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Solver não retornou solução (status desconhecido/erro).")
        print("Status:", status)
        raise RuntimeError(f"CP-SAT status {status}")

    total_cost = solver.ObjectiveValue()

    assigned_demands_by_pro = {p["id"]: [] for p in pros}
    assigned_by_demand: dict[int, str | None] = {}
    for di, d in enumerate(demands):
        assigned = None
        for p in pros:
            if solver.Value(x[(p["id"], di)]) == 1:
                assigned = p["id"]
                assigned_demands_by_pro[assigned].append(d)
                break
        assigned_by_demand[di] = assigned

    # Preparar impressão no mesmo layout (por dia)
    n_pros = len(pros_by_sequence)
    per_day: list[dict] = []
    for day in range(days):
        day_num = day + 1
        start_idx = (base_shift + day) % n_pros
        pros_for_day = pros_by_sequence[start_idx:] + pros_by_sequence[:start_idx]

        day_items = [(gi, d) for gi, d in enumerate(demands) if d["day"] == day_num]
        demands_day = [d for _, d in day_items]
        assigned_pids = [assigned_by_demand.get(gi) for gi, _ in day_items]

        per_day.append(
            {
                "day_number": day_num,
                "pros_for_day": pros_for_day,
                "assigned_demands_by_pro": assigned_demands_by_pro,
                "demands_day": demands_day,
                "assigned_pids": assigned_pids,
            }
        )

    return per_day, total_cost

