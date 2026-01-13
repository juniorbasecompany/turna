"""
Turna - Leitura de demandas cirúrgicas a partir de PDF (texto / imagem / misto).

API principal:
    readDemands(pdf_path: str) -> dict

Entrega:
- Envelope genérico: doc_type_guess/entities/tables/sections/meta (compatível com o que você já tem)
- PLUS: campo "demands" normalizado (o que vocês realmente precisam), com:
    date, room, start_time, end_time, procedure, anesthesia_type, complexity,
    professionals (lista), notes, source (page + row_index + raw)

Pipeline:
  1) Extração de tabela clássica (quando possível):
     - Camelot (lattice -> stream)
     - Tabula-py (fallback)
  2) Fallback 1: LLM de visão (OpenAI) para estruturar (opcional, se OPENAI_API_KEY existir)
  3) Fallback 2: Offline regex parser (sem LLM) - focado em agendas cirúrgicas

Dependências:
- pdfplumber
- pymupdf (fitz)
- camelot-py[cv] (opcional)
- tabula-py (opcional)
- openai (opcional, modo online)

Obs:
- O modo offline_regex foi ajustado para separar melhor "Cirurgião" vs "Procedimento"
  usando heurísticas clínicas (tokens de procedimento).
"""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Iterable


# -------------------------
# Public API
# -------------------------

