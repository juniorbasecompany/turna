#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
read_demands_ai.py
Extractor híbrido para demandas cirúrgicas a partir de PDFs:
1) tenta extração offline (rápida) via read_demands.py / regex
2) se falhar (demands vazio), usa IA (OpenAI) com JSON estrito
3) cache por hash do PDF + parâmetros (evita custo repetido)

Uso:
  python read_demands_ai.py "arquivo.pdf"
  python read_demands_ai.py "arquivo.pdf" --no-cache
  python read_demands_ai.py "arquivo.pdf" --model gpt-4.1-mini

Requisitos:
  pip install openai python-dotenv pypdfium2 pillow
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
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
# Cache
# -----------------------------
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _cache_key(pdf_hash: str, model: str, dpi: int, max_pages: Optional[int], prompt_version: str) -> str:
    raw = f"{pdf_hash}|model={model}|dpi={dpi}|max_pages={max_pages}|pv={prompt_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _cache_dir() -> Path:
    here = Path(__file__).resolve().parent
    out = here / "output" / "cache"
    out.mkdir(parents=True, exist_ok=True)
    return out

def _cache_read(key: str) -> Optional[dict]:
    p = _cache_dir() / f"{key}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _cache_write(key: str, payload: dict) -> None:
    p = _cache_dir() / f"{key}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

# -----------------------------
# Schema fixo + validação simples
# -----------------------------
ISO_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
HM_RE = re.compile(r"^\d{2}:\d{2}$")
DMHM_RE = re.compile(r"^\d{2}/\d{2}\s+\d{2}:\d{2}$")  # ex: 11/03 09:00

ALLOWED_DOC_TYPES = {"demands", "agenda", "unknown"}

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
        dd = {
            "date": _normalize_str(d.get("date")),
            "room": _normalize_str(d.get("room")),
            "start_time": _normalize_str(d.get("start_time")),
            "end_time": _normalize_str(d.get("end_time")),
            "procedure": _normalize_str(d.get("procedure")),
            "anesthesia_type": _normalize_str(d.get("anesthesia_type")),
            "complexity": _normalize_str(d.get("complexity")),
            "professionals": _as_list(d.get("professionals")),
            "notes": _normalize_str(d.get("notes")),
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

        demands.append(dd)

    out["demands"] = demands
    return out

# -----------------------------
# Fallback offline (rápido)
# -----------------------------
def _try_offline(pdf_path: Path) -> Optional[dict]:
    """
    Tenta reaproveitar o seu parser offline.
    Se retornar demands não-vazio, aceitamos.
    """
    try:
        # importa o read_demands.py (offline) do mesmo pacote/pasta
        here = Path(__file__).resolve().parent
        sys.path.insert(0, str(here))
        import read_demands as offline  # noqa
    except Exception:
        return None

    try:
        # O teu read_demands.py normalmente expõe readDemands(pdf_path) -> dict
        if hasattr(offline, "readDemands"):
            raw = offline.readDemands(str(pdf_path))
        elif hasattr(offline, "main"):
            return None
        else:
            return None

        if not isinstance(raw, dict):
            return None

        normalized = _validate_and_normalize_result(raw)
        if normalized.get("demands"):
            normalized.setdefault("meta", {})
            normalized["meta"].setdefault("hybrid", {})
            normalized["meta"]["hybrid"]["used"] = "offline"
            return normalized

        return None
    except Exception:
        return None
    finally:
        try:
            sys.path.remove(str(Path(__file__).resolve().parent))
        except Exception:
            pass

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
  - date (DD/MM/AAAA ou null)
  - room (string ou null)
  - start_time (HH:MM ou "DD/MM HH:MM")
  - end_time (HH:MM ou "DD/MM HH:MM")
  - procedure (string)
  - anesthesia_type (string ou null)
  - complexity (string ou null)
  - professionals (lista; se não houver, [])
  - notes (string ou null)
  - source (objeto livre; inclua page e qualquer raw útil)
- Não invente dados que não estejam no documento.
"""

def _call_ai_extract(pdf_path: Path, model: str, dpi: int, max_pages: Optional[int]) -> dict:
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
# Orquestração híbrida + cache
# -----------------------------
def extract_demands(pdf_path: str, model: str = "gpt-4.1-mini", dpi: int = 200, max_pages: Optional[int] = None,
                    use_cache: bool = True) -> dict:
    pdf = Path(pdf_path).resolve()
    if not pdf.exists():
        raise FileNotFoundError(str(pdf))

    _progress(f"calculando hash: {pdf.name} ...")
    pdf_hash = _sha256_file(pdf)
    key = _cache_key(pdf_hash, model=model, dpi=dpi, max_pages=max_pages, prompt_version=PROMPT_VERSION)

    if use_cache:
        _progress("verificando cache...")
        cached = _cache_read(key)
        if cached:
            _progress("cache HIT")
            cached.setdefault("meta", {})
            cached["meta"].setdefault("hybrid", {})
            cached["meta"]["hybrid"]["used"] = "cache"
            return cached
        _progress("cache MISS")

    # 1) offline
    _progress("tentando extração offline...")
    offline = _try_offline(pdf)
    if offline is not None:
        _progress("offline OK")
        if use_cache:
            _cache_write(key, offline)
        return offline
    _progress("offline vazio/indisponível; usando IA...")

    # 2) IA
    ai = _call_ai_extract(pdf, model=model, dpi=dpi, max_pages=max_pages)
    ai.setdefault("meta", {})
    ai["meta"].setdefault("hybrid", {})
    ai["meta"]["hybrid"]["used"] = "ai"
    ai["meta"]["hybrid"]["offline_failed"] = True

    if use_cache:
        _cache_write(key, ai)
    return ai

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="Caminho do PDF")
    parser.add_argument("--model", default="gpt-4.1-mini", help="Modelo OpenAI")
    parser.add_argument("--dpi", type=int, default=200, help="DPI para render do PDF")
    parser.add_argument("--max-pages", type=int, default=None, help="Limitar páginas (debug/custo)")
    parser.add_argument("--no-cache", action="store_true", help="Desabilita cache")
    parser.add_argument("--out", default=None, help="Caminho do JSON de saída (opcional)")

    args = parser.parse_args()

    result = extract_demands(
        args.pdf_path,
        model=args.model,
        dpi=args.dpi,
        max_pages=args.max_pages,
        use_cache=(not args.no_cache),
    )

    txt = json.dumps(result, ensure_ascii=False, indent=2)
    print(txt)

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
