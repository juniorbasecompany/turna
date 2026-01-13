#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
read_demands_ai.py
Extractor híbrido para demandas cirúrgicas a partir de PDFs:
1) usa IA (OpenAI) com JSON estrito
2) (cache removido)

Uso:
  python read_demands_ai.py "arquivo.pdf"
  python read_demands_ai.py "arquivo.pdf"
  python read_demands_ai.py "arquivo.pdf" --model gpt-4.1-mini

Requisitos:
  pip install openai python-dotenv pypdfium2 pillow
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------
# Progresso (stderr, não altera JSON em stdout)
# -----------------------------
def _progress(msg: str) -> None:
    """
    Logs de progresso para evitar impressão de "congelamento".
    Vai para stderr para não interferir no JSON impresso em stdout.
    Desative com: DEMAND_PROGRESS=0
    """
    v = (os.getenv("DEMAND_PROGRESS") or "1").strip().lower()
    if v in {"0", "false", "no", "off"}:
        return
    try:
        print(f"[turna] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass

# -----------------------------
# Env loading (robusto)
# -----------------------------
try:
    from dotenv import load_dotenv

    here = Path(__file__).resolve().parent       # demand/
    project_root = here.parent                   # turna/
    # 1) Preferir sempre o .env na raiz do projeto (robusto mesmo se CWD mudar)
    load_dotenv(project_root / ".env")
    # 2) Também tenta .env no diretório atual (útil em execuções ad-hoc)
    load_dotenv(".env")
except Exception:
    pass

# -----------------------------
# OpenAI client
# -----------------------------
def _openai_client():
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("Instale openai: pip install openai") from e

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não encontrada. Coloque no arquivo .env na raiz do projeto (turna/.env):\n"
            "OPENAI_API_KEY=sk-...\n"
        )
    return OpenAI(api_key=api_key)

# -----------------------------
# PDF -> imagens (para IA)
# -----------------------------
def _render_pdf_to_png_b64(pdf_path: Path, dpi: int = 200, max_pages: Optional[int] = None) -> List[str]:
    try:
        import pypdfium2 as pdfium
        from PIL import Image
    except Exception as e:
        raise RuntimeError("Instale pypdfium2 e pillow: pip install pypdfium2 pillow") from e

    pdf = pdfium.PdfDocument(str(pdf_path))
    n_pages = len(pdf)
    if max_pages is not None:
        n_pages = min(n_pages, max_pages)

    out: List[str] = []
    scale = dpi / 72.0

    for i in range(n_pages):
        page = pdf.get_page(i)
        pil_image = page.render(scale=scale).to_pil()
        page.close()

        # encode PNG -> base64
        import io
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        out.append(b64)

    pdf.close()
    return out

