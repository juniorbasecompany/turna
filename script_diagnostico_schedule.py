#!/usr/bin/env python3
"""
Script de diagnóstico para verificar se os registros fragmentados de schedule estão sendo criados.

Este script:
1. Busca logs recentes do worker
2. Filtra logs relacionados à geração de escala
3. Analisa se as alocações foram extraídas e registros criados
4. Verifica no banco de dados quantos registros foram realmente salvos
"""

import subprocess
import re
import sys
from datetime import datetime
from pathlib import Path

# Adicionar backend ao path para importar módulos
project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

try:
    from dotenv import load_dotenv
    load_dotenv(backend_path / ".env")
except Exception:
    pass

from sqlmodel import Session, select, create_engine
from app.model.schedule import Schedule
from app.model.job import Job, JobType, JobStatus
import os


def get_docker_logs(tail=500):
    """Busca logs recentes do worker via docker-compose."""
    try:
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", str(tail), "worker"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"[ERRO] Erro ao buscar logs: {result.stderr}", file=sys.stderr)
            return None
    except FileNotFoundError:
        print("[ERRO] docker-compose nao encontrado. Certifique-se de que esta instalado.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[ERRO] Timeout ao buscar logs", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}", file=sys.stderr)
        return None


def analyze_logs(logs_text):
    """Analisa logs e extrai informações relevantes."""
    if not logs_text:
        return None
    
    # Padrões para buscar
    patterns = {
        "inicio_extracao": r"\[GENERATE_SCHEDULE\] Iniciando extracao de alocacoes individuais\. per_day tem (\d+) dias",
        "total_alocadas": r"\[GENERATE_SCHEDULE\] Total de demandas alocadas encontradas: (\d+)",
        "extraidas": r"\[GENERATE_SCHEDULE\] Extraidas (\d+) alocacoes individuais",
        "preparando_gravar": r"\[GENERATE_SCHEDULE\] Preparando para gravar (\d+) registros individuais",
        "adicionados_sessao": r"\[GENERATE_SCHEDULE\] (\d+) registros individuais adicionados a sessao",
        "verificacao_pos_commit": r"\[GENERATE_SCHEDULE\] Verificacao pos-commit: (\d+) registros individuais encontrados",
        "job_completed": r"generate_schedule_job.*'ok': True.*'job_id': (\d+).*'schedule_id': (\d+)",
        "profissional_demandas": r"\[EXTRACT_ALLOCATIONS\] Profissional (.+?): (\d+) demandas",
    }
    
    results = {
        "dias_processados": None,
        "total_alocadas": None,
        "extraidas": None,
        "preparando_gravar": None,
        "adicionados_sessao": None,
        "verificacao_pos_commit": None,
        "job_id": None,
        "schedule_id": None,
        "profissionais": [],
        "linhas_relevantes": [],
    }
    
    # Buscar todas as linhas relevantes
    for line in logs_text.split("\n"):
        if "GENERATE_SCHEDULE" in line or "EXTRACT_ALLOCATIONS" in line:
            results["linhas_relevantes"].append(line)
            
            # Buscar padrões
            for key, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    if key == "job_completed":
                        results["job_id"] = int(match.group(1))
                        results["schedule_id"] = int(match.group(2))
                    elif key == "profissional_demandas":
                        results["profissionais"].append({
                            "id": match.group(1),
                            "demandas": int(match.group(2))
                        })
                    else:
                        results[key] = int(match.group(1))
    
    return results


