"""
Aplicação principal.

Importante: a intenção é manter a MESMA lógica e a MESMA saída,
apenas separando em arquivos menores.
"""

import sys

from ortools.sat.python import cp_model

from core import greedy_allocate, overlap
from data import DEMANDS_BY_DAY, PROS
from diagnose import diagnose_infeasibility
from output import ANSI_RESET, ANSI_YELLOW, USE_ANSI_COLORS, fmt_time_range, yellow

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

    if ALLOCATION_MODE == "greedy":
        total_cost_all_days = 0

        print("Demandas")
        for day in range(1, days + 1):
            print(f"Dia {day}")
            for d in demands:
                if d["day"] != day:
                    continue
                did_txt = yellow(d["id"]) if d["is_pediatric"] else d["id"]
                time_txt = fmt_time_range(d["start"], d["end"], d["is_pediatric"])
                ped_tag = " 👶" if d["is_pediatric"] else ""
                print(f"{did_txt} - {time_txt}{ped_tag}")

        print()
        print("Profissionais")
        for p in pros_by_sequence:
            tags = []
            for (vs, ve) in p["vacation"]:
                tags.append(f"folga {vs}-{ve}")
            tags_str = (" ".join(tags)) if tags else "-"
            pid_txt = (
                f"{ANSI_YELLOW}{p['id']}{ANSI_RESET}"
                if p["can_peds"] and USE_ANSI_COLORS
                else p["id"]
            )
            print(f"{p['sequence']:02d} {pid_txt} {tags_str}")

        n_pros = len(pros_by_sequence)

        # Rodízio fixo por dia (independente de quantos profissionais foram "usados").
        # Dia 1 começa no primeiro da lista (sequence 1), como era antes.
        base_shift = 0

        for day in range(days):
            day_num = day + 1
            demands_day = [d for d in demands if d["day"] == day_num]

            start_idx = (base_shift + day) % n_pros
            pros_for_day = pros_by_sequence[start_idx:] + pros_by_sequence[:start_idx]

            assigned_by_demand, assigned_demands_by_pro, _used_count = greedy_allocate(demands_day, pros_for_day)
            solution_label = "GULOSA"
            _ = solution_label

            unassigned_count = sum(1 for di in range(len(demands_day)) if assigned_by_demand.get(di) is None)
            ped_unassigned_count = sum(
                1
                for di, d in enumerate(demands_day)
                if d["is_pediatric"] and assigned_by_demand.get(di) is None
            )
            total_cost = (
                UNASSIGNED_PENALTY * unassigned_count
                + PED_UNASSIGNED_EXTRA_PENALTY * ped_unassigned_count
            )
            total_cost_all_days += total_cost
            _ = total_cost

            print()
            print("=" * 40)
            print(f"Dia {day + 1}")

            print()
            print("HORÁRIO...: 012345678901234567890123")
            first_hour = 0
            last_hour_exclusive = 24
            for p in pros_for_day:
                pid = p["id"]
                chars = []
                for hour in range(first_hour, last_hour_exclusive):
                    hs = hour
                    he = hour + 1
                    on_vacation = any(overlap(vs, ve, hs, he) for (vs, ve) in p["vacation"])
                    if on_vacation:
                        chars.append("z")
                    else:
                        dem = next(
                            (d for d in assigned_demands_by_pro[pid] if overlap(d["start"], d["end"], hs, he)),
                            None,
                        )
                        if dem and dem["is_pediatric"] and USE_ANSI_COLORS:
                            chars.append(f"{ANSI_YELLOW}{dem['id']}{ANSI_RESET}")
                        else:
                            chars.append(dem["id"] if dem else "_")
                print(f"{p['sequence']:02d} {pid}: {''.join(chars)}")

            print()
            for di, d in enumerate(demands_day):
                assigned = assigned_by_demand.get(di)
                assigned_txt = assigned if assigned else "_______"
                did_txt = yellow(d["id"]) if d["is_pediatric"] else d["id"]
                assigned_out = yellow(assigned_txt) if (d["is_pediatric"] and assigned) else assigned_txt
                time_txt = fmt_time_range(d["start"], d["end"], d["is_pediatric"])
                print(f"{did_txt} {time_txt} {assigned_out}")

        print()
        print("=" * 40)
        print(f"Custo total (todos os {days} dias): {total_cost_all_days}")
        return

    # -------------------------
    # 2) MODELO CP-SAT (opcional)
    # -------------------------
    model = cp_model.CpModel()

    # Variável de decisão: x[p,di] = 1 se anestesista p faz a demanda di
    # (usamos índice di porque pode haver IDs repetidos em demands)
    x = {}
    for p in pros:
        for di, d in enumerate(demands):
            x[(p["id"], di)] = model.NewBoolVar(f"x_{p['id']}_{d['id']}_{di}")

    # u[di] = 1 se a demanda di ficar sem profissional (somente se ALLOW_UNASSIGNED)
    u = {}
    if ALLOW_UNASSIGNED:
        for di, d in enumerate(demands):
            u[di] = model.NewBoolVar(f"u_{d['id']}_{di}")

    # -------------------------
    # 3) REGRAS HARD (obrigatórias)
    # -------------------------
    for di, d in enumerate(demands):
        if ALLOW_UNASSIGNED:
            model.Add(sum(x[(p["id"], di)] for p in pros) + u[di] == 1)
        else:
            model.Add(sum(x[(p["id"], di)] for p in pros) == 1)

    overlap_pairs = []
    for i in range(len(demands)):
        for j in range(i + 1, len(demands)):
            di, dj = demands[i], demands[j]
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
                if overlap(vs, ve, d["start"], d["end"]):
                    model.Add(x[(pid, di)] == 0)

    # -------------------------
    # 4) OBJETIVO (custo)
    # -------------------------
    costs = []
    if ALLOW_UNASSIGNED:
        costs.extend(UNASSIGNED_PENALTY * u[di] for di in range(len(demands)))
    for p in pros:
        pid = p["id"]
        for di, d in enumerate(demands):
            # Reservar pediatras: usar pediatra em demanda não-pediátrica tem custo suave.
            if p["can_peds"] and (not d["is_pediatric"]):
                costs.append(PED_PRO_ON_NON_PED_PENALTY * x[(pid, di)])

    if ALLOW_UNASSIGNED:
        # Demanda pediátrica sem atendimento custa mais caro.
        costs.extend(
            PED_UNASSIGNED_EXTRA_PENALTY * u[di]
            for di, d in enumerate(demands)
            if d["is_pediatric"]
        )

    model.Minimize(sum(costs))

    # -------------------------
    # 5) RESOLVER
    # -------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    if status == cp_model.INFEASIBLE:
        print("Sem solução viável com as regras hard (inviável).")
        print("Isso significa que as restrições obrigatórias entram em conflito entre si.")
        diagnose_infeasibility(demands, pros)
        return
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Solver não retornou solução (status desconhecido/erro).")
        print("Status:", status)
        return

    solution_label = "ÓTIMA" if status == cp_model.OPTIMAL else "FACTÍVEL"
    total_cost = solver.ObjectiveValue()
    _ = solution_label
    _ = total_cost

    assigned_demands_by_pro = {p["id"]: [] for p in pros}
    assigned_by_demand = {}
    for di, d in enumerate(demands):
        assigned = None
        for p in pros:
            if solver.Value(x[(p["id"], di)]) == 1:
                assigned = p["id"]
                assigned_demands_by_pro[assigned].append(d)
                break
        assigned_by_demand[di] = assigned

    # -------------------------
    # 6) EXIBIR RESULTADO
    # -------------------------
    print()

    for di, d in enumerate(demands):
        assigned = assigned_by_demand.get(di)
        assigned_txt = assigned if assigned else "_______"
        did_txt = yellow(d["id"]) if d["is_pediatric"] else d["id"]
        assigned_out = yellow(assigned_txt) if (d["is_pediatric"] and assigned) else assigned_txt
        time_txt = fmt_time_range(d["start"], d["end"], d["is_pediatric"])
        print(f"{did_txt} {time_txt} {assigned_out}")

    first_hour = 0
    last_hour_exclusive = 24

    print()
    print("Demandas")
    for d in demands:
        did_txt = yellow(d["id"]) if d["is_pediatric"] else d["id"]
        time_txt = fmt_time_range(d["start"], d["end"], d["is_pediatric"])
        ped_tag = " 👶" if d["is_pediatric"] else ""
        print(f"{did_txt} - {time_txt}{ped_tag}")

    print()
    print("Profissionais")
    for p in pros_by_sequence:
        tags = []
        for (vs, ve) in p["vacation"]:
            tags.append(f"folga {vs}-{ve}")
        tags_str = (" ".join(tags)) if tags else "-"
        pid_txt = (
            f"{ANSI_YELLOW}{p['id']}{ANSI_RESET}"
            if p["can_peds"] and USE_ANSI_COLORS
            else p["id"]
        )
        print(f"{pid_txt} {tags_str}")

    print()
    print("Alocados entre 0 a 23 horas")
    print("HORÁRIO: 012345678901234567890123")
    for p in pros_by_sequence:
        pid = p["id"]
        chars = []
        for hour in range(first_hour, last_hour_exclusive):
            hs = hour
            he = hour + 1
            on_vacation = any(overlap(vs, ve, hs, he) for (vs, ve) in p["vacation"])
            if on_vacation:
                chars.append("z")
            else:
                dem = next(
                    (d for d in assigned_demands_by_pro[pid] if overlap(d["start"], d["end"], hs, he)),
                    None,
                )
                if dem and dem["is_pediatric"] and USE_ANSI_COLORS:
                    chars.append(f"{ANSI_YELLOW}{dem['id']}{ANSI_RESET}")
                else:
                    chars.append(dem["id"] if dem else "_")
        print(f"{pid}: {''.join(chars)}")

    uncovered_demands = [d for di, d in enumerate(demands) if assigned_by_demand.get(di) is None]
    _ = uncovered_demands

