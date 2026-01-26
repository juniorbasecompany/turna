#!/usr/bin/env python3
"""
Script para verificar status do job e reiniciar worker se necessário.
"""

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent

def reiniciar_worker():
    """Reinicia o worker do Docker."""
    print("Reiniciando worker...")
    try:
        result = subprocess.run(
            ["docker-compose", "restart", "worker"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("[OK] Worker reiniciado com sucesso!")
            return True
        else:
            print(f"[ERRO] Erro ao reiniciar worker: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERRO] Erro ao reiniciar worker: {e}")
        return False

def main():
    print("="*70)
    print("VERIFICACAO E REINICIO DO WORKER")
    print("="*70)
    print()
    print("O worker precisa ser reiniciado para carregar as mudancas no codigo.")
    print("Deseja reiniciar agora? (s/N): ", end="", flush=True)
    
    try:
        resposta = input().strip().lower()
        if resposta in ['s', 'sim', 'y', 'yes']:
            if reiniciar_worker():
                print("\n[OK] Worker reiniciado!")
                print("Aguarde alguns segundos e gere uma nova escala.")
                return 0
            else:
                return 1
        else:
            print("Reinicio cancelado.")
            print("\nPara reiniciar manualmente, execute:")
            print("  docker-compose restart worker")
            return 0
    except (EOFError, KeyboardInterrupt):
        print("\n[AVISO] Entrada interrompida.")
        print("\nPara reiniciar manualmente, execute:")
        print("  docker-compose restart worker")
        return 1

if __name__ == "__main__":
    sys.exit(main())
