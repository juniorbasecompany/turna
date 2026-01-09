# pip install ortools
from datetime import datetime, timedelta
import sys

from ortools.sat.python import cp_model

sys.stdout.reconfigure(encoding="utf-8")

# -------------------------
# DADOS (editáveis)
# -------------------------
# A ideia aqui é manter o "mini mundo" como constantes no topo do arquivo,
# para que seja fácil de editar/entender sem depender de geração aleatória.
DEMANDS_BY_DAY = {
    1: [
        {"id": "A", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 10, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 7, "is_pediatric": False},
        {"id": "G", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "C", "start": 7, "end": 12, "is_pediatric": True},
        {"id": "H", "start": 7, "end": 10, "is_pediatric": False},
        {"id": "D", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "E", "start": 8, "end": 12, "is_pediatric": False},
        {"id": "C", "start": 9, "end": 10, "is_pediatric": False},
        {"id": "E", "start": 9, "end": 13, "is_pediatric": False},
        {"id": "F", "start": 10, "end": 14, "is_pediatric": False},
        {"id": "G", "start": 11, "end": 15, "is_pediatric": False},
        {"id": "H", "start": 12, "end": 16, "is_pediatric": False},
        {"id": "A", "start": 13, "end": 17, "is_pediatric": True},
        {"id": "B", "start": 14, "end": 18, "is_pediatric": False},
        {"id": "C", "start": 15, "end": 19, "is_pediatric": False},
        {"id": "D", "start": 16, "end": 20, "is_pediatric": False},
        {"id": "D", "start": 17, "end": 19, "is_pediatric": False},
        {"id": "E", "start": 18, "end": 22, "is_pediatric": False},
        {"id": "G", "start": 18, "end": 21, "is_pediatric": False},
        {"id": "H", "start": 20, "end": 22, "is_pediatric": False},
        {"id": "E", "start": 21, "end": 22, "is_pediatric": False},
        {"id": "F", "start": 19, "end": 22, "is_pediatric": True},
        {"id": "A", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "B", "start": 7, "end": 11, "is_pediatric": False},
        {"id": "C", "start": 9, "end": 12, "is_pediatric": False},
        {"id": "D", "start": 10, "end": 14, "is_pediatric": False},
        {"id": "E", "start": 12, "end": 15, "is_pediatric": False},
        {"id": "F", "start": 13, "end": 16, "is_pediatric": False},
        {"id": "G", "start": 15, "end": 18, "is_pediatric": False},
        {"id": "H", "start": 17, "end": 20, "is_pediatric": False},
        {"id": "A", "start": 19, "end": 22, "is_pediatric": False},
    ],
    2: [
        {"id": "A", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 11, "is_pediatric": False},
        {"id": "A", "start": 6, "end": 7, "is_pediatric": False},
        {"id": "D", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "E", "start": 7, "end": 9, "is_pediatric": False},
        {"id": "C", "start": 7, "end": 10, "is_pediatric": True},
        {"id": "D", "start": 8, "end": 12, "is_pediatric": False},
        {"id": "G", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "H", "start": 9, "end": 12, "is_pediatric": False},
        {"id": "E", "start": 9, "end": 13, "is_pediatric": False},
        {"id": "F", "start": 10, "end": 14, "is_pediatric": True},
        {"id": "G", "start": 11, "end": 15, "is_pediatric": False},
        {"id": "H", "start": 12, "end": 16, "is_pediatric": False},
        {"id": "A", "start": 13, "end": 17, "is_pediatric": False},
        {"id": "B", "start": 14, "end": 18, "is_pediatric": True},
        {"id": "C", "start": 15, "end": 19, "is_pediatric": False},
        {"id": "D", "start": 16, "end": 20, "is_pediatric": False},
        {"id": "G", "start": 17, "end": 19, "is_pediatric": False},
        {"id": "E", "start": 18, "end": 22, "is_pediatric": False},
        {"id": "H", "start": 18, "end": 21, "is_pediatric": False},
        {"id": "A", "start": 20, "end": 22, "is_pediatric": False},
        {"id": "D", "start": 19, "end": 22, "is_pediatric": False},
        {"id": "A", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "C", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "D", "start": 9, "end": 13, "is_pediatric": False},
        {"id": "E", "start": 11, "end": 14, "is_pediatric": False},
        {"id": "F", "start": 12, "end": 16, "is_pediatric": False},
        {"id": "G", "start": 14, "end": 17, "is_pediatric": False},
        {"id": "H", "start": 16, "end": 18, "is_pediatric": False},
        {"id": "A", "start": 20, "end": 22, "is_pediatric": False},
    ],
    3: [
        {"id": "A", "start": 6, "end": 10, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "E", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "C", "start": 7, "end": 11, "is_pediatric": True},
        {"id": "D", "start": 8, "end": 12, "is_pediatric": False},
        {"id": "H", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "F", "start": 7, "end": 9, "is_pediatric": False},
        {"id": "E", "start": 9, "end": 14, "is_pediatric": False},
        {"id": "F", "start": 10, "end": 13, "is_pediatric": False},
        {"id": "G", "start": 11, "end": 15, "is_pediatric": True},
        {"id": "H", "start": 12, "end": 16, "is_pediatric": False},
        {"id": "A", "start": 13, "end": 17, "is_pediatric": False},
        {"id": "B", "start": 14, "end": 18, "is_pediatric": False},
        {"id": "C", "start": 15, "end": 19, "is_pediatric": False},
        {"id": "D", "start": 16, "end": 20, "is_pediatric": True},
        {"id": "A", "start": 17, "end": 19, "is_pediatric": False},
        {"id": "E", "start": 18, "end": 22, "is_pediatric": False},
        {"id": "F", "start": 18, "end": 21, "is_pediatric": False},
        {"id": "G", "start": 20, "end": 22, "is_pediatric": False},
        {"id": "H", "start": 19, "end": 22, "is_pediatric": False},
        {"id": "A", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "B", "start": 7, "end": 9, "is_pediatric": False},
        {"id": "C", "start": 8, "end": 12, "is_pediatric": False},
        {"id": "D", "start": 9, "end": 11, "is_pediatric": False},
        {"id": "E", "start": 10, "end": 13, "is_pediatric": False},
        {"id": "F", "start": 12, "end": 15, "is_pediatric": False},
        {"id": "G", "start": 14, "end": 18, "is_pediatric": False},
        {"id": "H", "start": 17, "end": 19, "is_pediatric": False},
        {"id": "A", "start": 19, "end": 22, "is_pediatric": False},
    ],
    4: [
        {"id": "A", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 10, "is_pediatric": False},
        {"id": "E", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "A", "start": 6, "end": 7, "is_pediatric": False},
        {"id": "C", "start": 7, "end": 12, "is_pediatric": True},
        {"id": "B", "start": 7, "end": 9, "is_pediatric": False},
        {"id": "D", "start": 8, "end": 13, "is_pediatric": False},
        {"id": "G", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "E", "start": 9, "end": 11, "is_pediatric": False},
        {"id": "F", "start": 10, "end": 14, "is_pediatric": False},
        {"id": "G", "start": 11, "end": 15, "is_pediatric": False},
        {"id": "H", "start": 12, "end": 16, "is_pediatric": True},
        {"id": "A", "start": 13, "end": 17, "is_pediatric": False},
        {"id": "B", "start": 14, "end": 18, "is_pediatric": False},
        {"id": "C", "start": 15, "end": 19, "is_pediatric": False},
        {"id": "D", "start": 16, "end": 20, "is_pediatric": True},
        {"id": "C", "start": 17, "end": 19, "is_pediatric": False},
        {"id": "E", "start": 18, "end": 22, "is_pediatric": False},
        {"id": "F", "start": 18, "end": 21, "is_pediatric": False},
        {"id": "G", "start": 20, "end": 22, "is_pediatric": False},
        {"id": "D", "start": 19, "end": 22, "is_pediatric": False},
        {"id": "A", "start": 6, "end": 10, "is_pediatric": False},
        {"id": "B", "start": 7, "end": 9, "is_pediatric": False},
        {"id": "C", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "D", "start": 9, "end": 12, "is_pediatric": False},
        {"id": "E", "start": 10, "end": 12, "is_pediatric": False},
        {"id": "F", "start": 11, "end": 15, "is_pediatric": False},
        {"id": "G", "start": 13, "end": 16, "is_pediatric": False},
        {"id": "H", "start": 16, "end": 20, "is_pediatric": False},
        {"id": "A", "start": 19, "end": 22, "is_pediatric": False},
    ],
    5: [
        {"id": "A", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 10, "is_pediatric": True},
        {"id": "D", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "E", "start": 6, "end": 7, "is_pediatric": False},
        {"id": "C", "start": 7, "end": 11, "is_pediatric": False},
        {"id": "D", "start": 8, "end": 12, "is_pediatric": False},
        {"id": "H", "start": 8, "end": 11, "is_pediatric": False},
        {"id": "F", "start": 7, "end": 9, "is_pediatric": False},
        {"id": "E", "start": 9, "end": 13, "is_pediatric": False},
        {"id": "F", "start": 10, "end": 14, "is_pediatric": False},
        {"id": "G", "start": 11, "end": 15, "is_pediatric": True},
        {"id": "H", "start": 12, "end": 16, "is_pediatric": False},
        {"id": "A", "start": 13, "end": 17, "is_pediatric": False},
        {"id": "B", "start": 14, "end": 18, "is_pediatric": False},
        {"id": "C", "start": 15, "end": 19, "is_pediatric": False},
        {"id": "D", "start": 16, "end": 20, "is_pediatric": True},
        {"id": "A", "start": 17, "end": 19, "is_pediatric": False},
        {"id": "E", "start": 18, "end": 22, "is_pediatric": False},
        {"id": "F", "start": 18, "end": 21, "is_pediatric": False},
        {"id": "G", "start": 20, "end": 22, "is_pediatric": False},
        {"id": "B", "start": 19, "end": 22, "is_pediatric": False},
        {"id": "A", "start": 6, "end": 8, "is_pediatric": False},
        {"id": "B", "start": 6, "end": 9, "is_pediatric": False},
        {"id": "C", "start": 8, "end": 10, "is_pediatric": False},
        {"id": "D", "start": 9, "end": 12, "is_pediatric": False},
        {"id": "E", "start": 10, "end": 14, "is_pediatric": False},
        {"id": "F", "start": 12, "end": 15, "is_pediatric": False},
        {"id": "G", "start": 13, "end": 17, "is_pediatric": False},
        {"id": "H", "start": 16, "end": 18, "is_pediatric": False},
        {"id": "A", "start": 19, "end": 22, "is_pediatric": False},
    ],
}

