# pip install ortools
from datetime import datetime, timedelta
import sys

from ortools.sat.python import cp_model

sys.stdout.reconfigure(encoding="utf-8")


def overlap(a_start, a_end, b_start, b_end) -> bool:
    # [start, end) overlaps if start < other_end and other_start < end
    return a_start < b_end and b_start < a_end


def is_available(p, start: int, end: int) -> bool:
    return not any(overlap(vs, ve, start, end) for (vs, ve) in p["vacation"])


def greedy_allocate(demands, pros):
    # Alocação gulosa por profissional:
    # - percorre profissionais na ordem de pros
    # - para cada profissional, tenta alocar demandas remanescentes ordenadas por:
    #   1) início mais cedo (start asc)
    #   2) término mais tarde (end desc)
    # - respeita: pediatria, folga e não sobreposição
    remaining = set(range(len(demands)))
    assigned_by_demand = {di: None for di in range(len(demands))}
    assigned_demands_by_pro = {p["id"]: [] for p in pros}

    def demand_sort_key(di: int):
        d = demands[di]
        return (d["start"], -d["end"], di)

    for p in pros:
        pid = p["id"]
        scheduled = []
        for di in sorted(remaining, key=demand_sort_key):
            d = demands[di]

            if d["is_pediatric"] and not p["can_peds"]:
                continue
            if not is_available(p, d["start"], d["end"]):
                continue
            if any(overlap(d["start"], d["end"], sd["start"], sd["end"]) for sd in scheduled):
                continue

            assigned_by_demand[di] = pid
            assigned_demands_by_pro[pid].append(d)
            scheduled.append(d)
            remaining.remove(di)

    return assigned_by_demand, assigned_demands_by_pro


def diagnose_infeasibility(demands, pros) -> None:
    print()
    print("Diagnóstico rápido (regras hard):")

    print("- Elegibilidade por demanda:")
    any_empty = False
    for d in demands:
        eligible = []
        for p in pros:
            if d["is_pediatric"] and not p["can_peds"]:
                continue
            if not is_available(p, d["start"], d["end"]):
                continue
            eligible.append(p["id"])

        ped_tag = " ped" if d["is_pediatric"] else ""
        if not eligible:
            any_empty = True
            print(
                f"  - {d['id']} {d['start']}-{d['end']}{ped_tag}: "
                f"SEM profissionais elegíveis (pediatria/férias)"
            )
        else:
            print(
                f"  - {d['id']} {d['start']}-{d['end']}{ped_tag}: "
                f"{', '.join(eligible)}"
            )

    # Checagem por janelas (segmentos) para identificar gargalos por simultaneidade
    points = {0, 24}
    for d in demands:
        points.add(d["start"])
        points.add(d["end"])
    for p in pros:
        for (vs, ve) in p["vacation"]:
            points.add(vs)
            points.add(ve)
    points = sorted(points)

    print("- Gargalos por simultaneidade:")
    any_bottleneck = False
    for i in range(len(points) - 1):
        s, e = points[i], points[i+1]
        if s == e:
            continue

        active = [d for d in demands if overlap(d["start"], d["end"], s, e)]
        if not active:
            continue

        available = [p for p in pros if is_available(p, s, e)]
        if len(active) > len(available):
            any_bottleneck = True
            active_ids = "".join(d["id"] for d in active)
            print(
                f"  - {s}-{e}: "
                f"{len(active)} demandas ativas ({active_ids}) > {len(available)} profissionais disponíveis"
            )

        active_ped = [d for d in active if d["is_pediatric"]]
        if active_ped:
            available_ped = [p for p in available if p["can_peds"]]
            if len(active_ped) > len(available_ped):
                any_bottleneck = True
                active_ped_ids = "".join(d["id"] for d in active_ped)
                print(
                    f"  - {s}-{e}: "
                    f"{len(active_ped)} demandas ped ({active_ped_ids}) > {len(available_ped)} profissionais com ped"
                )

    if not any_empty and not any_bottleneck:
        print("  - Não identifiquei um gargalo óbvio; pode ser um conflito mais sutil entre sobreposições/skills.")


