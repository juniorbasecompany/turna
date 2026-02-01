"""
Schema e definições de dados para extração de demandas.

Este módulo centraliza as definições de formato, validações e constantes
relacionadas ao schema de dados, permitindo modificações sem quebrar o sistema.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------
# Expressões regulares
# -----------------------------
ISO_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
HM_RE = re.compile(r"^\d{2}:\d{2}$")
DMHM_RE = re.compile(r"^\d{2}/\d{2}\s+\d{2}:\d{2}$")  # ex: 11/03 09:00
ID_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,6}\b")
ISO_DT_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

# -----------------------------
# Constantes
# -----------------------------
DEFAULT_TZ_OFFSET = "-03:00"

# Campos de ID aceitos (ordem de preferência)
ID_FIELDS = ("id", "ID", "case_id", "caseId")

# Campos alternativos para skills
SKILLS_ALT_FIELDS = ("skills", "habilidades")

# -----------------------------
# Funções de parsing e normalização
# -----------------------------

def period_start_ymd(meta: dict) -> Optional[Tuple[int, int, int]]:
    """
    Extrai a primeira data do período em meta.period (ex: "12/01/2026 a 18/01/2026").
    Retorna (yyyy, mm, dd).
    """
    if not isinstance(meta, dict):
        return None
    period = meta.get("period")
    if not isinstance(period, str):
        return None
    m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", period)
    if not m:
        return None
    dd, mm, yyyy = m.group(1).split("/")
    try:
        return int(yyyy), int(mm), int(dd)
    except Exception:
        return None

def to_iso_datetime(yyyy: int, mm: int, dd: int, hh: int, mi: int, tz_offset: str = DEFAULT_TZ_OFFSET) -> str:
    """Converte componentes de data/hora para ISO datetime com timezone."""
    return f"{yyyy:04d}-{mm:02d}-{dd:02d}T{hh:02d}:{mi:02d}:00{tz_offset}"

def parse_time_hhmm(s: str) -> Optional[Tuple[int, int]]:
    """Parse formato HH:MM. Retorna (hh, mm) ou None."""
    if not s or not HM_RE.match(s):
        return None
    hh, mm = s.split(":")
    try:
        return int(hh), int(mm)
    except Exception:
        return None

def parse_dmhm(s: str) -> Optional[Tuple[int, int, int, int]]:
    """Parse formato DD/MM HH:MM. Retorna (dd, mm, hh, mi) ou None."""
    if not s or not DMHM_RE.match(s):
        return None
    dm, hm = s.split()
    dd, mm = dm.split("/")
    hh, mi = hm.split(":")
    try:
        return int(dd), int(mm), int(hh), int(mi)
    except Exception:
        return None

def coerce_time_to_iso(raw: Optional[str], meta: dict) -> Optional[str]:
    """
    Converte:
    - "DD/MM HH:MM" -> "YYYY-MM-DDTHH:MM:00-03:00" (usa o ano de meta.period)
    - "HH:MM"       -> usa a data inicial de meta.period
    - ISO já pronto -> mantém
    """
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if ISO_DT_TZ_RE.match(s):
        return s

    ymd0 = period_start_ymd(meta)
    if not ymd0:
        return None
    yyyy0, mm0, dd0 = ymd0

    dmhm = parse_dmhm(s)
    if dmhm:
        dd, mm, hh, mi = dmhm
        return to_iso_datetime(yyyy0, mm, dd, hh, mi)

    hm = parse_time_hhmm(s)
    if hm:
        hh, mi = hm
        return to_iso_datetime(yyyy0, mm0, dd0, hh, mi)

    return None

def canon_priority(x: Optional[str]) -> Optional[str]:
    """Normaliza string de prioridade para formato canônico."""
    if not x:
        return None
    s = str(x).strip()
    if not s:
        return None
    low = s.lower()
    if "urg" in low:
        return "Urgente"
    if "emerg" in low:
        return "Emergência"
    return None

def extract_priority(notes: Optional[str]) -> Optional[str]:
    """Extrai prioridade do campo notes."""
    if not notes:
        return None
    m = re.search(r"(?i)\bprioridade\s*:\s*(urgente|emerg[êe]ncia)\b", notes)
    if not m:
        return None
    return canon_priority(m.group(1))

def canon_skill_token(tok: str) -> str:
    """Normaliza token de skill para formato canônico."""
    t = tok.strip()
    if not t:
        return ""
    # normalizações comuns (sem inventar skills novas)
    if t.lower() == "obstetrica":
        return "Obstétrica"
    if t.lower() == "cardiaca":
        return "Cardíaca"
    return t

def parse_skills(x: Any) -> List[str]:
    """
    skills: lista de strings. Aceita entrada como lista ou string separada por vírgula.
    """
    if x is None:
        return []
    if isinstance(x, list):
        out: List[str] = []
        for it in x:
            s = canon_skill_token(str(it))
            if s:
                out.append(s)
        return out
    if isinstance(x, str):
        # corta tudo após "Prioridade:" se veio junto
        s = re.split(r"(?i)\bprioridade\s*:", x, maxsplit=1)[0]
        parts = re.split(r"[;,|]", s)
        out = []
        for p in parts:
            t = canon_skill_token(p)
            if t:
                out.append(t)
        return out
    return []

def extract_id(d: dict) -> Optional[str]:
    """Extrai ID da demanda a partir dos campos explícitos (id, ID, case_id, caseId)."""
    for k in ID_FIELDS:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def normalize_str(x: Any) -> Optional[str]:
    """Normaliza valor para string ou None."""
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None

def as_list(x: Any) -> List[Any]:
    """Converte valor para lista (retorna [] se não for lista)."""
    return x if isinstance(x, list) else []

def validate_and_normalize_result(obj: dict) -> dict:
    """
    Garante que o JSON final tenha sempre as chaves e tipos esperados.
    Não tenta "adivinhar" campos complexos; só normaliza e protege.
    """
    out: Dict[str, Any] = {}

    # meta
    meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
    # Remove timezone (não necessário no output)
    if "timezone" in meta:
        del meta["timezone"]
    out["meta"] = meta

    # demand list
    demand_list = []
    for d in as_list(obj.get("demands")):
        if not isinstance(d, dict):
            continue

        notes = normalize_str(d.get("notes"))
        priority = extract_priority(notes)

        # skills: preferir campo explícito; fallback heurístico para casos onde IA colocou em "complexity"
        skills = parse_skills(d.get("skills"))
        if not skills:
            skills = parse_skills(d.get("habilidades"))
        if not skills:
            # heuristic: se "complexity" veio como lista de habilidades (ex: "Geral, Obstétrica")
            cx = normalize_str(d.get("complexity"))
            if cx and ("," in cx or "|" in cx or ";" in cx):
                skills = parse_skills(cx)

        extracted_id = extract_id(d)
        room = normalize_str(d.get("room"))
        if extracted_id and room:
            room = f"{extracted_id} {room}"
        elif extracted_id and not room:
            room = extracted_id

        dd = {
            "room": room,
            "start_time": normalize_str(d.get("start_time")),
            "end_time": normalize_str(d.get("end_time")),
            "procedure": normalize_str(d.get("procedure")),
            "anesthesia_type": normalize_str(d.get("anesthesia_type")),
            "complexity": normalize_str(d.get("complexity")),
            "skills": skills,
            "priority": priority,
            "members": as_list(d.get("members")),
            "notes": notes,
        }

        # Regras mínimas: precisa ter procedure + start/end (ou início/fim "dd/mm hh:mm")
        if not dd["procedure"]:
            continue

        # Normaliza start_time/end_time para ISO datetime com timezone
        iso_start = coerce_time_to_iso(dd["start_time"], out.get("meta", {}))
        iso_end = coerce_time_to_iso(dd["end_time"], out.get("meta", {}))
        if not (iso_start and iso_end):
            # sem data suficiente para ISO (ex: meta.period ausente) -> não aceita como demanda pronta
            continue
        dd["start_time"] = iso_start
        dd["end_time"] = iso_end

        demand_list.append(dd)

    out["demands"] = demand_list

    # Normaliza date_reference: prioriza cabeçalho (meta.period), fallback para primeira demanda
    date_ref: Optional[str] = None

    # 1) Tenta extrair do cabeçalho (meta.period)
    ymd = period_start_ymd(out.get("meta", {}))
    if ymd:
        yyyy, mm, dd = ymd
        date_ref = f"{yyyy:04d}-{mm:02d}-{dd:02d}"

    # 2) Fallback: primeira demanda válida
    if not date_ref and demand_list:
        for d in demand_list:
            st = d.get("start_time")
            if isinstance(st, str) and ISO_DT_TZ_RE.match(st):
                date_ref = st[:10]  # YYYY-MM-DD
                break

    if date_ref:
        out["meta"]["date_reference"] = date_ref
    elif "date_reference" in out["meta"]:
        # Se veio da IA mas não conseguimos normalizar, remove
        del out["meta"]["date_reference"]

    return out
