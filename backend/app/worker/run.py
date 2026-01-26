from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Permite rodar via `python app/worker/run.py` (script) sem erro de import do pacote `app`.
# Quando executado assim, o Python coloca `app/worker` no sys.path, e não o project root.
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Carrega .env antes de qualquer import que use os.getenv (session, redis, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(project_root.parent / ".env")
    load_dotenv(project_root / ".env")
except Exception:
    pass

# Configurar logging antes de importar outros módulos
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from arq.worker import run_worker

from app.worker.worker_settings import WorkerSettings


def main() -> None:
    # Executa o worker do Arq (processo separado da API)
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