DEMANDS = [
    {"day": day, **d}
    for day, day_demands in DEMANDS_BY_DAY.items()
    for d in day_demands
]

PROS = [
    {"id": "Joaquim", "sequence": 1, "can_peds": False, "vacation": [(13, 17)]},
    {"id": "Nicolas", "sequence": 2, "can_peds": False, "vacation": [(7, 12)]},
    {"id": "Carlota", "sequence": 3, "can_peds": False, "vacation": []},
    {"id": "Mariana", "sequence": 4, "can_peds": True, "vacation": []},
    {"id": "Fabiano", "sequence": 5, "can_peds": False, "vacation": []},
    {"id": "Julieta", "sequence": 6, "can_peds": True, "vacation": []},
    {"id": "Gustavo", "sequence": 7, "can_peds": False, "vacation": []},
    {"id": "Ricardo", "sequence": 8, "can_peds": False, "vacation": [(0, 24)]},
    {"id": "Augusto", "sequence": 9, "can_peds": False, "vacation": []},
    {"id": "Camilla", "sequence": 10, "can_peds": False, "vacation": []},
]

DAYS = max(DEMANDS_BY_DAY.keys(), default=0)

# -------------------------
# OUTPUT (cores)
# -------------------------
# Em terminais que suportam ANSI, isso deixa o ID da demanda em amarelo quando for pediátrica.
# Se o seu terminal não suportar, basta colocar False.
USE_ANSI_COLORS = True
ANSI_YELLOW = "\x1b[33m"
ANSI_RESET = "\x1b[0m"


