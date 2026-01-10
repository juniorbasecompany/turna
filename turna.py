"""
Entrypoint compatível.

O código foi modularizado (dados, regras e aplicação). Este arquivo existe para manter
o comando `py turna.py` funcionando sem mudar o comportamento/saída.
"""

from app import main


MODE1 = "greedy"
MODE2 = "cp-sat"


if __name__ == "__main__":
    main(MODE1)