def readDemands(pdf_path: str) -> dict:
    path = Path(pdf_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {path}")
    if not path.is_file():
        raise ValueError(f"pdf_path não é arquivo: {path}")

    debug = _env_bool("DEMAND_DEBUG", default=False)
    openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    openai_model = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
    render_zoom = _env_float("DEMAND_RENDER_ZOOM", default=2.0)
    text_max_chars = _env_int("DEMAND_TEXT_MAX_CHARS", default=6000)

    texts_by_page = _extract_text_pdfplumber(path, debug=debug)
    page_count = len(texts_by_page)
    has_text = sum(len(t or "") for t in texts_by_page) >= 20

    used_images = False
    model_used = openai_model if openai_api_key else "offline"
    strategy = "offline_regex"

    # 1) EXTRAÇÃO CLÁSSICA (Camelot/Tabula) — melhor quando PDF tem texto e tabela real.
    tables: list[dict] = []
    if has_text:
        tables = _extract_tables_camelot(path, debug=debug)
        if tables:
            strategy = "camelot"
        else:
            tables = _extract_tables_tabula(path, debug=debug)
            if tables:
                strategy = "tabula"

    # Se achou tabela clássica, podemos tentar enriquecer entities/sections via LLM (opcional),
    # mas a parte crítica (tabela) já veio.
    entities: dict[str, dict] = {}
    sections: list[dict] = []
    doc_type_guess: str | None = None

    if tables:
        if openai_api_key:
            try:
                with tempfile.TemporaryDirectory(prefix="turna_demands_") as tmp_dir:
                    pngs = _render_pages_pymupdf(path, Path(tmp_dir), zoom=render_zoom, debug=debug)
                    used_images = True
                    page_text = _limit_text(texts_by_page[0] or "", text_max_chars)
                    page_out = _extract_page_with_openai(
                        page_num=1,
                        page_text=page_text,
                        png_path=pngs[0],
                        api_key=openai_api_key,
                        model=openai_model,
                        debug=debug,
                        expect_tables=False,
                    )
                    page_out = _sanitize_page_result(page_out, page_num=1)
                    doc_type_guess = page_out.get("doc_type_guess") or None
                    entities = page_out.get("entities", {}) or {}
                    sections = page_out.get("sections", []) or []
            except Exception as e:
                if debug:
                    print(f"[readDemands] LLM meta-only falhou: {e}")

        if not sections:
            sections = _basic_sections_from_texts(texts_by_page)
        if not entities:
            entities = _basic_entities_from_texts(texts_by_page)
        if not doc_type_guess:
            doc_type_guess = _guess_doc_type(sections, entities)

        envelope = _build_envelope(
            pdf_path=str(path),
            page_count=page_count,
            has_text=has_text,
            used_images=used_images,
            model_used=model_used,
            strategy=strategy,
            doc_type_guess=doc_type_guess,
            entities=entities,
            tables=tables,
            sections=sections,
        )

        # Normaliza o que você realmente precisa
        envelope["demands"] = _normalize_demands_from_tables(envelope, debug=debug)

        _validate_envelope_or_raise(envelope)
        return envelope

    # 2) FALLBACK LLM (visão) para tabelas (se houver chave)
    if openai_api_key:
        with tempfile.TemporaryDirectory(prefix="turna_demands_") as tmp_dir:
            tmp = Path(tmp_dir)
            pngs = _render_pages_pymupdf(path, tmp, zoom=render_zoom, debug=debug)
            used_images = True

            pages: list[dict] = []
            for i in range(page_count):
                page_num = i + 1
                page_text = _limit_text(texts_by_page[i] or "", text_max_chars)
                page_out = _extract_page_with_openai(
                    page_num=page_num,
                    page_text=page_text,
                    png_path=pngs[i],
                    api_key=openai_api_key,
                    model=openai_model,
                    debug=debug,
                    expect_tables=True,
                )
                pages.append(_sanitize_page_result(page_out, page_num=page_num))

        merged = _merge_pages(
            pages,
            pdf_path=str(path),
            page_count=page_count,
            has_text=has_text,
            used_images=used_images,
            model_used=openai_model,
            strategy="llm",
        )

        # Garantia: se LLM não trouxe tabela mas há texto, tenta offline regex
        if (not merged.get("tables")) and has_text:
            t_rx, s_rx, _ = _extract_tables_offline_regex(texts_by_page, debug=debug)
            if t_rx:
                merged["tables"] = t_rx
                if not merged.get("sections"):
                    merged["sections"] = s_rx
                merged["meta"]["extraction"]["strategy"] = "offline_regex"
                merged["meta"]["extraction"]["model"] = "offline"

        merged["demands"] = _normalize_demands_from_tables(merged, debug=debug)

        _validate_envelope_or_raise(merged)
        return merged

    # 3) FALLBACK OFFLINE REGEX
    t_rx, s_rx, _ = _extract_tables_offline_regex(texts_by_page, debug=debug)
    entities = _basic_entities_from_texts(texts_by_page)
    doc_type_guess = _guess_doc_type(s_rx, entities)

    envelope = _build_envelope(
        pdf_path=str(path),
        page_count=page_count,
        has_text=has_text,
        used_images=False,
        model_used="offline",
        strategy="offline_regex",
        doc_type_guess=doc_type_guess,
        entities=entities,
        tables=t_rx,
        sections=s_rx or _basic_sections_from_texts(texts_by_page),
    )
    envelope["demands"] = _normalize_demands_from_tables(envelope, debug=debug)
    _validate_envelope_or_raise(envelope)
    return envelope


# -------------------------
# Demands normalização (o que vocês precisam)
# -------------------------

def _normalize_demands_from_tables(envelope: dict, *, debug: bool) -> list[dict]:
    """
    Converte tables (genérico) -> lista 'demands' normalizada.
    Foco: data, sala/local, início/fim, procedimento, tipo anestesia, profissionais, observações.
    """
    tables = envelope.get("tables") or []
    if not isinstance(tables, list) or not tables:
        return []

    # pega a melhor tabela (maior rows e confidence)
    best = None
    best_score = -1.0
    for t in tables:
        if not isinstance(t, dict):
            continue
        rows = t.get("rows") or []
        conf = float(t.get("confidence", 0.0) or 0.0)
        score = conf * 10.0 + (len(rows) if isinstance(rows, list) else 0)
        if score > best_score:
            best_score = score
            best = t

    if not best:
        return []

    columns = [str(c) for c in (best.get("columns") or [])]
    rows = best.get("rows") or []
    if not isinstance(rows, list):
        return []

    colmap = _map_columns(columns)

    demands: list[dict] = []
    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        date = _first_nonempty(r.get(colmap.get("date")), r.get("Data"), r.get("date"))
        room = _first_nonempty(
            r.get(colmap.get("room")),
            r.get("Sala"),
            r.get("Local"),
            r.get("Unidade"),
        )
        # horário: pode ser "Horário" ou Inicio/Fim
        start_time = _first_nonempty(r.get(colmap.get("start_time")))
        end_time = _first_nonempty(r.get(colmap.get("end_time")))
        time_range = _first_nonempty(r.get(colmap.get("time_range")), r.get("Horário"), r.get("Horario"))
        if (not start_time or not end_time) and time_range:
            st, en = _split_time_range(str(time_range))
            start_time = start_time or st
            end_time = end_time or en

        procedure = _first_nonempty(r.get(colmap.get("procedure")), r.get("Procedimento"))
        anesthesia_type = _first_nonempty(r.get(colmap.get("anesthesia_type")), r.get("Tipo anestesia"))
        complexity = _first_nonempty(r.get(colmap.get("complexity")), r.get("Complexidade"))
        notes = _first_nonempty(r.get(colmap.get("notes")), r.get("Notas"), r.get("Observações"), r.get("Observacoes"))

        surgeon = _first_nonempty(r.get(colmap.get("surgeon")), r.get("Cirurgião"), r.get("Cirurgiao"))

        # Se ainda estiver sem procedure mas surgeon veio "Dr(a). Nome PROCEDIMENTO" (caso offline regex),
        # tenta reparar.
        if (not procedure) and surgeon and isinstance(surgeon, str):
            repaired_surgeon, repaired_proc = _repair_surgeon_proc_from_joined(surgeon)
            if repaired_proc:
                procedure = repaired_proc
            if repaired_surgeon:
                surgeon = repaired_surgeon

        professionals = []
        if surgeon:
            professionals.append({"role": "cirurgiao", "name": surgeon})

        # Regras mínimas: precisa ter date + start/end ou time_range
        if not date or not start_time or not end_time:
            # ainda assim pode ser útil, mas marca como incompleta
            pass

        demand = {
            "date": date,
            "room": room,
            "start_time": start_time,
            "end_time": end_time,
            "procedure": procedure,
            "anesthesia_type": anesthesia_type,
            "complexity": complexity,
            "professionals": professionals,
            "notes": notes,
            "source": {
                "page": int(best.get("page", 1) or 1),
                "table": str(best.get("name", "table")),
                "row_index": idx,
                "raw": r,
            },
        }
        demands.append(demand)

    if debug:
        ok = sum(1 for d in demands if d.get("date") and d.get("start_time") and d.get("end_time") and d.get("procedure"))
        print(f"[readDemands] demands normalizados: {len(demands)} (completos={ok})")
    return demands


def _map_columns(columns: list[str]) -> dict[str, str | None]:
    """
    Mapeia nomes variados -> chaves canônicas.
    """
    def n(s: str) -> str:
        return _norm_key(s)

    cols = {n(c): c for c in columns}

    def pick(*candidates: str) -> str | None:
        for cand in candidates:
            if cand in cols:
                return cols[cand]
        return None

    return {
        "date": pick("data", "date"),
        "room": pick("sala", "local", "unidade"),
        "surgeon": pick("cirurgiao", "cirurgião", "medico", "médico"),
        "procedure": pick("procedimento", "cirurgia", "procedimento/cirurgia"),
        "time_range": pick("horario", "horário"),
        "start_time": pick("inicio", "início", "start"),
        "end_time": pick("fim", "end"),
        "anesthesia_type": pick("tipoanestesia", "tipo anestesia", "anestesia"),
        "complexity": pick("complexidade"),
        "notes": pick("notas", "observacoes", "observações"),
    }


def _repair_surgeon_proc_from_joined(surgeon_field: str) -> tuple[str | None, str | None]:
    """
    Quando o offline_regex erra e entrega:
        "Dr(a). Felipe Cesárea" em Cirurgião
    tenta separar procedimento do final.
    """
    s = surgeon_field.strip()
    # Se terminar com token "procedimento-like", separa
    toks = s.split()
    if len(toks) >= 3:
        last = toks[-1]
        if _is_probably_procedure_token(last):
            # nome = tudo exceto o último token; proc = último token
            return " ".join(toks[:-1]).strip(), last
    return surgeon_field, None


# -------------------------
# 1) EXTRAÇÃO CLÁSSICA (Camelot / Tabula)
# -------------------------

def _extract_tables_camelot(pdf_path: Path, *, debug: bool) -> list[dict]:
    """
    Camelot (lattice -> stream). Dependência opcional: camelot-py[cv].
    """
    try:
        import camelot  # type: ignore
    except Exception:
        return []

    for flavor in ("lattice", "stream"):
        out: list[dict] = []
        try:
            tables = camelot.read_pdf(str(pdf_path), pages="all", flavor=flavor)
        except Exception as e:
            if debug:
                print(f"[readDemands] Camelot {flavor} falhou: {e}")
            continue

        if not tables:
            continue

        for ti, t in enumerate(tables):
            try:
                df = t.df  # pandas.DataFrame
            except Exception:
                continue
            if df is None or getattr(df, "empty", False):
                continue

            grid = [[_normalize_cell(str(x)) for x in row] for row in df.values.tolist()]
            grid = _trim_empty_rows(grid)
            if len(grid) < 2:
                continue

            columns_raw = grid[0]
            if not any(c.strip() for c in columns_raw):
                continue

            columns, grid_data = _dedupe_columns_keep_first(columns_raw, grid[1:])
            rows = _grid_rows_to_dicts(columns, grid_data)
            if not rows:
                continue

            page = int(getattr(t, "page", 1) or 1)
            conf = 0.92 if flavor == "lattice" else 0.88
            out.append(
                {
                    "name": f"procedimentos_{flavor}_{ti + 1}",
                    "page": page,
                    "columns": columns,
                    "rows": rows,
                    "confidence": float(conf),
                }
            )

        if out:
            return out

    return []


def _extract_tables_tabula(pdf_path: Path, *, debug: bool) -> list[dict]:
    """
    Tabula-py (Java). Dependência opcional: tabula-py.
    """
    try:
        import tabula  # type: ignore
    except Exception:
        return []

    for lattice in (True, False):
        out: list[dict] = []
        try:
            dfs = tabula.read_pdf(
                str(pdf_path),
                pages="all",
                multiple_tables=True,
                lattice=lattice,
                stream=(not lattice),
                guess=True,
            )
        except Exception as e:
            if debug:
                print(f"[readDemands] Tabula (lattice={lattice}) falhou: {e}")
            continue

        if not dfs:
            continue

        for i, df in enumerate(dfs):
            if df is None or getattr(df, "empty", False):
                continue

            cols = [str(c).strip() for c in list(getattr(df, "columns", []))]
            cols = [c for c in cols if c]
            if not cols:
                continue

            rows: list[dict] = []
            try:
                for _, r in df.iterrows():
                    row = {}
                    for c in cols:
                        val = r.get(c)
                        if val is None:
                            row[c] = None
                        else:
                            s = str(val).strip()
                            row[c] = None if s in ("", "nan", "NaN") else s
                    if any(v not in (None, "") for v in row.values()):
                        rows.append(row)
            except Exception:
                continue

            if rows:
                out.append(
                    {
                        "name": f"procedimentos_tabula_{'lattice' if lattice else 'stream'}_{i + 1}",
                        "page": 1,
                        "columns": cols,
                        "rows": rows,
                        "confidence": 0.88 if lattice else 0.85,
                    }
                )

        if out:
            return out

    return []


def _dedupe_columns_keep_first(columns: list[str], data_rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    seen: set[str] = set()
    keep_idx: list[int] = []
    cols_out: list[str] = []
    for i, c in enumerate(columns):
        name = (c or "").strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        keep_idx.append(i)
        cols_out.append(name)

    rows_out: list[list[str]] = []
    for r in data_rows:
        rows_out.append([(r[i] if i < len(r) else "") for i in keep_idx])
    return cols_out, rows_out


def _grid_rows_to_dicts(columns: list[str], data_rows: list[list[str]]) -> list[dict]:
    rows: list[dict] = []
    for r in data_rows:
        row = {}
        for i, c in enumerate(columns):
            v = r[i].strip() if i < len(r) and isinstance(r[i], str) else (r[i] if i < len(r) else "")
            row[c] = None if v in ("", "-", "—") else v
        if any(v not in (None, "") for v in row.values()):
            rows.append(row)
    return rows


def _trim_empty_rows(grid: list[list[str]]) -> list[list[str]]:
    return [[c.strip() for c in r] for r in grid if any((c or "").strip() for c in r)]


def _normalize_cell(s: str) -> str:
    s = s.replace("\x00", "")
    return re.sub(r"\s+", " ", s).strip()


# -------------------------
# 3) OFFLINE REGEX PARSER (foco em agenda cirúrgica)
# -------------------------

def _extract_tables_offline_regex(texts_by_page: list[str], *, debug: bool) -> tuple[list[dict], list[dict], float]:
    """
    Converte texto "achatado" (pdfplumber) para tabela.
    - Só cria tabela se houver >= 5 linhas com data+horário parseáveis.
    - Preserva cabeçalho se detectar.
    """
    lines_by_page: list[list[str]] = []
    for t in texts_by_page:
        t = _normalize_ws(t or "")
        lines_by_page.append([ln.strip() for ln in t.splitlines() if ln.strip()])


    # --- Layout C (ID/Unidade/Especialidade/Procedimento/Início/Fim/Duração/Observações) ---
    header_c = _find_header_line_layout_c(lines_by_page)
    if header_c is not None:
        page_h, idx_h, _ = header_c
        parsed_rows_c: list[dict] = []
        cand = 0
        for page_i, lines in enumerate(lines_by_page, start=1):
            # considera apenas a página do header (por enquanto)
            if page_i != page_h:
                continue
            # linhas após o header
            after = [ln for j, ln in enumerate(lines) if j > idx_h]
            merged = _merge_wrapped_rows_by_id(after)
            for ln in merged:
                if re.match(r"^[A-Z]{2}-\d{4}\b", ln.strip()):
                    cand += 1
                    row = _parse_layout_c_line(ln)
                    if row:
                        parsed_rows_c.append(row)

        if len(parsed_rows_c) >= 5:
            columns_c = ["ID","Unidade","Especialidade","Procedimento","Início","Fim","Duração","Observações"]
            table_c = {
                "name": "procedimentos",
                "page": page_h,
                "columns": columns_c,
                "rows": parsed_rows_c,
                "confidence": 0.78,
            }
            sections_c = _sections_excluding_table_like(lines_by_page, header_c)
            if debug:
                print(f"[readDemands] Offline regex table (layout C): rows={len(parsed_rows_c)} cand={cand} conf=0.78")
            return [table_c], sections_c, 0.78

    header_info = _find_header_line(lines_by_page)
    columns: list[str] = []
    header_page = 1
    header_idx = None
    if header_info is not None:
        header_page, header_idx, header_line = header_info
        columns = _columns_from_header_line(header_line)
        if debug:
            print(f"[readDemands] Header detectado (p={header_page}): {header_line}")

    data_pat = re.compile(r"^\d{2}/\d{2}/\d{4}\b")
    time_pat = re.compile(r"(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})")

    parsed_rows: list[dict] = []
    total_candidates = 0
    parsed_ok = 0

    for page_i, lines in enumerate(lines_by_page, start=1):
        for li, ln in enumerate(lines):
            if header_info is not None and page_i == header_page and header_idx is not None and li == header_idx:
                continue
            if not data_pat.search(ln):
                continue
            total_candidates += 1
            if not time_pat.search(ln):
                continue
            row = _parse_procedure_line(ln, columns=columns)
            if row is None:
                continue
            parsed_ok += 1
            parsed_rows.append(row)

    if parsed_ok < 5:
        return [], _basic_sections_from_texts(texts_by_page), 0.0

    ratio = (parsed_ok / max(1, total_candidates)) if total_candidates else 0.0
    conf = 0.78 if ratio >= 0.70 else (0.60 if ratio >= 0.40 else 0.50)

    # Se não tem header detectável, usa schema mínimo que o Turna precisa
    if not columns:
        columns = ["Data", "Sala", "Cirurgião", "Procedimento", "Início", "Fim", "Tipo anestesia", "Complexidade", "Notas"]

    # garante Inicio/Fim separados (mesmo que também tenha Horário)
    normalized_rows: list[dict] = []
    for r in parsed_rows:
        rr = dict(r)
        # se só vier Horário, preenche Inicio/Fim
        if ("Início" in columns or "Inicio" in columns or "Fim" in columns) and (rr.get("Início") is None or rr.get("Fim") is None):
            st, en = _split_time_range(str(rr.get("Horário") or rr.get("Horario") or ""))
            rr.setdefault("Início", st)
            rr.setdefault("Fim", en)
        normalized_rows.append(rr)

    # filtra para colunas detectadas
    rows: list[dict] = []
    for r in normalized_rows:
        rows.append({c: r.get(c) for c in columns})

    table = {
        "name": "procedimentos",
        "page": int(header_page or 1),
        "columns": columns,
        "rows": rows,
        "confidence": float(conf),
    }
    sections = _sections_excluding_table_like(lines_by_page, header_info)

    if debug:
        print(f"[readDemands] Offline regex table: rows={len(rows)} ratio={ratio:.2f} conf={conf:.2f}")

    return [table], sections, float(conf)



def _find_header_line_layout_c(lines_by_page: list[list[str]]) -> tuple[int, int, str] | None:
    """Detecta header do layout C: ID/Unidade/Especialidade/Procedimento/Início/Fim/Duração/Observações."""
    for page_i, lines in enumerate(lines_by_page, start=1):
        for li, ln in enumerate(lines):
            low = _strip_accents(ln).lower()
            if "id" not in low:
                continue
            if "unidade" not in low:
                continue
            if "proced" not in low:
                continue
            if ("inicio" in low) and ("fim" in low):
                return page_i, li, ln
    return None


def _merge_wrapped_rows_by_id(lines: list[str]) -> list[str]:
    """Une quebras de linha dentro de uma linha de tabela do layout C (que começa com SL-2000 etc.)."""
    id_pat = re.compile(r"^[A-Z]{2}-\d{4}\b")
    out: list[str] = []
    cur: list[str] = []
    for ln in lines:
        if id_pat.search(ln.strip()):
            if cur:
                out.append(_normalize_ws(" ".join(cur)))
            cur = [ln.strip()]
        else:
            if cur:
                cur.append(ln.strip())
    if cur:
        out.append(_normalize_ws(" ".join(cur)))
    return out


def _parse_layout_c_line(line: str) -> dict | None:
    """Parseia uma linha do layout C para um dict com colunas canônicas."""
    line = _normalize_ws(line)
    toks = line.split(" ")
    if len(toks) < 10:
        return None
    if not re.match(r"^[A-Z]{2}-\d{4}$", toks[0]):
        return None

    # Estrutura típica:
    # ID | Unidade <X> | Especialidade | Procedimento... | dd/mm HH:MM | dd/mm HH:MM | <N> min | Observações...
    rec_id = toks[0]

    # Unidade: geralmente "Unidade" + "Sul/Central"
    unit = None
    idx = 1
    if len(toks) >= 3 and toks[1].lower() == "unidade":
        unit = f"{toks[1]} {toks[2]}"
        idx = 3
    else:
        # fallback: tenta pegar dois tokens
        if len(toks) >= 3:
            unit = f"{toks[1]} {toks[2]}"
            idx = 3
        else:
            return None

    # encontra o primeiro token dd/mm (início)
    date_pat = re.compile(r"^\d{2}/\d{2}$")
    try:
        start_date_i = next(i for i in range(idx, len(toks)) if date_pat.match(toks[i]))
    except StopIteration:
        return None

    # deve existir: start_date, start_time, end_date, end_time, duration, 'min'
    if start_date_i + 5 >= len(toks):
        return None
    start_date = toks[start_date_i]
    start_time = toks[start_date_i + 1]
    end_date = toks[start_date_i + 2]
    end_time = toks[start_date_i + 3]
    duration = toks[start_date_i + 4]
    min_tok = toks[start_date_i + 5].lower()
    if not re.match(r"^\d{2}:\d{2}$", start_time):
        return None
    if not re.match(r"^\d{2}:\d{2}$", end_time):
        return None
    if min_tok not in ("min", "mins", "min."):
        return None
    if not duration.isdigit():
        # alguns PDFs podem vir "120" ok; senão, tenta extrair dígitos
        m = re.search(r"(\d+)", duration)
        if not m:
            return None
        duration = m.group(1)

    # Tudo entre idx e start_date_i vira: Especialidade + Procedimento.
    # Heurística: especialidade geralmente 1 token (Cardiologia, Ortopedia, Geral, Oftalmologia)
    mid = toks[idx:start_date_i]
    if not mid:
        return None
    specialty = mid[0]
    procedure = " ".join(mid[1:]).strip() if len(mid) > 1 else None

    # Observações: após 'min'
    obs = " ".join(toks[start_date_i + 6 :]).strip() or None
    if obs in ("-", "—"):
        obs = None

    # Monta dict usando nomes de coluna do layout C
    return {
        "ID": rec_id,
        "Unidade": unit,
        "Especialidade": specialty,
        "Procedimento": procedure,
        "Início": f"{start_date} {start_time}",
        "Fim": f"{end_date} {end_time}",
        "Duração": f"{duration} min",
        "Observações": obs,
    }


def _find_header_line(lines_by_page: list[list[str]]) -> tuple[int, int, str] | None:
    for page_i, lines in enumerate(lines_by_page, start=1):
        for li, ln in enumerate(lines):
            low = _strip_accents(ln).lower()
            if "data" not in low:
                continue
            if ("hor" in low) or ("inicio" in low) or ("fim" in low):
                return page_i, li, ln
    return None


def _columns_from_header_line(header_line: str) -> list[str]:
    # separação por múltiplos espaços (quando existir)
    if re.search(r"\s{2,}", header_line):
        cols = [c.strip() for c in re.split(r"\s{2,}", header_line.strip()) if c.strip()]
        cols = _canonicalize_header_cols(cols)
        return cols

    # fallback: detecta termos mais comuns (sem inventar demais)
    patterns = [
        r"Data",
        r"Sala",
        r"Unidade",
        r"Local",
        r"Cirurgi[aã]o",
        r"Procedimento",
        r"Hor[aá]rio",
        r"In[ií]cio",
        r"Fim",
        r"Dura[cç][aã]o",
        r"Tipo\s+anestesia",
        r"Anestesia",
        r"Complexidade",
        r"Notas",
        r"Observa[cç][oõ]es",
    ]
    matches: list[tuple[int, str]] = []
    for pat in patterns:
        m = re.search(pat, header_line, flags=re.IGNORECASE)
        if m:
            matches.append((m.start(), header_line[m.start() : m.end()].strip()))
    matches.sort(key=lambda x: x[0])
    cols: list[str] = []
    for _, txt in matches:
        if txt and txt not in cols:
            cols.append(txt)
    cols = _canonicalize_header_cols(cols)
    return cols


def _canonicalize_header_cols(cols: list[str]) -> list[str]:
    """
    Ajusta levemente para garantir Inicio/Fim quando o header usa apenas "Horário".
    Sem inventar colunas aleatórias.
    """
    norm = [_strip_accents(c).lower().replace(" ", "") for c in cols]
    has_hor = any("horario" in c for c in norm)
    has_inicio = any("inicio" in c for c in norm)
    has_fim = any(c == "fim" for c in norm)

    out = cols[:]
    if has_hor and not (has_inicio and has_fim):
        # mantém "Horário" (não inventa), mas mais tarde vamos preencher Inicio/Fim na linha
        # se o consumidor quiser.
        pass
    return out


def _parse_procedure_line(line: str, *, columns: list[str]) -> dict | None:
    """
    Exemplo:
      03/02/2026 Sala 5 Dr(a). Felipe Cesárea 14:00 – 17:00 Raqui Média -
    """
    original = line.strip()
    m_date = re.match(r"^(\d{2}/\d{2}/\d{4})\b\s*(.*)$", original)
    if not m_date:
        return None
    date = m_date.group(1)
    rest = m_date.group(2).strip()

    m_time = re.search(r"(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})", rest)
    if not m_time:
        return None
    t_start, t_end = m_time.group(1), m_time.group(2)
    horario = f"{t_start} – {t_end}"

    before = rest[: m_time.start()].strip()
    after = rest[m_time.end() :].strip()

    # sala
    sala = None
    m_sala = re.search(r"\bSala\s+\d+\b", before, flags=re.IGNORECASE)
    if m_sala:
        sala = before[m_sala.start() : m_sala.end()].strip()
        before = (before[: m_sala.start()] + " " + before[m_sala.end() :]).strip()

    # split cirurgião/procedimento (melhorado)
    cirurgiao, procedimento = _split_surgeon_procedure(before)

    tipo, comp, notas = _parse_after_time(after)

    # monta com colunas detectadas (preservando)
    row: dict[str, Any] = {}
    if columns:
        for c in columns:
            c_low = _strip_accents(str(c)).lower().strip()
            c_low_ns = c_low.replace(" ", "")
            if "data" == c_low_ns:
                row[c] = date
            elif "sala" == c_low_ns:
                row[c] = sala
            elif "inicio" == c_low_ns:
                row[c] = t_start
            elif "fim" == c_low_ns:
                row[c] = t_end
            elif "horario" in c_low_ns:
                row[c] = horario
            elif "cirurgiao" in c_low_ns:
                row[c] = cirurgiao
            elif "procedimento" in c_low_ns:
                row[c] = procedimento
            elif "anestesia" in c_low_ns:
                row[c] = tipo
            elif "complexidade" in c_low_ns:
                row[c] = comp
            elif ("notas" in c_low_ns) or ("observacoes" in c_low_ns):
                row[c] = notas
            else:
                row[c] = None

        # garante campos mínimos mesmo se não existirem como colunas
        if "Início" not in row and "Inicio" not in row:
            row["Início"] = t_start
        if "Fim" not in row:
            row["Fim"] = t_end
        if "Procedimento" not in row:
            row["Procedimento"] = procedimento
        if "Cirurgião" not in row and "Cirurgiao" not in row:
            row["Cirurgião"] = cirurgiao
        if "Sala" not in row:
            row["Sala"] = sala
        if "Data" not in row:
            row["Data"] = date
        if "Horário" not in row and "Horario" not in row:
            row["Horário"] = horario
        if "Notas" not in row:
            row["Notas"] = notas
        if "Tipo anestesia" not in row:
            row["Tipo anestesia"] = tipo
        if "Complexidade" not in row:
            row["Complexidade"] = comp

        return row

    return {
        "Data": date,
        "Sala": sala,
        "Cirurgião": cirurgiao,
        "Procedimento": procedimento,
        "Início": t_start,
        "Fim": t_end,
        "Horário": horario,
        "Tipo anestesia": tipo,
        "Complexidade": comp,
        "Notas": notas,
    }


def _split_surgeon_procedure(before: str) -> tuple[str | None, str | None]:
    """
    Antes (entre Sala e Horário) geralmente é:
      "Dr(a). Nome Sobrenome Procedimento ..."
    Problema anterior: procedimento entrava no nome.
    Heurística nova:
      - captura o prefixo Dr/Dra/Dr(a).
      - captura tokens de nome até:
          * atingir 3 tokens, OU
          * o próximo token parecer "procedimento" (por padrões: ectomia/scopia/plastia/cesarea/etc.)
      - o restante vira procedimento
    """
    s = before.strip()
    if not s:
        return None, None

    m = re.match(r"^(dr\(a\)\.|dr\.|dra\.|dr|dra)\b\.?\s*(.*)$", s, flags=re.IGNORECASE)
    if not m:
        # sem título de médico: pode ser só procedimento
        return None, s

    title = m.group(1).strip()
    tail = m.group(2).strip()
    if not tail:
        return title, None

    tokens = tail.split()

    name_tokens: list[str] = []
    proc_tokens: list[str] = []

    for i, tok in enumerate(tokens):
        if not name_tokens:
            name_tokens.append(tok)
            continue

        # se o token atual parece início de procedimento, para nome
        if _is_probably_procedure_token(tok):
            proc_tokens = tokens[i:]
            break

        # ainda nome: aceita conectores e tokens com inicial maiúscula
        if len(name_tokens) < 3 and _looks_like_name_token(tok):
            name_tokens.append(tok)
            continue

        # fallback: se não parece nome e não foi classificado como procedimento, assume procedimento
        proc_tokens = tokens[i:]
        break

    if not proc_tokens and len(tokens) > len(name_tokens):
        proc_tokens = tokens[len(name_tokens):]

    surgeon = f"{title} " + " ".join(name_tokens)
    surgeon = re.sub(r"\s+", " ", surgeon).strip()

    procedure = " ".join(proc_tokens).strip() if proc_tokens else None
    procedure = procedure if procedure not in ("", "-", "—") else None

    return surgeon or None, procedure


def _is_probably_procedure_token(tok: str) -> bool:
    """
    Detecta tokens que frequentemente são início de procedimento.
    Usa normalização sem acento.
    """
    t = _strip_accents(tok).lower().strip(".,;:()[]{}")
    if not t:
        return False

    # alguns procedimentos comuns / pistas
    # (não precisa cobrir tudo — só impedir que "Cesárea" vire sobrenome)
    keywords = (
        "cesar", "cesarea",
        "scopia", "ectomia", "tomia", "plastia", "pexia",
        "artrosc", "endosc", "colonosc", "histerosc",
        "cateter", "implante", "marcapasso",
        "apendic", "colecist",
        "revascular", "revask",
        "prostatect",
        "facect",
        "estrab",
    )
    if any(k in t for k in keywords):
        return True

    # sufixos médicos frequentes
    suffixes = ("ectomia", "tomia", "scopia", "plastia", "rafia", "pexia", "oscopia")
    if any(t.endswith(s) for s in suffixes):
        return True

    return False


def _looks_like_name_token(tok: str) -> bool:
    t = tok.strip()
    if not t:
        return False
    low = _strip_accents(t).lower().strip(".,;:()")
    if low in ("de", "da", "do", "dos", "das", "e"):
        return True
    if any(ch.isdigit() for ch in t):
        return False
    return bool(re.match(r"^[A-ZÀ-Ý]", t))


def _parse_after_time(after: str) -> tuple[str | None, str | None, str | None]:
    s = after.strip()
    if not s:
        return None, None, None

    anesthesia_opts = ["Geral", "Raqui", "Sedação", "Sedacao", "Regional", "Peridural", "Local", "Bloqueio"]
    tipo = None
    for opt in anesthesia_opts:
        m = re.search(rf"\b{re.escape(opt)}\b", s, flags=re.IGNORECASE)
        if m:
            tipo = s[m.start() : m.end()]
            break

    m_comp = re.search(r"\b(Baixa|Média|Media|Alta)\b", s, flags=re.IGNORECASE)
    comp = None
    if m_comp:
        raw = m_comp.group(1)
        comp = "Média" if _strip_accents(raw).lower() == "media" else raw.capitalize()

    cleaned = s
    if tipo:
        cleaned = re.sub(rf"\b{re.escape(tipo)}\b", "", cleaned, flags=re.IGNORECASE).strip()
    if comp:
        cleaned = re.sub(rf"\b{re.escape(comp)}\b", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    notas = None if cleaned in ("", "-", "—") else cleaned
    return tipo, comp, notas


def _split_time_range(time_range: str) -> tuple[str | None, str | None]:
    m = re.search(r"(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})", time_range or "")
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _sections_excluding_table_like(lines_by_page: list[list[str]], header_info: tuple[int, int, str] | None) -> list[dict]:
    sections: list[dict] = []
    data_pat = re.compile(r"^\d{2}/\d{2}/\d{4}\b")
    time_pat = re.compile(r"(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})")

    for page_i, lines in enumerate(lines_by_page, start=1):
        for li, ln in enumerate(lines):
            if header_info is not None:
                hp, hi, _ = header_info
                if page_i == hp and li == hi:
                    continue
            if data_pat.search(ln) and time_pat.search(ln):
                continue
            kind = "title" if li <= 2 and len(ln) <= 120 else "text"
            sections.append({"kind": kind, "text": ln, "page": page_i, "confidence": 0.65 if kind == "title" else 0.55})

    return sections


# -------------------------
# 2) LLM (visão) — opcional
# -------------------------

def _extract_page_with_openai(
    *,
    page_num: int,
    page_text: str,
    png_path: Path,
    api_key: str,
    model: str,
    debug: bool,
    expect_tables: bool,
) -> dict:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("Dependência ausente: openai (modo online)") from e

    prompt = _build_page_prompt(page_num=page_num, page_text=page_text, expect_tables=expect_tables)
    data_url = f"data:image/png;base64,{_read_file_b64(png_path)}"
    client = OpenAI(api_key=api_key)

    raw = ""
    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            if attempt == 1:
                raw = _openai_vision_json(client, model=model, prompt=prompt, data_url=data_url)
            else:
                raw = _openai_fix_json(client, model=model, bad_output=raw)
            obj = _loads_json_strict(raw)
            if not isinstance(obj, dict):
                raise ValueError("LLM retornou JSON mas não é objeto (dict)")
            return obj
        except Exception as e:
            last_err = e
            if debug:
                print(f"[readDemands] LLM JSON inválido (p={page_num}, attempt={attempt}): {e}")
            continue

    raise RuntimeError(f"Falha ao extrair página {page_num} via OpenAI") from last_err


def _openai_vision_json(client: Any, *, model: str, prompt: str, data_url: str) -> str:
    # Responses API + fallback ChatCompletions
    try:
        resp = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }],
            response_format={"type": "json_object"},
        )
        out_text = getattr(resp, "output_text", None)
        if isinstance(out_text, str) and out_text.strip():
            return out_text
        return str(resp).strip()
    except Exception:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()