def check_database(job_id=None, schedule_id=None):
    """Verifica no banco de dados quantos registros foram criados."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[AVISO] DATABASE_URL nao encontrada. Pulando verificacao do banco.", file=sys.stderr)
        return None
    
    try:
        engine = create_engine(database_url)
        with Session(engine) as session:
            results = {}
            
            # Se temos job_id, buscar registros relacionados
            if job_id:
                job = session.get(Job, job_id)
                if job:
                    results["job"] = {
                        "id": job.id,
                        "status": str(job.status),
                        "result_data": job.result_data,
                    }
                    
                    # Buscar todos os Schedule relacionados ao job
                    schedules = session.exec(
                        select(Schedule)
                        .where(Schedule.job_id == job_id)
                    ).all()
                    
                    results["schedules"] = {
                        "total": len(schedules),
                        "mestre": None,
                        "fragmentados": [],
                    }
                    
                    for sv in schedules:
                        result_data = sv.result_data or {}
                        if result_data.get("fragmented"):
                            results["schedules"]["mestre"] = {
                                "id": sv.id,
                                "name": sv.name,
                                "allocation_count": result_data.get("allocation_count", 0),
                            }
                        else:
                            # Verificar se é um registro fragmentado (tem professional no result_data)
                            if "professional" in result_data:
                                results["schedules"]["fragmentados"].append({
                                    "id": sv.id,
                                    "name": sv.name,
                                    "professional": result_data.get("professional"),
                                    "day": result_data.get("day"),
                                })
            
            # Se temos schedule_id, verificar diretamente
            if schedule_id:
                sv = session.get(Schedule, schedule_id)
                if sv:
                    result_data = sv.result_data or {}
                    results["schedule"] = {
                        "id": sv.id,
                        "name": sv.name,
                        "fragmented": result_data.get("fragmented", False),
                        "allocation_count": result_data.get("allocation_count", 0),
                        "has_per_day": "per_day" in result_data,
                    }
            
            return results
    except Exception as e:
        print(f"[AVISO] Erro ao verificar banco de dados: {e}", file=sys.stderr)
        return None


def print_report(log_analysis, db_check):
    """Imprime relatório formatado."""
    print("\n" + "="*70)
    print("RELATORIO DE DIAGNOSTICO - FRAGMENTACAO DE SCHEDULE")
    print("="*70 + "\n")
    
    if not log_analysis and not db_check:
        print("[ERRO] Nao foi possivel analisar os logs nem verificar o banco.")
        print("   Certifique-se de que o Docker esta rodando e tente gerar uma nova escala.\n")
        return
    
    if not log_analysis:
        print("[AVISO] Nao foi possivel analisar os logs (Docker pode nao estar acessivel).")
        print("        Mostrando apenas informacoes do banco de dados.\n")
    
    # Seção 1: Análise dos Logs
    if log_analysis:
        print("ANALISE DOS LOGS:")
        print("-" * 70)
        
        if log_analysis["dias_processados"]:
            print(f"[OK] Dias processados: {log_analysis['dias_processados']}")
        else:
            print("[AVISO] Dias processados: nao encontrado nos logs")
        
        if log_analysis["total_alocadas"] is not None:
            print(f"[OK] Total de demandas alocadas: {log_analysis['total_alocadas']}")
        else:
            print("[AVISO] Total de demandas alocadas: nao encontrado")
        
        if log_analysis["extraidas"] is not None:
            print(f"[OK] Alocacoes extraidas: {log_analysis['extraidas']}")
        else:
            print("[ERRO] Alocacoes extraidas: NENHUMA encontrada nos logs!")
            print("   [AVISO] PROBLEMA: A funcao de extracao pode nao estar sendo executada.")
        
        if log_analysis["preparando_gravar"] is not None:
            print(f"[OK] Registros preparados para gravar: {log_analysis['preparando_gravar']}")
        else:
            print("[AVISO] Registros preparados: nao encontrado")
        
        if log_analysis["adicionados_sessao"] is not None:
            print(f"[OK] Registros adicionados a sessao: {log_analysis['adicionados_sessao']}")
        else:
            print("[AVISO] Registros adicionados a sessao: nao encontrado")
        
        if log_analysis["verificacao_pos_commit"] is not None:
            print(f"[OK] Registros encontrados no banco (pos-commit): {log_analysis['verificacao_pos_commit']}")
        else:
            print("[AVISO] Verificacao pos-commit: nao encontrada")
        
        if log_analysis["job_id"]:
            print(f"[OK] Job ID: {log_analysis['job_id']}")
        if log_analysis["schedule_id"]:
            print(f"[OK] Schedule ID: {log_analysis['schedule_id']}")
        
        if log_analysis["profissionais"]:
            print(f"\n[OK] Profissionais com alocacoes: {len(log_analysis['profissionais'])}")
            for pro in log_analysis["profissionais"][:5]:  # Mostrar apenas os 5 primeiros
                print(f"   - {pro['id']}: {pro['demandas']} demandas")
            if len(log_analysis["profissionais"]) > 5:
                print(f"   ... e mais {len(log_analysis['profissionais']) - 5} profissionais")
    else:
        print("ANALISE DOS LOGS:")
        print("-" * 70)
        print("[AVISO] Logs nao disponiveis (Docker pode nao estar acessivel)")
    
    # Seção 2: Verificação do Banco de Dados
    print("\n" + "="*70)
    print("VERIFICACAO DO BANCO DE DADOS:")
    print("-" * 70)
    
    if db_check:
        if "job" in db_check:
            job = db_check["job"]
            print(f"[OK] Job {job['id']} encontrado - Status: {job['status']}")
            if job.get("result_data"):
                rd = job["result_data"]
                print(f"   - allocation_count: {rd.get('allocation_count', 'N/A')}")
                print(f"   - fragmented_records_count: {rd.get('fragmented_records_count', 'N/A')}")
        
        if "schedules" in db_check:
            schedules = db_check["schedules"]
            print(f"\n[OK] Total de registros Schedule relacionados: {schedules['total']}")
            
            if schedules["mestre"]:
                m = schedules["mestre"]
                print(f"   [MESTRE] Registro MESTRE:")
                print(f"      - ID: {m['id']}")
                print(f"      - Nome: {m['name']}")
                print(f"      - allocation_count: {m['allocation_count']}")
            
            fragmentados = schedules["fragmentados"]
            print(f"   [FRAGMENTADOS] Registros FRAGMENTADOS: {len(fragmentados)}")
            if fragmentados:
                for frag in fragmentados[:10]:  # Mostrar apenas os 10 primeiros
                    print(f"      - ID {frag['id']}: {frag['name']} (Prof: {frag['professional']}, Dia: {frag['day']})")
                if len(fragmentados) > 10:
                    print(f"      ... e mais {len(fragmentados) - 10} registros")
            else:
                print("      [ERRO] NENHUM registro fragmentado encontrado no banco!")
        
        if "schedule" in db_check:
            sv = db_check["schedule"]
            print(f"\n[OK] Schedule {sv['id']}:")
            print(f"   - Nome: {sv['name']}")
            print(f"   - Fragmented: {sv['fragmented']}")
            print(f"   - Allocation count: {sv['allocation_count']}")
            print(f"   - Tem per_day: {sv['has_per_day']}")
    else:
        print("[AVISO] Nao foi possivel verificar o banco de dados")
    
    # Seção 3: Diagnóstico
    print("\n" + "="*70)
    print("DIAGNOSTICO:")
    print("-" * 70)
    
    problemas = []
    sucessos = []
    
    if log_analysis:
        if log_analysis["extraidas"] is None or log_analysis["extraidas"] == 0:
            problemas.append("[ERRO] Nenhuma alocacao foi extraida do resultado do solver")
        elif log_analysis["extraidas"] > 0:
            sucessos.append(f"[OK] {log_analysis['extraidas']} alocacoes foram extraidas com sucesso")
        
        if log_analysis["preparando_gravar"] is None or log_analysis["preparando_gravar"] == 0:
            problemas.append("[ERRO] Nenhum registro foi preparado para gravar")
        elif log_analysis["preparando_gravar"] > 0:
            sucessos.append(f"[OK] {log_analysis['preparando_gravar']} registros foram preparados")
    
    if db_check and "schedules" in db_check:
        fragmentados = len(db_check["schedules"]["fragmentados"])
        if fragmentados == 0:
            problemas.append("[ERRO] Nenhum registro fragmentado foi encontrado no banco de dados")
        else:
            sucessos.append(f"[OK] {fragmentados} registros fragmentados encontrados no banco")
    
    if sucessos:
        for s in sucessos:
            print(s)
    
    if problemas:
        print("\n[AVISO] PROBLEMAS ENCONTRADOS:")
        for p in problemas:
            print(f"   {p}")
    elif not log_analysis and not db_check:
        print("\n[AVISO] Nao foi possivel fazer diagnostico completo (logs e banco nao disponiveis)")
    else:
        print("\n[OK] Tudo parece estar funcionando corretamente!")
    
    # Seção 4: Próximos Passos
    if problemas:
        print("\n" + "="*70)
        print("PROXIMOS PASSOS:")
        print("-" * 70)
        print("1. Verifique se o codigo foi atualizado corretamente")
        print("2. Reinicie o worker: docker-compose restart worker")
        print("3. Gere uma nova escala")
        print("4. Execute este script novamente")
    
    print("\n" + "="*70 + "\n")


def main():
    """Função principal."""
    print("Iniciando diagnostico de fragmentacao de schedule...\n")
    
    # 1. Buscar logs
    print("Buscando logs do worker...")
    logs = get_docker_logs(tail=500)
    
    log_analysis = None
    if logs:
        # 2. Analisar logs
        print("Analisando logs...")
        log_analysis = analyze_logs(logs)
    else:
        print("[AVISO] Nao foi possivel buscar logs do Docker.")
        print("        Continuando apenas com verificacao do banco de dados...\n")
    
    # 3. Verificar banco de dados
    db_check = None
    job_id = None
    schedule_id = None
    
    if log_analysis:
        job_id = log_analysis.get("job_id")
        schedule_id = log_analysis.get("schedule_id")
    
    # Se não temos job_id dos logs, buscar o último job de geração de escala
    if not job_id:
        print("Buscando ultimo job de geracao de escala no banco...")
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                engine = create_engine(database_url)
                with Session(engine) as session:
                    last_job = session.exec(
                        select(Job)
                        .where(Job.job_type == JobType.GENERATE_SCHEDULE)
                        .order_by(Job.created_at.desc())
                        .limit(1)
                    ).first()
                    if last_job:
                        job_id = last_job.id
                        result_data = last_job.result_data or {}
                        schedule_id = result_data.get("schedule_id")
                        print(f"   Encontrado job_id={job_id}, schedule_id={schedule_id}")
        except Exception as e:
            print(f"   [AVISO] Erro ao buscar ultimo job: {e}")
    
    if job_id or schedule_id:
        print("Verificando banco de dados...")
        db_check = check_database(
            job_id=job_id,
            schedule_id=schedule_id
        )
    
    # 4. Imprimir relatório
    print_report(log_analysis, db_check)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
