"""
Regras core: overlap/disponibilidade e alocação ambiciosa.
"""


def overlap(a_start, a_end, b_start, b_end) -> bool:
    # Intervalos meio-abertos [start, end) sobrepõem se:
    #   a_start < b_end and b_start < a_end
    return a_start < b_end and b_start < a_end


def is_available(p, start: int, end: int) -> bool:
    return not any(overlap(vs, ve, start, end) for (vs, ve) in p["vacation"])