def _openai_fix_json(client: Any, *, model: str, bad_output: str) -> str:
    prompt = (
        "Corrija o conteúdo abaixo para JSON VÁLIDO e devolva SOMENTE JSON.\n"
        "Sem comentários e sem texto fora do JSON.\n\n"
        "CONTEÚDO:\n"
        + (bad_output or "")
    )
    try:
        resp = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            response_format={"type": "json_object"},
        )
        out_text = getattr(resp, "output_text", None)
        if isinstance(out_text, str) and out_text.strip():
            return out_text
        return str(resp).strip()
    except Exception:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()


def _build_page_prompt(*, page_num: int, page_text: str, expect_tables: bool) -> str:
    tables_rule = (
        "- Você DEVE preencher tables com columns e rows sempre que houver qualquer tabela.\n"
        if expect_tables
        else "- Não invente tables; se houver, pode deixar tables=[] (tabela virá do extractor clássico).\n"
    )
    return (
        "Você é um extrator de informações de PDF (agenda cirúrgica / demandas).\n"
        "Retorne APENAS JSON VÁLIDO (proibido texto fora do JSON).\n\n"
        "Regras:\n"
        "- Preserve nomes de colunas EXATAMENTE como aparecem (não invente colunas).\n"
        "- Campos desconhecidos podem ser null.\n"
        "- Inclua confidence (0..1) e page em cada item.\n"
        + tables_rule
        + "\n"
        "Estrutura:\n"
        "{\n"
        '  "doc_type_guess": string|null,\n'
        '  "entities": { "<chave>": { "value": any, "page": int, "confidence": float } },\n'
        '  "tables": [ { "name": string, "page": int, "columns": [string], "rows": [ { "<col>": any } ], "confidence": float } ],\n'
        '  "sections": [ { "kind": "title|note|footer|text", "text": string, "page": int, "confidence": float } ]\n'
        "}\n\n"
        f"PAGE_NUMBER: {page_num}\n\n"
        "TEXTO_EXTRAÍDO:\n"
        "-----\n"
        + (page_text if page_text.strip() else "")
        + "\n-----\n"
        "A imagem desta página foi fornecida; use-a como fonte para colunas e linhas.\n"
    )


