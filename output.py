"""
Funções de output/format.
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

