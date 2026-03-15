#!/usr/bin/env python3
"""
Executa a extração de demandas (demand.read) para um PDF ou imagem e grava o JSON.
Uso: python script_run_extract.py <caminho_do_arquivo> [--out saida.json]

O resultado é o mesmo que o job extract_demand_job grava em Job.result_data.
"""
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python script_run_extract.py <caminho_do_arquivo> [--out saida.json]", file=sys.stderr)
        sys.exit(1)
    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists():
        print(f"Arquivo não encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    backend_dir = Path(__file__).resolve().parent / "backend"
    args = [sys.executable, "-m", "demand.read", str(pdf_path)]
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        if i + 1 < len(sys.argv):
            args.extend(["--out", sys.argv[i + 1]])
    rc = subprocess.run(args, cwd=str(backend_dir))
    if rc.returncode != 0:
        sys.exit(rc.returncode)
    out_path = backend_dir / "test" / "demanda.json"
    if "--out" in sys.argv and sys.argv.index("--out") + 1 < len(sys.argv):
        out_path = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    if out_path.exists():
        data = json.loads(out_path.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        demands = data.get("demands", [])
        print(f"Resultado: meta com {len(meta)} chaves, demands com {len(demands)} itens.")
        print(f"JSON salvo em: {out_path}")


if __name__ == "__main__":
    main()
