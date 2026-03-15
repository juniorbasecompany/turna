#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste completo: leitura do conteúdo do arquivo, geração do JSON e apresentação no painel.

Fluxo:
  1. Obtém token (dev ou env).
  2. Faz upload do arquivo (PDF/JPEG/PNG) com hospital_id.
  3. Dispara job de extração (Ler conteúdo).
  4. Aguarda job COMPLETED ou FAILED (poll com timeout).
  5. Busca o JSON que o painel do arquivo exibe (result_data do job COMPLETED).
  6. Salva o JSON em test/e2e_extracted.json e exibe resumo.

Pré-requisitos:
  - Backend rodando (ex.: uvicorn), com APP_ENV=dev para /auth/dev/token
  - Redis e Worker (Arq) rodando para o job de extração concluir
  - OPENAI_API_KEY no .env do backend

Uso:
  python script_test_full_read.py <caminho_do_arquivo> --hospital-id <id>
  BACKEND_URL=http://localhost:8000 TEST_EMAIL=test@test.com python script_test_full_read.py ./doc.pdf --hospital-id 1

Variáveis de ambiente:
  BACKEND_URL   - Base da API (default: http://localhost:8000)
  TEST_EMAIL    - Email para /auth/dev/token (default: test@test.com)
  TEST_TOKEN    - Se definido, usa este token em vez de chamar /auth/dev/token
  HOSPITAL_ID   - Pode ser passado por env em vez de --hospital-id
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instale requests: pip install requests", file=sys.stderr)
    sys.exit(1)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def get_token(base_url: str, email: str) -> str:
    """Obtém JWT via POST /auth/dev/token (APP_ENV=dev)."""
    url = f"{base_url.rstrip('/')}/auth/dev/token"
    r = requests.post(
        url,
        json={"email": email, "name": "Test E2E"},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"Erro ao obter token: {r.status_code} {r.text}", file=sys.stderr)
        sys.exit(1)
    data = r.json()
    if data.get("requires_tenant_selection") and data.get("tenants"):
        tid = data["tenants"][0]["id"]
        r2 = requests.post(
            url,
            json={"email": email, "name": "Test E2E", "tenant_id": tid},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if r2.status_code != 200:
            print(f"Erro ao obter token (tenant): {r2.status_code} {r2.text}", file=sys.stderr)
            sys.exit(1)
        data = r2.json()
    token = data.get("access_token")
    if not token:
        print("Resposta sem access_token", file=sys.stderr)
        sys.exit(1)
    return token


def upload_file(base_url: str, token: str, file_path: Path, hospital_id: int) -> int:
    """Faz upload e retorna file_id."""
    url = f"{base_url.rstrip('/')}/file/upload"
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/octet-stream")}
        params = {"hospital_id": hospital_id}
        r = requests.post(
            url,
            files=files,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
    if r.status_code != 201:
        print(f"Erro no upload: {r.status_code} {r.text}", file=sys.stderr)
        sys.exit(1)
    data = r.json()
    return int(data["file_id"])


def create_extract_job(base_url: str, token: str, file_id: int) -> int:
    """Cria job de extração e retorna job_id."""
    url = f"{base_url.rstrip('/')}/job/extract"
    r = requests.post(
        url,
        json={"file_id": file_id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code not in (200, 201):
        print(f"Erro ao criar job de extração: {r.status_code} {r.text}", file=sys.stderr)
        sys.exit(1)
    return int(r.json()["job_id"])


def poll_job_status(base_url: str, token: str, job_id: int, timeout_seconds: int = 400, interval: float = 3.0) -> str:
    """Aguarda job COMPLETED ou FAILED. Retorna status."""
    url = f"{base_url.rstrip('/')}/job/{job_id}"
    start = time.monotonic()
    while (time.monotonic() - start) < timeout_seconds:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if r.status_code != 200:
            print(f"Erro ao consultar job: {r.status_code}", file=sys.stderr)
            time.sleep(interval)
            continue
        data = r.json()
        status = data.get("status", "")
        if status == "COMPLETED":
            return "COMPLETED"
        if status == "FAILED":
            return "FAILED"
        print(f"  Job status: {status} ... aguardando")
        time.sleep(interval)
    return "TIMEOUT"


def get_json_for_file_from_panel(base_url: str, token: str, file_id: int) -> tuple[dict | None, int | None]:
    """
    Obtém o JSON que o painel do arquivo exibe (igual ao fluxo do frontend).
    GET /job/list?job_type=extract_demand&status=COMPLETED&limit=100, encontra job com input_data.file_id == file_id.
    Retorna (result_data, job_id) ou (None, None) se não houver.
    """
    url = f"{base_url.rstrip('/')}/job/list"
    r = requests.get(
        url,
        params={"job_type": "extract_demand", "status": "COMPLETED", "limit": 100},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"Erro ao listar jobs: {r.status_code} {r.text}", file=sys.stderr)
        return None, None
    data = r.json()
    items = data.get("items") or []
    file_id_num = int(file_id)
    for job in items:
        inp = job.get("input_data") or {}
        jfid = inp.get("file_id")
        if jfid is not None and int(jfid) == file_id_num:
            rd = job.get("result_data")
            if rd is not None and isinstance(rd, dict):
                return rd, int(job["id"])
    return None, None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Teste completo: upload, leitura do conteúdo, geração e apresentação do JSON no painel."
    )
    parser.add_argument("file_path", type=Path, help="Caminho do PDF ou imagem (JPEG/PNG)")
    parser.add_argument("--hospital-id", type=int, default=None, help="ID do hospital (ou env HOSPITAL_ID)")
    parser.add_argument("--out", type=Path, default=None, help="Arquivo de saída do JSON (default: backend/test/e2e_extracted.json)")
    parser.add_argument("--no-upload", action="store_true", help="Pular upload e job; apenas buscar JSON para file_id (requer --file-id)")
    parser.add_argument("--file-id", type=int, default=None, help="Com --no-upload, file_id para buscar JSON do painel")
    args = parser.parse_args()

    base_url = env("BACKEND_URL", "http://localhost:8000")
    email = env("TEST_EMAIL", "test@test.com")
    token_env = env("TEST_TOKEN")
    hospital_id = args.hospital_id or (int(env("HOSPITAL_ID")) if env("HOSPITAL_ID") else None)

    if args.no_upload:
        if args.file_id is None:
            print("Com --no-upload é obrigatório --file-id.", file=sys.stderr)
            sys.exit(1)
        token = token_env or get_token(base_url, email)
        json_data, job_id = get_json_for_file_from_panel(base_url, token, args.file_id)
        if json_data is None:
            print("Nenhum job COMPLETED com result_data encontrado para este file_id.", file=sys.stderr)
            sys.exit(1)
        out_path = args.out or Path(__file__).resolve().parent / "backend" / "test" / "e2e_extracted.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = json_data.get("meta", {})
        demands = json_data.get("demands", [])
        print(f"JSON do painel (job_id={job_id}): {len(meta)} chaves em meta, {len(demands)} demandas.")
        print(f"Salvo em: {out_path}")
        return
    # Fluxo completo
    if not args.file_path.exists():
        print(f"Arquivo não encontrado: {args.file_path}", file=sys.stderr)
        sys.exit(1)
    if hospital_id is None:
        print("Informe --hospital-id ou variável HOSPITAL_ID.", file=sys.stderr)
        sys.exit(1)

    token = token_env or get_token(base_url, email)
    print("1. Upload do arquivo...")
    file_id = upload_file(base_url, token, args.file_path, hospital_id)
    print(f"   file_id={file_id}")

    print("2. Disparando job de extração (Ler conteúdo)...")
    job_id = create_extract_job(base_url, token, file_id)
    print(f"   job_id={job_id}")

    print("3. Aguardando conclusão do job (poll)...")
    status = poll_job_status(base_url, token, job_id)
    if status == "FAILED":
        r = requests.get(
            f"{base_url.rstrip('/')}/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        err = (r.json() or {}).get("error_message", "Sem mensagem")
        print(f"   Job falhou: {err}", file=sys.stderr)
        sys.exit(1)
    if status == "TIMEOUT":
        print("   Timeout aguardando o job.", file=sys.stderr)
        sys.exit(1)
    print("   Job COMPLETED.")

    print("4. Buscando JSON exibido no painel do arquivo...")
    json_data, _ = get_json_for_file_from_panel(base_url, token, file_id)
    if json_data is None:
        print("   Erro: job list não retornou result_data para este file_id.", file=sys.stderr)
        sys.exit(1)

    out_path = args.out or Path(__file__).resolve().parent / "backend" / "test" / "e2e_extracted.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = json_data.get("meta", {})
    demands = json_data.get("demands", [])
    has_meta = isinstance(meta, dict)
    has_demands = isinstance(demands, list)

    print("5. Resultado (conteúdo que aparece no painel 'JSON extraído'):")
    print(f"   meta: {len(meta)} chaves")
    print(f"   demands: {len(demands)} itens")
    print(f"   JSON salvo em: {out_path}")

    if not has_meta or not has_demands:
        print("   Estrutura inválida (esperado meta e demands).", file=sys.stderr)
        sys.exit(1)
    print("   Teste completo: OK.")


if __name__ == "__main__":
    main()
