"""
Implementação da alocação ambiciosa.

Tudo que for específico de greedy deve ficar nesta pasta.
"""

import logging

from strategy.core import overlap, is_available

logger = logging.getLogger(__name__)


def greedy_allocate(demands, pros):
    # Alocação ambiciosa por profissional:
    # - percorre profissionais na ordem de pros
    # - para cada profissional, aloca em loop alternando:
    #   1) demanda com início mais cedo
    #   2) demanda com término mais tarde
    #   até não conseguir alocar mais nada para ele
    # - respeita: pediatria, folga e não sobreposição
    import time
    
    remaining = set(range(len(demands)))
    assigned_by_demand = {di: None for di in range(len(demands))}
    assigned_demands_by_pro = {p["id"]: [] for p in pros}
    processed_pros = 0
    
    logger.debug(f"[GREEDY_ALLOCATE] Iniciando: {len(demands)} demandas, {len(pros)} profissionais")
    
    max_iterations_per_pro = len(demands) * 2  # Limite de segurança para detectar loops
    total_iterations = 0

    for pro_idx, p in enumerate(pros):
        if not remaining:
            logger.debug(f"[GREEDY_ALLOCATE] Todas as demandas foram alocadas após processar {processed_pros} profissionais")
            break
        pid = p["id"]
        scheduled = []
        processed_pros += 1
        pro_start_time = time.time()
        iterations_for_pro = 0

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
            iterations_for_pro += 1
            total_iterations += 1
            
            # Detecção de loop: se exceder limite de iterações, logar e parar
            if iterations_for_pro > max_iterations_per_pro:
                logger.error(f"[GREEDY_ALLOCATE] POSSÍVEL LOOP DETECTADO! Profissional {pid} ({pro_idx + 1}/{len(pros)}) excedeu {max_iterations_per_pro} iterações. Remaining: {len(remaining)}, Scheduled: {len(scheduled)}")
                break
            
            if total_iterations > len(demands) * len(pros) * 10:
                logger.error(f"[GREEDY_ALLOCATE] POSSÍVEL LOOP DETECTADO! Total de iterações ({total_iterations}) excedeu limite seguro ({len(demands) * len(pros) * 10})")
                break
            
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
        
        pro_duration = time.time() - pro_start_time
        if iterations_for_pro > 100:
            logger.warning(f"[GREEDY_ALLOCATE] Profissional {pid} ({pro_idx + 1}/{len(pros)}) processado em {pro_duration:.3f}s com {iterations_for_pro} iterações ({len(scheduled)} demandas alocadas)")
        else:
            logger.debug(f"[GREEDY_ALLOCATE] Profissional {pid} ({pro_idx + 1}/{len(pros)}) processado em {pro_duration:.3f}s: {len(scheduled)} demandas alocadas")

    logger.debug(f"[GREEDY_ALLOCATE] Concluído: {processed_pros} profissionais processados, {len(remaining)} demandas não alocadas, total de iterações: {total_iterations}")
    return assigned_by_demand, assigned_demands_by_pro, processed_pros

