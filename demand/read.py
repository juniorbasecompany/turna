#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
read_demands_ai.py
Extractor híbrido para demandas cirúrgicas a partir de PDFs ou imagens:
1) usa IA (OpenAI) com JSON estrito
2) (cache removido)

Uso:
  python read_demands_ai.py "arquivo.pdf"
  python read_demands_ai.py "arquivo.jpg"
  python read_demands_ai.py "arquivo.png" --model gpt-4.1-mini

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

# Permite execução direta do script (importações relativas ou absolutas)
try:
    from . import config, prompt
    from .schema import (
        DEFAULT_TZ_OFFSET,
        HM_RE,
        ID_RE,
        ISO_DT_TZ_RE,
        as_list,
        canon_priority,
        canon_skill_token,
        coerce_time_to_iso,
        extract_id,
        extract_priority,
        normalize_str,
        parse_dmhm,
        parse_skills,
        parse_time_hhmm,
        period_start_ymd,
        to_iso_datetime,
        validate_and_normalize_result,
    )
except ImportError:
    # Fallback para execução direta do script
    import config
    import prompt
    from schema import (
        DEFAULT_TZ_OFFSET,
        HM_RE,
        ID_RE,
        ISO_DT_TZ_RE,
        as_list,
        canon_priority,
        canon_skill_token,
        coerce_time_to_iso,
        extract_id,
        extract_priority,
        normalize_str,
        parse_dmhm,
        parse_skills,
        parse_time_hhmm,
        period_start_ymd,
        to_iso_datetime,
        validate_and_normalize_result,
    )

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
def _render_pdf_to_png_b64(pdf_path: Path, dpi: int = None, max_pages: Optional[int] = None) -> List[str]:
    if dpi is None:
        dpi = config.DEFAULT_DPI
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
# Imagem (JPEG/PNG) -> base64 (para IA)
# -----------------------------
def _render_image_to_png_b64(image_path: Path) -> List[str]:
    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError("Instale pillow: pip install pillow") from e

    import io
    img = Image.open(str(image_path))

    # Converte para RGB se necessário (JPEG pode ser RGB, PNG pode ter transparência)
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # encode PNG -> base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return [b64]

# -----------------------------
# Arquivo (PDF/Imagem) -> imagens base64 (para IA)
# -----------------------------
def _render_file_to_png_b64(file_path: Path, dpi: int = None, max_pages: Optional[int] = None) -> List[str]:
    """
    Detecta o tipo de arquivo e renderiza para lista de imagens base64.
    Aceita PDF, JPEG e PNG.
    """
    suffix_lower = file_path.suffix.lower()

    if suffix_lower in (".jpg", ".jpeg", ".png"):
        return _render_image_to_png_b64(file_path)
    elif suffix_lower == ".pdf":
        return _render_pdf_to_png_b64(file_path, dpi=dpi, max_pages=max_pages)
    else:
        raise ValueError(f"Formato não suportado: {suffix_lower}. Use PDF, JPEG ou PNG.")

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

def _should_use_text_only(pages_text: List[Tuple[int, str]], min_chars: int = None) -> bool:
    if min_chars is None:
        min_chars = config.MIN_CHARS_FOR_TEXT_ONLY
    """
    Decide se vale mandar só texto para a IA.
    Critério simples: existe pelo menos 1 página com >= min_chars.
    """
    for _, t in pages_text:
        if len((t or "").strip()) >= min_chars:
            return True
    return False

# -----------------------------
# Schema e validação (importados de schema.py)
# -----------------------------
# Funções de schema importadas no início do arquivo - usar diretamente

# -----------------------------
# IA extraction (prompts importados de prompt.py)
# -----------------------------
# Importa prompts de prompt.py

def _call_ai_extract_text_only(pdf_path: Path, model: str, pages_text: List[Tuple[int, str]], custom_user_prompt: Optional[str] = None) -> dict:
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

    # Usa prompt customizado do hospital se fornecido, senão usa o padrão
    user_prompt = custom_user_prompt if custom_user_prompt else prompt.USER_PROMPT

    content = [
        {"type": "input_text", "text": user_prompt},
        {"type": "input_text", "text": "Conteúdo extraído (text layer) por página:\n" + joined},
    ]

    _progress(f"chamando OpenAI (text-only, model={model})...")
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": prompt.SYSTEM_PROMPT}]},
            {"role": "user", "content": content},
        ],
        temperature=config.DEFAULT_TEMPERATURE,
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
        {"model": model, "strategy": "ai_text", "prompt_version": prompt.PROMPT_VERSION}
    )
    obj.setdefault("demands", [])

    return validate_and_normalize_result(obj)