def yellow(txt: str) -> str:
    if not USE_ANSI_COLORS:
        return txt
    return f"{ANSI_YELLOW}{txt}{ANSI_RESET}"


def fmt_time_range(start: int, end: int, is_pediatric: bool) -> str:
    txt = f"{start:02d} às {end:02d}"
    return yellow(txt) if is_pediatric else txt


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

        def is_feasible_ped(di: int) -> bool:
            d = demands[di]
            if not d["is_pediatric"]:
                return False
            if not is_available(p, d["start"], d["end"]):
                return False
            if any(overlap(d["start"], d["end"], sd["start"], sd["end"]) for sd in scheduled):
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
    demands = list(DEMANDS)
    pros = list(PROS)

    # -------------------------
    # 2) ALOCAÇÃO (1 dia)
    # -------------------------
    ALLOCATION_MODE = "greedy"  # "greedy" | "cp-sat"

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
        for day in range(1, DAYS + 1):
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

        for day in range(DAYS):
            day_num = day + 1
            demands_day = [d for d in demands if d["day"] == day_num]

            start_idx = (base_shift + day) % n_pros
            pros_for_day = pros_by_sequence[start_idx:] + pros_by_sequence[:start_idx]

            assigned_by_demand, assigned_demands_by_pro, used_count = greedy_allocate(demands_day, pros_for_day)
            solution_label = "GULOSA"

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

            print()
            print("=" * 40)
            print(f"Dia {day + 1}")

            # -------------------------
            # 6) EXIBIR RESULTADO
            # -------------------------

            first_hour = 0
            last_hour_exclusive = 24

            print()
            print("HORÁRIO...: 012345678901234567890123")
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
        print(f"Custo total (todos os {DAYS} dias): {total_cost_all_days}")
        return
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

        solution_label = "ÓTIMA" if status == cp_model.OPTIMAL else "FACTÍVEL"
        total_cost = solver.ObjectiveValue()

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


if __name__ == "__main__":
    main()
