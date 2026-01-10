"""
Regras core: overlap/disponibilidade e alocação gulosa.
"""


def overlap(a_start, a_end, b_start, b_end) -> bool:
    # [start, end) overlaps if start < other_end and other_start < end
    return a_start < b_end and b_start < a_end


def is_available(p, start: int, end: int) -> bool:
    return not any(overlap(vs, ve, start, end) for (vs, ve) in p["vacation"])


def greedy_allocate(demands, pros):
    # Alocação gulosa por profissional:
    # - percorre profissionais na ordem de pros
    # - para cada profissional, aloca em loop alternando:
    #   1) demanda com início mais cedo
    #   2) demanda com término mais tarde
    #   até não conseguir alocar mais nada para ele
    # - respeita: pediatria, folga e não sobreposição
    remaining = set(range(len(demands)))
    assigned_by_demand = {di: None for di in range(len(demands))}
    assigned_demands_by_pro = {p["id"]: [] for p in pros}
    processed_pros = 0

    for p in pros:
        if not remaining:
            break
        pid = p["id"]
        scheduled = []
        processed_pros += 1

        def is_feasible_ped(di: int) -> bool:
            d = demands[di]
            if not d["is_pediatric"]:
                return False
            if not is_available(p, d["start"], d["end"]):
                return False
            if any(overlap(d["start"], d["end"], sd["start"], sd["end"]) for sd in scheduled):
                return False
            return True

        def is_feasible(di: int) -> bool:
            d = demands[di]
            if d["is_pediatric"] and not p["can_peds"]:
                return False
            if not is_available(p, d["start"], d["end"]):
                return False
            if any(overlap(d["start"], d["end"], sd["start"], sd["end"]) for sd in scheduled):
                return False

            # Regra de "reservar pediatras":
            # se este profissional faz pediatria e existe alguma demanda pediátrica
            # ainda remanescente e factível, então evitamos consumi-lo com demanda
            # não-pediátrica.
            if p["can_peds"] and (not d["is_pediatric"]):
                has_feasible_ped_remaining = any(
                    demands[odi]["is_pediatric"] and is_feasible_ped(odi)
                    for odi in remaining
                )
                if has_feasible_ped_remaining:
                    return False

            return True

        def pick_earliest_start() -> int | None:
            candidates = [di for di in remaining if is_feasible(di)]
            if not candidates:
                return None
            return min(
                candidates,
                key=lambda di: (demands[di]["start"], -demands[di]["end"], di),
            )

        def pick_latest_end() -> int | None:
            candidates = [di for di in remaining if is_feasible(di)]
            if not candidates:
                return None
            return max(
                candidates,
                key=lambda di: (demands[di]["end"], -demands[di]["start"], -di),
            )

        pick_earliest = True
        while True:
            chosen = pick_earliest_start() if pick_earliest else pick_latest_end()
            if chosen is None:
                # tenta uma vez com o outro critério; se falhar também, acabou para este profissional
                chosen = pick_latest_end() if pick_earliest else pick_earliest_start()
                if chosen is None:
                    break
                pick_earliest = not pick_earliest

            d = demands[chosen]
            assigned_by_demand[chosen] = pid
            assigned_demands_by_pro[pid].append(d)
            scheduled.append(d)
            remaining.remove(chosen)
            pick_earliest = not pick_earliest

    return assigned_by_demand, assigned_demands_by_pro, processed_pros

