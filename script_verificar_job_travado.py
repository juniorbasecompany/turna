#!/usr/bin/env python3
"""
Script para verificar por que um job está travado em RUNNING.
"""

import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

try:
    from dotenv import load_dotenv
    load_dotenv(backend_path / ".env")
except Exception:
    pass

import os
from sqlmodel import Session, create_engine
from app.model.job import Job, JobStatus
from app.model.base import utc_now


def verificar_job(job_id: int):
    """Verifica detalhes de um job travado."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERRO] DATABASE_URL nao encontrada.")
        return 1
    
    try:
        engine = create_engine(database_url)
        with Session(engine) as session:
            job = session.get(Job, job_id)
            
            if not job:
                print(f"[ERRO] Job {job_id} nao encontrado.")
                return 1
            
            print("="*70)
            print(f"INFORMACOES DO JOB {job_id}")
            print("="*70)
            print(f"Status: {job.status}")
            print(f"Tipo: {job.job_type}")
            print(f"Tenant ID: {job.tenant_id}")
            print(f"Criado em: {job.created_at}")
            print(f"Atualizado em: {job.updated_at}")
            
            if job.started_at:
                print(f"Iniciado em: {job.started_at}")
                tempo_decorrido = utc_now() - job.started_at
                print(f"Tempo decorrido: {tempo_decorrido}")
                print(f"  - Total segundos: {tempo_decorrido.total_seconds():.1f}s")
                print(f"  - Total minutos: {tempo_decorrido.total_seconds() / 60:.1f}min")
                
                # Se está rodando há mais de 5 minutos, provavelmente travou
                if tempo_decorrido.total_seconds() > 300:
                    print(f"\n[AVISO] Job esta rodando ha mais de 5 minutos - provavelmente travado!")
            else:
                print("Iniciado em: N/A")
            
            if job.completed_at:
                print(f"Completado em: {job.completed_at}")
            else:
                print("Completado em: N/A (ainda rodando)")
            
            if job.error_message:
                print(f"\nMensagem de erro: {job.error_message}")
            
            if job.input_data:
                print(f"\nInput data:")
                import json
                print(json.dumps(job.input_data, indent=2, default=str))
            
            if job.result_data:
                print(f"\nResult data:")
                import json
                print(json.dumps(job.result_data, indent=2, default=str))
            
            print("\n" + "="*70)
            
            # Diagnóstico
            if job.status == JobStatus.RUNNING:
                if job.started_at:
                    tempo = (utc_now() - job.started_at).total_seconds()
                    if tempo > 300:  # 5 minutos
                        print("[DIAGNOSTICO] Job provavelmente travado!")
                        print("  Possiveis causas:")
                        print("  1. Worker usando codigo antigo (precisa reiniciar)")
                        print("  2. Erro nao capturado no codigo")
                        print("  3. Deadlock no banco de dados")
                        print("  4. Processo travado em loop infinito")
                        print("\n  Solucao:")
                        print("  1. Reinicie o worker: docker-compose restart worker")
                        print("  2. Cancele este job: python script_cancelar_job.py", job_id, "--force")
                        print("  3. Gere uma nova escala")
                else:
                    print("[DIAGNOSTICO] Job em RUNNING mas sem started_at - estado inconsistente!")
            
            return 0
            
    except Exception as e:
        print(f"[ERRO] Erro ao verificar job: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    if len(sys.argv) < 2:
        print("Uso: python script_verificar_job_travado.py <job_id>")
        print("\nExemplo:")
        print("  python script_verificar_job_travado.py 157")
        return 1
    
    try:
        job_id = int(sys.argv[1])
    except ValueError:
        print(f"[ERRO] Job ID invalido: {sys.argv[1]}")
        return 1
    
    return verificar_job(job_id)


if __name__ == "__main__":
    sys.exit(main())
