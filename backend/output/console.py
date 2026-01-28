"""
Funções de output/format para console.
"""

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


def print_demands_overview(demand_list: list[dict], days: int) -> None:
    print("Demandas")
    for day in range(1, days + 1):
        print(f"Dia {day}")
        for d in demand_list:
            if d["day"] != day:
                continue
            did_txt = yellow(d["id"]) if d["is_pediatric"] else d["id"]
            time_txt = fmt_time_range(d["start"], d["end"], d["is_pediatric"])
            ped_tag = " 👶" if d["is_pediatric"] else ""
            print(f"{did_txt} - {time_txt}{ped_tag}")


def print_member_list_overview(pros_by_sequence: list[dict]) -> None:
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


def print_day_result(
    day_number: int,
    pros_for_day: list[dict],
    assigned_demands_by_pro: dict[str, list[dict]],
    demands_day: list[dict],
    assigned_pids: list[str | None],
    overlap_fn,
) -> None:
    print()
    print("=" * 40)
    print(f"Dia {day_number}")

    print()
    print("HORÁRIO...: 012345678901234567890123")
    first_hour = 0
    last_hour_exclusive = 24
    for p in pros_for_day:
        pid = p["id"]
        chars = []
        for hour in range(first_hour, last_hour_exclusive):
            # Cada coluna representa uma hora [h, h+1) no modelo [start, end).
            hs = hour
            he = hour + 1
            on_vacation = any(overlap_fn(vs, ve, hs, he) for (vs, ve) in p["vacation"])
            if on_vacation:
                chars.append("z")
            else:
                dem = next(
                    (d for d in assigned_demands_by_pro.get(pid, []) if overlap_fn(d["start"], d["end"], hs, he)),
                    None,
                )
                if dem and dem["is_pediatric"] and USE_ANSI_COLORS:
                    chars.append(f"{ANSI_YELLOW}{dem['id']}{ANSI_RESET}")
                else:
                    chars.append(dem["id"] if dem else "_")
        print(f"{p['sequence']:02d} {pid}: {''.join(chars)}")

    print()
    for d, assigned in zip(demands_day, assigned_pids, strict=True):
        assigned_txt = assigned if assigned else "_______"
        did_txt = yellow(d["id"]) if d["is_pediatric"] else d["id"]
        assigned_out = yellow(assigned_txt) if (d["is_pediatric"] and assigned) else assigned_txt
        time_txt = fmt_time_range(d["start"], d["end"], d["is_pediatric"])
        print(f"{did_txt} {time_txt} {assigned_out}")


def print_total_cost(days: int, total_cost: float | int) -> None:
    print()
    print("=" * 40)
    print(f"Custo total (todos os {days} dias): {total_cost}")

