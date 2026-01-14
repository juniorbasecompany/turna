from __future__ import annotations

import sys
from pathlib import Path

from arq.worker import run_worker

# Permite rodar via `python app/workers/run.py` (script) sem erro de import do pacote `app`.
# Quando executado assim, o Python coloca `app/workers` no sys.path, e não o project root.
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.workers.worker_settings import WorkerSettings


def main() -> None:
    # Executa o worker do Arq (processo separado da API)
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