# -----------------------------
# PDF -> texto (text layer)
# -----------------------------
def _extract_pdf_text(pdf_path: Path, max_pages: Optional[int] = None) -> List[Tuple[int, str]]:
    """
    Extrai texto por página via pdfplumber. Retorna lista (page_num, text).
    Se pdfplumber não estiver instalado, levanta RuntimeError com instrução.
    """
    try:
        import pdfplumber
    except Exception as e:
        raise RuntimeError("Instale pdfplumber: pip install pdfplumber") from e

    out: List[Tuple[int, str]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = pdf.pages
        if max_pages is not None:
            pages = pages[:max_pages]
        for i, page in enumerate(pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            out.append((i + 1, text))
    return out

def _should_use_text_only(pages_text: List[Tuple[int, str]], min_chars: int = 40) -> bool:
    """
    Decide se vale mandar só texto para a IA.
    Critério simples: existe pelo menos 1 página com >= min_chars.
    """
    for _, t in pages_text:
        if len((t or "").strip()) >= min_chars:
            return True
    return False

# -----------------------------
# Schema fixo + validação simples
# -----------------------------
ISO_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
HM_RE = re.compile(r"^\d{2}:\d{2}$")
DMHM_RE = re.compile(r"^\d{2}/\d{2}\s+\d{2}:\d{2}$")  # ex: 11/03 09:00
ID_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,6}\b")

ALLOWED_DOC_TYPES = {"demands", "agenda", "unknown"}
DEFAULT_TZ_OFFSET = "-03:00"

def _canon_priority(x: Optional[str]) -> Optional[str]:
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

def _extract_priority(notes: Optional[str]) -> Optional[str]:
    if not notes:
        return None
    m = re.search(r"(?i)\bprioridade\s*:\s*(urgente|emerg[êe]ncia)\b", notes)
    if not m:
        return None
    return _canon_priority(m.group(1))

def _canon_skill_token(tok: str) -> str:
    t = tok.strip()
    if not t:
        return ""
    # normalizações comuns (sem inventar skills novas)
    if t.lower() == "obstetrica":
        return "Obstétrica"
    if t.lower() == "cardiaca":
        return "Cardíaca"
    return t

def _parse_skills(x: Any) -> List[str]:
    """
    skills: lista de strings. Aceita entrada como lista ou string separada por vírgula.
    """
    if x is None:
        return []
    if isinstance(x, list):
        out: List[str] = []
        for it in x:
            s = _canon_skill_token(str(it))
            if s:
                out.append(s)
        return out
    if isinstance(x, str):
        # corta tudo após "Prioridade:" se veio junto
        s = re.split(r"(?i)\bprioridade\s*:", x, maxsplit=1)[0]
        parts = re.split(r"[;,|]", s)
        out = []
        for p in parts:
            t = _canon_skill_token(p)
            if t:
                out.append(t)
        return out
    return []

def _extract_id(d: dict) -> Optional[str]:
    # Preferir campos explícitos
    for k in ("id", "ID", "case_id", "caseId"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Tentar do source/raw
    src = d.get("source") if isinstance(d.get("source"), dict) else {}
    raw = src.get("raw")
    if isinstance(raw, str):
        m = ID_RE.search(raw)
        if m:
            return m.group(0)
    return None

def _parse_iso_date(date_ddmmyyyy: str) -> Optional[Tuple[int, int, int]]:
    if not date_ddmmyyyy or not ISO_DATE_RE.match(date_ddmmyyyy):
        return None
    dd, mm, yyyy = date_ddmmyyyy.split("/")
    try:
        return int(yyyy), int(mm), int(dd)
    except Exception:
        return None

def _parse_time_hhmm(s: str) -> Optional[Tuple[int, int]]:
    if not s or not HM_RE.match(s):
        return None
    hh, mm = s.split(":")
    try:
        return int(hh), int(mm)
    except Exception:
        return None

def _parse_dmhm(s: str) -> Optional[Tuple[int, int, int, int]]:
    if not s or not DMHM_RE.match(s):
        return None
    dm, hm = s.split()
    dd, mm = dm.split("/")
    hh, mi = hm.split(":")
    try:
        return int(dd), int(mm), int(hh), int(mi)
    except Exception:
        return None

def _to_iso_local(yyyy: int, mm: int, dd: int, hh: int, mi: int, tz_offset: str = DEFAULT_TZ_OFFSET) -> str:
    return f"{yyyy:04d}-{mm:02d}-{dd:02d}T{hh:02d}:{mi:02d}:00{tz_offset}"

def _derive_start_end_iso(date_ddmmyyyy: Optional[str], start_time: Optional[str], end_time: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    start_at/end_at em ISO com offset fixo (padrão -03:00).
    Só calcula se houver ano disponível (via date DD/MM/AAAA).
    """
    if not date_ddmmyyyy:
        return None, None
    base = _parse_iso_date(date_ddmmyyyy)
    if not base:
        return None, None
    yyyy, base_mm, base_dd = base

    s_at: Optional[str] = None
    e_at: Optional[str] = None

    if start_time:
        dmhm = _parse_dmhm(start_time.strip())
        if dmhm:
            dd, mm, hh, mi = dmhm
            s_at = _to_iso_local(yyyy, mm, dd, hh, mi)
        else:
            hm = _parse_time_hhmm(start_time.strip())
            if hm:
                hh, mi = hm
                s_at = _to_iso_local(yyyy, base_mm, base_dd, hh, mi)

    if end_time:
        dmhm = _parse_dmhm(end_time.strip())
        if dmhm:
            dd, mm, hh, mi = dmhm
            e_at = _to_iso_local(yyyy, mm, dd, hh, mi)
        else:
            hm = _parse_time_hhmm(end_time.strip())
            if hm:
                hh, mi = hm
                e_at = _to_iso_local(yyyy, base_mm, base_dd, hh, mi)

    return s_at, e_at

def _normalize_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None

def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []

def _validate_and_normalize_result(obj: dict) -> dict:
    """
    Garante que o JSON final tenha sempre as chaves e tipos esperados.
    Não tenta "adivinhar" campos complexos; só normaliza e protege.
    """
    out: Dict[str, Any] = {}

    out["doc_type_guess"] = obj.get("doc_type_guess")
    if out["doc_type_guess"] not in ALLOWED_DOC_TYPES:
        out["doc_type_guess"] = "unknown"

    # entities
    entities = obj.get("entities") if isinstance(obj.get("entities"), dict) else {}
    out["entities"] = entities

    # sections / tables
    out["sections"] = _as_list(obj.get("sections"))
    out["tables"] = _as_list(obj.get("tables"))

    # meta
    meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
    out["meta"] = meta

    # demands
    demands = []
    for d in _as_list(obj.get("demands")):
        if not isinstance(d, dict):
            continue

        notes = _normalize_str(d.get("notes"))
        priority = _extract_priority(notes)

        # skills: preferir campo explícito; fallback heurístico para casos onde IA colocou em "complexity"
        skills = _parse_skills(d.get("skills"))
        if not skills:
            skills = _parse_skills(d.get("habilidades"))
        if not skills:
            # heuristic: se "complexity" veio como lista de habilidades (ex: "Geral, Obstétrica")
            cx = _normalize_str(d.get("complexity"))
            if cx and ("," in cx or "|" in cx or ";" in cx):
                skills = _parse_skills(cx)

        dd = {
            "id": _extract_id(d),
            "date": _normalize_str(d.get("date")),
            "room": _normalize_str(d.get("room")),
            "start_time": _normalize_str(d.get("start_time")),
            "end_time": _normalize_str(d.get("end_time")),
            "start_at": None,
            "end_at": None,
            "procedure": _normalize_str(d.get("procedure")),
            "anesthesia_type": _normalize_str(d.get("anesthesia_type")),
            "complexity": _normalize_str(d.get("complexity")),
            "skills": skills,
            "priority": priority,
            "professionals": _as_list(d.get("professionals")),
            "notes": notes,
            "source": d.get("source") if isinstance(d.get("source"), dict) else {},
        }

        # Regras mínimas: precisa ter procedure + start/end (ou início/fim "dd/mm hh:mm")
        if not dd["procedure"]:
            continue

        # aceita HH:MM ou "dd/mm HH:MM"
        def ok_time(t: Optional[str]) -> bool:
            if not t:
                return False
            return bool(HM_RE.match(t) or DMHM_RE.match(t))

        if not (ok_time(dd["start_time"]) and ok_time(dd["end_time"])):
            # ainda pode ser válido se vier tudo dentro de "source/raw" e você quiser tratar depois,
            # mas por padrão não vamos aceitar como demanda pronta.
            continue

        # date pode ser None se o layout não fornecer ano.
        if dd["date"] and not ISO_DATE_RE.match(dd["date"]):
            dd["date"] = None

        dd["start_at"], dd["end_at"] = _derive_start_end_iso(dd["date"], dd["start_time"], dd["end_time"])

        demands.append(dd)

    out["demands"] = demands
    return out

# -----------------------------
# IA extraction
# -----------------------------
PROMPT_VERSION = "v2.0"
SYSTEM_PROMPT = """Você é um extrator de dados de agenda cirúrgica.
Extraia as demandas (linhas de tabela) do PDF.
Você DEVE responder APENAS com JSON válido (sem markdown, sem explicações).
"""

USER_PROMPT = """Extraia as demandas cirúrgicas do documento.
Regras:
- Responda APENAS JSON.
- O JSON DEVE conter as chaves: doc_type_guess, entities, tables, sections, meta, demands.
- demands é uma lista de objetos com:
  - id (ex: "DC-1001" ou null)
  - date (DD/MM/AAAA ou null)
  - room (string ou null)
  - start_time (HH:MM ou "DD/MM HH:MM")
  - end_time (HH:MM ou "DD/MM HH:MM")
  - procedure (string)
  - anesthesia_type (string ou null)
  - skills (lista; se não houver, [])
  - priority ("Urgente" | "Emergência" | null)  # extrair de notes quando houver "Prioridade: ..."
  - complexity (string ou null)  # se existir como complexidade do caso (Baixa/Média/Alta)
  - professionals (lista; se não houver, [])
  - notes (string ou null)
  - source (objeto livre; inclua page e qualquer raw útil)
- Não invente dados que não estejam no documento.
"""

def _call_ai_extract_text_only(pdf_path: Path, model: str, pages_text: List[Tuple[int, str]]) -> dict:
    client = _openai_client()

    # Monta input somente texto (sem imagens)
    blocks: List[str] = []
    for page_num, text in pages_text:
        if not (text or "").strip():
            continue
        blocks.append(f"--- Página {page_num} ---\n{text.strip()}\n")

    joined = "\n".join(blocks).strip()
    if not joined:
        # sem texto útil -> caller deve cair para visão
        raise RuntimeError("PDF sem text layer útil para modo text-only")

    content = [
        {"type": "input_text", "text": USER_PROMPT},
        {"type": "input_text", "text": "Conteúdo extraído (text layer) por página:\n" + joined},
    ]

    _progress(f"chamando OpenAI (text-only, model={model})...")
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": content},
        ],
        temperature=0,
    )
    _progress("OpenAI respondeu; parseando JSON...")

    txt = ""
    try:
        txt = resp.output_text
    except Exception:
        try:
            txt = json.dumps(resp.model_dump(), ensure_ascii=False)
        except Exception:
            txt = str(resp)

    obj = _parse_json_strict(txt)
    obj.setdefault("meta", {})
    obj["meta"]["pdf_path"] = str(pdf_path)
    obj["meta"].setdefault("extraction", {})
    obj["meta"]["extraction"].update(
        {"model": model, "strategy": "ai_text", "prompt_version": PROMPT_VERSION}
    )
    obj.setdefault("doc_type_guess", "unknown")
    obj.setdefault("entities", {})
    obj.setdefault("tables", [])
    obj.setdefault("sections", [])
    obj.setdefault("demands", [])

    return _validate_and_normalize_result(obj)

def _call_ai_extract_vision(pdf_path: Path, model: str, dpi: int, max_pages: Optional[int]) -> dict:
    client = _openai_client()

    # render -> imagens base64
    _progress(f"renderizando PDF -> imagens (dpi={dpi}, max_pages={max_pages})...")
    images_b64 = _render_pdf_to_png_b64(pdf_path, dpi=dpi, max_pages=max_pages)
    _progress(f"renderização concluída: {len(images_b64)} página(s)")

    # Monta input multimodal
    # OBS: API Responses (openai python) aceita input_text + input_image
    content = [{"type": "input_text", "text": USER_PROMPT}]
    for b64 in images_b64:
        content.append({"type": "input_image", "image_url": f"data:image/png;base64,{b64}"})

    _progress(f"chamando OpenAI (model={model})...")
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": content},
        ],
        temperature=0,
    )
    _progress("OpenAI respondeu; parseando JSON...")

    # Extrai texto final
    txt = ""
    try:
        txt = resp.output_text
    except Exception:
        # fallback: tenta achar texto em resp.output
        try:
            txt = json.dumps(resp.model_dump(), ensure_ascii=False)
        except Exception:
            txt = str(resp)

    # Parse JSON estrito
    obj = _parse_json_strict(txt)
    obj.setdefault("meta", {})
    obj["meta"]["pdf_path"] = str(pdf_path)
    obj["meta"].setdefault("extraction", {})
    obj["meta"]["extraction"].update(
        {"model": model, "dpi": dpi, "max_pages": max_pages, "strategy": "ai", "prompt_version": PROMPT_VERSION}
    )
    obj.setdefault("doc_type_guess", "unknown")
    obj.setdefault("entities", {})
    obj.setdefault("tables", [])
    obj.setdefault("sections", [])
    obj.setdefault("demands", [])

    return _validate_and_normalize_result(obj)

def _parse_json_strict(txt: str) -> dict:
    """
    Aceita JSON puro. Se vier lixo antes/depois, tenta recortar o primeiro objeto {...}.
    """
    txt = txt.strip()

    # tentativa direta
    try:
        o = json.loads(txt)
        if isinstance(o, dict):
            return o
    except Exception:
        pass

    # recorte heurístico do primeiro {...}
    m = re.search(r"\{.*\}", txt, flags=re.DOTALL)
    if m:
        cut = m.group(0)
        try:
            o = json.loads(cut)
            if isinstance(o, dict):
                return o
        except Exception:
            pass

    raise RuntimeError("A IA não retornou JSON válido. Veja a saída bruta para diagnóstico.")

# -----------------------------
# Orquestração híbrida (cache removido)
# -----------------------------
def extract_demands(pdf_path: str, model: str = "gpt-4.1-mini", dpi: int = 200, max_pages: Optional[int] = None,
                    ) -> dict:
    pdf = Path(pdf_path).resolve()
    if not pdf.exists():
        raise FileNotFoundError(str(pdf))

    # Decide: text-only (text layer) vs visão (imagens)
    pages_text: List[Tuple[int, str]] = []
    use_text_only = False
    try:
        _progress("checando text layer (pdfplumber)...")
        pages_text = _extract_pdf_text(pdf, max_pages=max_pages)
        use_text_only = _should_use_text_only(pages_text, min_chars=40)
    except Exception as e:
        # Se pdfplumber não estiver disponível, seguimos com visão.
        _progress(f"text layer indisponível ({e}); usando visão...")
        use_text_only = False

    if use_text_only:
        _progress("text layer detectado; enviando somente texto para a IA...")
        try:
            return _call_ai_extract_text_only(pdf, model=model, pages_text=pages_text)
        except Exception as e:
            _progress(f"modo text-only falhou ({e}); usando visão...")

    # fallback: visão
    return _call_ai_extract_vision(pdf, model=model, dpi=dpi, max_pages=max_pages)

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="Caminho do PDF")
    parser.add_argument("--model", default="gpt-4.1-mini", help="Modelo OpenAI")
    parser.add_argument("--dpi", type=int, default=200, help="DPI para render do PDF")
    parser.add_argument("--max-pages", type=int, default=None, help="Limitar páginas (debug/custo)")
    parser.add_argument("--out", default=None, help="Caminho do JSON de saída (opcional)")

    args = parser.parse_args()

    result = extract_demands(
        args.pdf_path,
        model=args.model,
        dpi=args.dpi,
        max_pages=args.max_pages,
    )

    txt = json.dumps(result, ensure_ascii=False, indent=2)

    if args.out:
        out_path = Path(args.out).resolve()
    else:
        # padrão: test/demanda.json na raiz do projeto
        here = Path(__file__).resolve().parent
        project_root = here.parent
        out_path = project_root / "test" / "demanda.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