def main():
    # -------------------------
    # 1) DADOS (mini mundo)
    # -------------------------
    # Demandas (cirurgias) com intervalo, e um atributo simples "is_pediatric"
    demands = [
        {"id": "A", "start":  8, "end": 10, "is_pediatric": False},
        {"id": "A", "start": 12, "end": 18, "is_pediatric": False},
        {"id": "B", "start":  8, "end": 11, "is_pediatric": False},
        {"id": "C", "start": 11, "end": 13, "is_pediatric": False},
        {"id": "D", "start":  6, "end":  9, "is_pediatric": False},
        {"id": "E", "start": 13, "end": 16, "is_pediatric": False},
        {"id": "F", "start":  8, "end": 10, "is_pediatric": False},
        {"id": "F", "start": 17, "end": 18, "is_pediatric": True },
        {"id": "G", "start":  5, "end":  9, "is_pediatric": False},
    ]

    # Anestesistas com skills e preferências simples
    pros = [
        {"id": "Joaquim", "can_peds": False, "vacation": []},
        {"id": "Nicolas", "can_peds": False, "vacation": []},
        {"id": "Carlota", "can_peds": False, "vacation": [(0, 24)]},
        {"id": "Mariana", "can_peds": True , "vacation": [(11, 15)]},
    ]

    # -------------------------
    # 2) ALOCAÇÃO
    # -------------------------
    # Modo pedido: alocar por profissional, usando a ordem das demandas:
    # - início mais cedo
    # - depois término mais tarde
    ALLOCATION_MODE = "greedy"  # "greedy" | "cp-sat"

    # Se True, permite demandas sem profissional (entra como "Descoberto")
    ALLOW_UNASSIGNED = True
    UNASSIGNED_PENALTY = 1000

    if ALLOCATION_MODE == "greedy":
        assigned_by_demand, assigned_demands_by_pro = greedy_allocate(demands, pros)
        solution_label = "GULOSA"

        unassigned_count = sum(1 for di in range(len(demands)) if assigned_by_demand.get(di) is None)
        ped_assigned_count = sum(
            1
            for di, d in enumerate(demands)
            if d["is_pediatric"] and assigned_by_demand.get(di) is not None
        )
        total_cost = UNASSIGNED_PENALTY * unassigned_count + ped_assigned_count
    else:
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
            for j in range(i+1, len(demands)):
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
                base = 0
                if d["is_pediatric"]:
                    base += 1
                costs.append(base * x[(pid, di)])

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
    print("Solução:", solution_label)
    print("Custo total:", total_cost)
    print()

    # Para cada demanda, mostra quem foi alocado (na ordem da lista demands)
    for di, d in enumerate(demands):
        assigned = assigned_by_demand.get(di)
        print(f"{d['id']} {d['start']:02d} às {d['end']:02d} "
              f"peds={d['is_pediatric']} -> {(assigned if assigned else 'SEM')}")

    first_hour = 0
    last_hour_exclusive = 24

    print()
    print("Demandas")
    for d in demands:
        ped_tag = " 👶" if d["is_pediatric"] else ""
        print(f"{d['id']} - {d['start']:02d} às {d['end']:02d}{ped_tag}")
    print()
    print("Profissionais")
    for p in pros:
        tags = []
        if p["can_peds"]:
            tags.append("👶")
        for (vs, ve) in p["vacation"]:
            tags.append(f"folga {vs}-{ve}")
        print(f"{p['id']} " + (" ".join(tags)))
    print()
    print("Alocados entre 0 a 23 horas")
    print("HORÁRIO: 012345678901234567890123")
    for p in pros:
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
                chars.append(dem["id"] if dem else "_")
        print(f"{pid}: {''.join(chars)}")

    uncovered_demands = [d for di, d in enumerate(demands) if assigned_by_demand.get(di) is None]
    if uncovered_demands:
        print()
        print("Descobertas")
        for d in uncovered_demands:
            ped_tag = " 👶" if d["is_pediatric"] else ""
            print(f"{d['id']} - {d['start']:02d} às {d['end']:02d}{ped_tag}")


if __name__ == "__main__":
    main()
