#!/usr/bin/env python3
"""
Script para cancelar um job que está travado em status RUNNING.

Uso:
    python script_cancelar_job.py <job_id>
"""

import sys
from pathlib import Path

# Adicionar backend ao path
project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

try:
    from dotenv import load_dotenv
    load_dotenv(backend_path / ".env")
except Exception:
    pass

import os
from sqlmodel import Session, create_engine, select
from app.model.job import Job, JobStatus
from app.model.base import utc_now


def cancel_job(job_id: int, force: bool = False):
    """Cancela um job marcando como FAILED."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERRO] DATABASE_URL nao encontrada no ambiente.")
        return 1
    
    try:
        engine = create_engine(database_url)
        with Session(engine) as session:
            job = session.get(Job, job_id)
            
            if not job:
                print(f"[ERRO] Job {job_id} nao encontrado.")
                return 1
            
            print(f"Job encontrado:")
            print(f"  - ID: {job.id}")
            print(f"  - Tipo: {job.job_type}")
            print(f"  - Status atual: {job.status}")
            print(f"  - Tenant ID: {job.tenant_id}")
            
            if job.status == JobStatus.COMPLETED:
                print(f"[AVISO] Job ja esta COMPLETED. Nada a fazer.")
                return 0
            
            if job.status == JobStatus.FAILED:
                print(f"[AVISO] Job ja esta FAILED. Nada a fazer.")
                return 0
            
            # Confirmar cancelamento (se não for force)
            if not force:
                print(f"\nDeseja cancelar este job? (s/N): ", end="", flush=True)
                try:
                    resposta = input().strip().lower()
                    if resposta not in ['s', 'sim', 'y', 'yes']:
                        print("Cancelamento abortado pelo usuario.")
                        return 0
                except (EOFError, KeyboardInterrupt):
                    print("\n[AVISO] Entrada interrompida. Use --force para cancelar sem confirmacao.")
                    return 1
            else:
                print(f"\n[FORCE] Cancelando sem confirmacao...")
            
            # Marcar como FAILED
            job.status = JobStatus.FAILED
            job.error_message = "Cancelado manualmente via script"
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            
            session.add(job)
            session.commit()
            session.refresh(job)
            
            print(f"\n[OK] Job {job_id} cancelado com sucesso!")
            print(f"  - Novo status: {job.status}")
            print(f"  - Error message: {job.error_message}")
            
            return 0
            
    except Exception as e:
        print(f"[ERRO] Erro ao cancelar job: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: python script_cancelar_job.py <job_id> [--force|--yes]")
        print("\nExemplo:")
        print("  python script_cancelar_job.py 156")
        print("  python script_cancelar_job.py 156 --force")
        return 1
    
    try:
        job_id = int(sys.argv[1])
    except ValueError:
        print(f"[ERRO] Job ID invalido: {sys.argv[1]}")
        return 1
    
    force = len(sys.argv) > 2 and sys.argv[2] in ['--force', '--yes', '-f', '-y']
    
    return cancel_job(job_id, force=force)


if __name__ == "__main__":
    sys.exit(main())
