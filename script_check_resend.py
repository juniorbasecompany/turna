#!/usr/bin/env python3
"""
Script para verificar se o Resend está instalado no container Docker.
"""
import subprocess
import sys


def check_resend_in_container():
    """Verifica se o Resend está instalado no container da API."""
    print("[VERIFICANDO] Resend no container...")
    print()

    try:
        # Verificar se o container está rodando
        result = subprocess.run(
            ["docker", "compose", "ps", "-q", "api"],
            capture_output=True,
            text=True,
            check=False,
        )

        if not result.stdout.strip():
            print("[ERRO] Container 'api' nao esta rodando.")
            print("   Execute: docker compose up -d")
            return False

        # Verificar se resend está instalado
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "api", "python", "-c", "import resend; print('OK')"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and "OK" in result.stdout:
            print("[OK] Resend esta instalado no container!")
            return True
        else:
            print("[ERRO] Resend NAO esta instalado no container.")
            print()
            print("[INFO] Para instalar, voce precisa reconstruir o container:")
            print()
            print("   docker compose down")
            print("   docker compose build --no-cache api")
            print("   docker compose up -d")
            print()
            print("   Ou simplesmente:")
            print("   docker compose up -d --build")
            return False

    except FileNotFoundError:
        print("[ERRO] Docker nao encontrado. Certifique-se de que o Docker esta instalado e no PATH.")
        return False
    except Exception as e:
        print(f"[ERRO] Erro ao verificar: {e}")
        return False


def check_requirements_txt():
    """Verifica se resend está no requirements.txt."""
    print("[VERIFICANDO] requirements.txt...")
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            content = f.read()
            if "resend" in content.lower():
                print("[OK] Resend esta no requirements.txt")
                return True
            else:
                print("[ERRO] Resend NAO esta no requirements.txt")
                return False
    except FileNotFoundError:
        print("[ERRO] requirements.txt nao encontrado")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Verificação de Instalação do Resend")
    print("=" * 60)
    print()

    req_ok = check_requirements_txt()
    print()

    if req_ok:
        container_ok = check_resend_in_container()
        print()

        if container_ok:
            print("=" * 60)
            print("[OK] Tudo OK! Resend esta instalado e pronto para uso.")
            print("=" * 60)
            sys.exit(0)
        else:
            print("=" * 60)
            print("[AVISO] Resend esta no requirements.txt mas nao no container.")
            print("   Reconstrua o container para instalar.")
            print("=" * 60)
            sys.exit(1)
    else:
        print("=" * 60)
        print("[ERRO] Resend nao esta no requirements.txt")
        print("=" * 60)
        sys.exit(1)
