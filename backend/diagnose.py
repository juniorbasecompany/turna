"""
Diagnóstico de inviabilidade (regras hard).
"""

from strategy.core import overlap, is_available


def diagnose_infeasibility(demand_list, pros) -> None:
    print()
    print("Diagnóstico rápido (regras hard):")

    print("- Elegibilidade por demanda:")
    any_empty = False
    for d in demand_list:
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
    for d in demand_list:
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
        s, e = points[i], points[i + 1]
        if s == e:
            continue

        active = [d for d in demand_list if overlap(d["start"], d["end"], s, e)]
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