def _call_ai_extract_vision(pdf_path: Path, model: str, dpi: int, max_pages: Optional[int], custom_user_prompt: Optional[str] = None) -> dict:
    client = _openai_client()

    # render -> imagens base64
    _progress(f"renderizando arquivo -> imagens (dpi={dpi}, max_pages={max_pages})...")
    images_b64 = _render_file_to_png_b64(pdf_path, dpi=dpi, max_pages=max_pages)
    _progress(f"renderização concluída: {len(images_b64)} imagem(ns)")

    # Usa prompt customizado do hospital se fornecido, senão usa o padrão
    user_prompt = custom_user_prompt if custom_user_prompt else prompt.USER_PROMPT

    # Monta input multimodal
    # OBS: API Responses (openai python) aceita input_text + input_image
    content = [{"type": "input_text", "text": user_prompt}]
    for b64 in images_b64:
        content.append({"type": "input_image", "image_url": f"data:image/png;base64,{b64}"})

    _progress(f"chamando OpenAI (model={model})...")
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": prompt.SYSTEM_PROMPT}]},
            {"role": "user", "content": content},
        ],
        temperature=config.DEFAULT_TEMPERATURE,
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
        {"model": model, "dpi": dpi, "max_pages": max_pages, "strategy": "ai", "prompt_version": prompt.PROMPT_VERSION}
    )
    obj.setdefault("demands", [])

    return validate_and_normalize_result(obj)

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
def extract_demand(pdf_path: str, model: str = None, dpi: int = None, max_pages: Optional[int] = None,
                    custom_user_prompt: Optional[str] = None) -> dict:
    if model is None:
        model = config.DEFAULT_MODEL
    if dpi is None:
        dpi = config.DEFAULT_DPI
    file_path = Path(pdf_path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    suffix_lower = file_path.suffix.lower()

    # Se for imagem, usa visão diretamente (sem text layer)
    if suffix_lower in (".jpg", ".jpeg", ".png"):
        return _call_ai_extract_vision(file_path, model=model, dpi=dpi, max_pages=max_pages, custom_user_prompt=custom_user_prompt)

    # Para PDFs: Decide: text-only (text layer) vs visão (imagens)
    pages_text: List[Tuple[int, str]] = []
    use_text_only = False
    try:
        _progress("checando text layer (pdfplumber)...")
        pages_text = _extract_pdf_text(file_path, max_pages=max_pages)
        use_text_only = _should_use_text_only(pages_text)
    except Exception as e:
        # Se pdfplumber não estiver disponível, seguimos com visão.
        _progress(f"text layer indisponível ({e}); usando visão...")
        use_text_only = False

    if use_text_only:
        _progress("text layer detectado; enviando somente texto para a IA...")
        try:
            return _call_ai_extract_text_only(file_path, model=model, pages_text=pages_text, custom_user_prompt=custom_user_prompt)
        except Exception as e:
            _progress(f"modo text-only falhou ({e}); usando visão...")

    # fallback: visão
    return _call_ai_extract_vision(file_path, model=model, dpi=dpi, max_pages=max_pages, custom_user_prompt=custom_user_prompt)

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="Caminho do PDF ou imagem (JPEG/PNG)")
    parser.add_argument("--model", default=config.DEFAULT_MODEL, help="Modelo OpenAI")
    parser.add_argument("--dpi", type=int, default=config.DEFAULT_DPI, help="DPI para render do PDF")
    parser.add_argument("--max-pages", type=int, default=None, help="Limitar páginas (debug/custo)")
    parser.add_argument("--out", default=None, help="Caminho do JSON de saída (opcional)")

    args = parser.parse_args()

    result = extract_demand(
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
        out_path = project_root / config.DEFAULT_OUTPUT_PATH

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