# -------------------------
# Texto / Render
# -------------------------

def _extract_text_pdfplumber(path: Path, *, debug: bool) -> list[str]:
    try:
        import pdfplumber  # type: ignore
    except Exception as e:
        raise RuntimeError("Dependência ausente: pdfplumber") from e

    out: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                out.append(_normalize_ws(page.extract_text() or ""))
            except Exception as e:
                if debug:
                    print(f"[readDemands] pdfplumber extract_text falhou (p={i + 1}): {e}")
                out.append("")
    return out


def _render_pages_pymupdf(path: Path, out_dir: Path, *, zoom: float, debug: bool) -> list[Path]:
    try:
        import fitz  # type: ignore
    except Exception as e:
        raise RuntimeError("Dependência ausente: pymupdf (fitz)") from e

    pngs: list[Path] = []
    doc = fitz.open(str(path))
    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out_path = out_dir / f"page_{i + 1:04d}.png"
            pix.save(str(out_path))
            pngs.append(out_path)
    finally:
        doc.close()

    if debug:
        print(f"[readDemands] Render PNG ok: {len(pngs)} páginas (zoom={zoom})")
    return pngs


# -------------------------
# Envelope / Merge / Validação
# -------------------------

def _sanitize_page_result(obj: dict, *, page_num: int) -> dict:
    doc_type_guess = obj.get("doc_type_guess", None)
    if isinstance(doc_type_guess, str):
        doc_type_guess = doc_type_guess.strip() or None
    else:
        doc_type_guess = None

    entities_raw = obj.get("entities", {}) or {}
    entities: dict[str, dict] = {}
    if isinstance(entities_raw, dict):
        for k, v in entities_raw.items():
            key = str(k).strip()
            if not key or not isinstance(v, dict):
                continue
            entities[key] = {
                "value": v.get("value", None),
                "page": int(v.get("page", page_num) or page_num),
                "confidence": _clamp01(v.get("confidence", 0.0)),
            }

    tables_raw = obj.get("tables", []) or []
    tables: list[dict] = []
    if isinstance(tables_raw, list):
        for t in tables_raw:
            if not isinstance(t, dict):
                continue
            cols = t.get("columns", []) or []
            cols_str = [str(c).strip() for c in cols] if isinstance(cols, list) else []
            cols_str = [c for c in cols_str if c]
            rows_raw = t.get("rows", []) or []
            rows: list[dict] = [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []
            tables.append(
                {
                    "name": str(t.get("name", "table")),
                    "page": int(t.get("page", page_num) or page_num),
                    "columns": cols_str,
                    "rows": rows,
                    "confidence": _clamp01(t.get("confidence", 0.0)),
                }
            )

    sections_raw = obj.get("sections", []) or []
    sections: list[dict] = []
    if isinstance(sections_raw, list):
        for s in sections_raw:
            if not isinstance(s, dict):
                continue
            kind = str(s.get("kind", "text") or "text").strip().lower()
            if kind not in ("title", "note", "footer", "text"):
                kind = "text"
            text = s.get("text", "")
            if not isinstance(text, str):
                text = str(text)
            text = text.strip()
            if not text:
                continue
            sections.append(
                {
                    "kind": kind,
                    "text": text,
                    "page": int(s.get("page", page_num) or page_num),
                    "confidence": _clamp01(s.get("confidence", 0.0)),
                }
            )

    return {"doc_type_guess": doc_type_guess, "entities": entities, "tables": tables, "sections": sections}


def _merge_pages(
    pages: list[dict],
    *,
    pdf_path: str,
    page_count: int,
    has_text: bool,
    used_images: bool,
    model_used: str,
    strategy: str,
) -> dict:
    entities: dict[str, dict] = {}
    tables: list[dict] = []
    sections: list[dict] = []
    doc_type_candidates: list[str] = []

    for p in pages:
        dt = p.get("doc_type_guess")
        if isinstance(dt, str) and dt.strip():
            doc_type_candidates.append(dt.strip())
        for k, v in (p.get("entities", {}) or {}).items():
            if k not in entities or float(v.get("confidence", 0.0)) > float(entities[k].get("confidence", 0.0)):
                entities[k] = v
        tables.extend(list(p.get("tables", []) or []))
        sections.extend(list(p.get("sections", []) or []))

    doc_type_guess = doc_type_candidates[0] if doc_type_candidates else _guess_doc_type(sections, entities)
    return _build_envelope(
        pdf_path=pdf_path,
        page_count=page_count,
        has_text=has_text,
        used_images=used_images,
        model_used=model_used,
        strategy=strategy,
        doc_type_guess=doc_type_guess,
        entities=entities,
        tables=tables,
        sections=sections,
    )


def _build_envelope(
    *,
    pdf_path: str,
    page_count: int,
    has_text: bool,
    used_images: bool,
    model_used: str,
    strategy: str,
    doc_type_guess: str | None,
    entities: dict[str, dict],
    tables: list[dict],
    sections: list[dict],
) -> dict:
    return {
        "doc_type_guess": doc_type_guess,
        "entities": entities or {},
        "tables": tables or [],
        "sections": sections or [],
        "meta": {
            "pdf_path": pdf_path,
            "page_count": int(page_count),
            "extraction": {
                "has_text": bool(has_text),
                "used_images": bool(used_images),
                "model": str(model_used),
                "strategy": str(strategy),
            },
        },
    }


def _validate_envelope_or_raise(obj: Any) -> None:
    if not isinstance(obj, dict):
        raise ValueError("Envelope inválido: objeto raiz não é dict")
    for k in ("doc_type_guess", "entities", "tables", "sections", "meta", "demands"):
        if k not in obj:
            raise ValueError(f"Envelope inválido: faltando chave obrigatória '{k}'")
    meta = obj.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("Envelope inválido: meta deve ser dict")
    extraction = meta.get("extraction")
    if not isinstance(extraction, dict):
        raise ValueError("Envelope inválido: meta.extraction deve ser dict")
    for k in ("has_text", "used_images", "model", "strategy"):
        if k not in extraction:
            raise ValueError(f"Envelope inválido: meta.extraction.{k} ausente")
    if not isinstance(obj.get("demands"), list):
        raise ValueError("Envelope inválido: demands deve ser list")
    _assert_json_serializable(obj)


# -------------------------
# Heurísticas leves / utilitários
# -------------------------

def _guess_doc_type(sections: list[dict], entities: dict[str, dict]) -> str:
    text_bits: list[str] = []
    for s in sections[:8]:
        if s.get("kind") == "title":
            text_bits.append(str(s.get("text", "")))
    for k in list(entities.keys())[:8]:
        text_bits.append(k)
        v = entities.get(k, {}).get("value", None)
        if isinstance(v, str):
            text_bits.append(v)
    blob = " ".join(text_bits).lower()
    if any(w in blob for w in ("escala", "plantão", "plantao")):
        return "schedule"
    if any(w in blob for w in ("demanda", "demandas")):
        return "demands"
    if any(w in blob for w in ("agenda", "procedimento", "cirurgia", "cirurgias")):
        return "agenda"
    return "unknown"


def _basic_sections_from_texts(texts_by_page: list[str]) -> list[dict]:
    sections: list[dict] = []
    for i, t in enumerate(texts_by_page, start=1):
        t = _normalize_ws(t or "")
        if not t:
            continue
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        if not lines:
            continue
        # títulos iniciais
        for li, ln in enumerate(lines[:3]):
            if len(ln) <= 160:
                sections.append({"kind": "title" if li < 2 else "text", "text": ln, "page": i, "confidence": 0.6})
    return sections


def _basic_entities_from_texts(texts_by_page: list[str]) -> dict[str, dict]:
    entities: dict[str, dict] = {}
    all_text = "\n".join(_normalize_ws(t or "") for t in texts_by_page)

    m_hosp = re.search(r"\bHospital\s+[A-ZÀ-Ý][\wÀ-ÿ\s]+", all_text)
    if m_hosp:
        entities["hospital"] = {"value": m_hosp.group(0).strip(), "page": 1, "confidence": 0.6}

    m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", all_text)
    if m_date:
        entities["date"] = {"value": m_date.group(1), "page": 1, "confidence": 0.55}
    return entities


def _loads_json_strict(s: str) -> Any:
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido (decode): {e}") from e


def _read_file_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _normalize_ws(s: str) -> str:
    s = s.replace("\x00", "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(ln.rstrip() for ln in s.splitlines()).strip()


def _limit_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[...TRUNCATED...]"


def _clamp01(v: Any) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _assert_json_serializable(obj: Any) -> None:
    try:
        json.dumps(obj, ensure_ascii=False)
    except TypeError as e:
        raise ValueError(f"Envelope não serializável em JSON: {e}") from e


def _env_bool(name: str, *, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes", "y", "on")


def _env_int(name: str, *, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, *, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if raw == "":
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _norm_key(s: str) -> str:
    s = _strip_accents(str(s)).lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace(" ", "")
    return s


def _first_nonempty(*vals: Any) -> Any:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str):
            vv = v.strip()
            if vv == "" or vv in ("-", "—"):
                continue
            return vv
        return v
    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python read_demands.py <pdf_path>")
    out = readDemands(sys.argv[1])
    print(json.dumps(out, ensure_ascii=False, indent=2))
