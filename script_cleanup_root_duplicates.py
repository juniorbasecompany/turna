# -*- coding: utf-8 -*-
"""
Remove da raiz do repositório cópias residuais do backend (após migração para backend/).
Executar na raiz: python script_cleanup_root_duplicates.py

Se der "Access denied": feche o IDE, execute `docker compose down`, tente de novo.
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent

ITEMS = [
    "app",
    "alembic",
    "demand",
    "output",
    "strategy",
    "static",
    "requirements.txt",
    "Dockerfile",
    "app.py",
    "turna.py",
    "login.py",
    "diagnose.py",
    "alembic.ini",
]


def main() -> None:
    removed: list[str] = []
    failed: list[str] = []
    for name in ITEMS:
        p = ROOT / name
        if not p.exists():
            continue
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed.append(name)
        except Exception as e:
            failed.append(f"{name}: {e}")

    if removed:
        print("Removidos:", ", ".join(removed))
    if failed:
        print("Falharam:", ", ".join(failed))
        print("\nFeche o IDE, execute `docker compose down` e tente novamente.")
        sys.exit(1)
    if not removed and not failed:
        print("Nada a remover.")
    else:
        print("Concluído.")


if __name__ == "__main__":
    main()
