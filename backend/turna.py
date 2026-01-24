"""
Entrypoint compatível.

O código foi modularizado (dados, regras e aplicação). Este arquivo existe para manter
o comando `py turna.py` funcionando sem mudar o comportamento/saída.
"""

import importlib.util
from pathlib import Path

# Importa app.py diretamente (não o pacote app/)
spec = importlib.util.spec_from_file_location("app_module", Path(__file__).parent / "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)


MODE1 = "greedy"
MODE2 = "cp-sat"


if __name__ == "__main__":
    app_module.main(MODE1)

