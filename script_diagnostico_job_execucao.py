#!/usr/bin/env python3
"""
Script de diagnóstico para verificar se um job está sendo executado corretamente ou se está em loop/travado.

Este script:
1. Verifica jobs em execução (status RUNNING)
2. Detecta jobs travados (sem atualização há muito tempo)
3. Analisa logs recentes para detectar loops ou progresso
4. Mostra em qual etapa o job está
5. Sugere ações corretivas
"""

import subprocess
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

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
from app.model.job import Job, JobType, JobStatus
from app.model.base import utc_now
import os


def get_docker_logs(tail=1000, job_id: Optional[int] = None) -> Optional[str]:
    """Busca logs recentes do worker via docker-compose."""
    try:
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", str(tail), "worker"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Substitui caracteres inválidos ao invés de falhar
            cwd=project_root,
            timeout=15,
        )
        if result.returncode == 0:
            logs = result.stdout
            # Se temos job_id, filtrar apenas logs relacionados
            if job_id:
                lines = logs.split("\n")
                filtered = [line for line in lines if f"job_id={job_id}" in line or f"job_id={job_id}," in line or f"Job {job_id}" in line]
                return "\n".join(filtered)
            return logs
        else:
            print(f"[AVISO] Erro ao buscar logs: {result.stderr}", file=sys.stderr)
            return None
    except FileNotFoundError:
        print("[AVISO] docker-compose não encontrado. Logs não disponíveis.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[AVISO] Timeout ao buscar logs", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[AVISO] Erro ao buscar logs: {e}", file=sys.stderr)
        return None


def analyze_job_progress(logs_text: str, job_id: int) -> Dict:
    """Analisa logs para determinar em qual etapa o job está e detectar loops."""
    if not logs_text:
        return {
            "status": "unknown",
            "current_step": None,
            "last_activity": None,
            "possible_loop": False,
            "loop_indicators": [],
            "progress_steps": [],
        }
    
    # Etapas esperadas do processo (em ordem)
    expected_steps = [
        ("inicio", r"\[GENERATE_SCHEDULE\] Iniciando job_id="),
        ("leitura_demandas", r"\[GENERATE_SCHEDULE\] Chamando _demands_from_database"),
        ("demandas_encontradas", r"\[GENERATE_SCHEDULE\] Encontradas \d+ demandas"),
        ("solver_inicio", r"\[GENERATE_SCHEDULE\] Iniciando solver greedy"),
        ("solver_dia", r"\[SOLVE_GREEDY\] Dia \d+/\d+ concluído"),
        ("solver_concluido", r"\[GENERATE_SCHEDULE\] Solver greedy concluído"),
        ("extracao_inicio", r"\[GENERATE_SCHEDULE\] Iniciando extração de alocações individuais"),
        ("extracao_concluida", r"\[GENERATE_SCHEDULE\] Extraídas \d+ alocações individuais"),
        ("criacao_registros", r"\[GENERATE_SCHEDULE\] Criação de \d+ registros concluída"),
        ("commit", r"\[GENERATE_SCHEDULE\] Fazendo commit"),
        ("commit_concluido", r"\[GENERATE_SCHEDULE\] Commit concluído"),
        ("concluido", r"\[GENERATE_SCHEDULE\] Job \d+ CONCLUÍDO"),
    ]
    
    # Indicadores de loop
    loop_indicators = [
        (r"\[GREEDY_ALLOCATE\] POSSÍVEL LOOP DETECTADO", "Loop detectado no greedy_allocate"),
        (r"\[SOLVE_GREEDY\] Dia \d+/\d+ concluído", "Processamento repetitivo de dias"),
        (r"\[GREEDY_ALLOCATE\] Profissional .+ processado em .+s com \d+ iterações", "Muitas iterações por profissional"),
    ]
    
    progress_steps = []
    last_activity = None
    possible_loop = False
    loop_found = []
    
    lines = logs_text.split("\n")
    for line in lines:
        # Extrair timestamp se disponível
        timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        if timestamp_match:
            try:
                last_activity = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        # Verificar etapas de progresso
        for step_name, pattern in expected_steps:
            if re.search(pattern, line):
                progress_steps.append({
                    "step": step_name,
                    "line": line.strip(),
                    "timestamp": last_activity,
                })
                break
        
        # Verificar indicadores de loop
        for pattern, description in loop_indicators:
            if re.search(pattern, line):
                possible_loop = True
                loop_found.append({
                    "description": description,
                    "line": line.strip(),
                })
    
    # Determinar etapa atual
    current_step = None
    if progress_steps:
        current_step = progress_steps[-1]["step"]
    
    # Verificar se há repetição excessiva de mensagens (possível loop)
    message_counts = {}
    for line in lines:
        # Extrair mensagem principal (sem timestamp e valores variáveis)
        clean_line = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "", line)
        clean_line = re.sub(r"job_id=\d+", "job_id=XXX", clean_line)
        clean_line = re.sub(r"Job \d+", "Job XXX", clean_line)
        clean_line = re.sub(r"\d+\.\d+", "X.X", clean_line)  # Números decimais
        clean_line = re.sub(r"\d+", "N", clean_line)  # Outros números
        
        if clean_line.strip():
            message_counts[clean_line] = message_counts.get(clean_line, 0) + 1
    
    # Se alguma mensagem aparece mais de 50 vezes, pode ser loop
    for msg, count in message_counts.items():
        if count > 50:
            possible_loop = True
            loop_found.append({
                "description": f"Mensagem repetida {count} vezes",
                "line": msg[:100] + "..." if len(msg) > 100 else msg,
            })
    
    return {
        "status": "running" if current_step else "unknown",
        "current_step": current_step,
        "last_activity": last_activity,
        "possible_loop": possible_loop,
        "loop_indicators": loop_found,
        "progress_steps": progress_steps,
        "message_counts": {k: v for k, v in sorted(message_counts.items(), key=lambda x: x[1], reverse=True)[:5]},
    }


def check_running_jobs() -> List[Dict]:
    """Verifica todos os jobs em execução."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []
    
    try:
        engine = create_engine(database_url)
        with Session(engine) as session:
            jobs = session.exec(
                select(Job)
                .where(Job.status == JobStatus.RUNNING)
                .where(Job.job_type == JobType.GENERATE_SCHEDULE)
                .order_by(Job.started_at.desc())
            ).all()
            
            result = []
            now = utc_now()
            
            for job in jobs:
                elapsed = None
                if job.started_at:
                    elapsed = (now - job.started_at).total_seconds()
                
                time_since_update = None
                if job.updated_at:
                    time_since_update = (now - job.updated_at).total_seconds()
                
                result.append({
                    "id": job.id,
                    "tenant_id": job.tenant_id,
                    "started_at": job.started_at,
                    "updated_at": job.updated_at,
                    "elapsed_seconds": elapsed,
                    "time_since_update": time_since_update,
                    "input_data": job.input_data,
                })
            
            return result
    except Exception as e:
        print(f"[ERRO] Erro ao verificar jobs: {e}", file=sys.stderr)
        return []


def diagnose_job(job_id: int) -> Dict:
    """Faz diagnóstico completo de um job."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL não encontrada"}
    
    try:
        engine = create_engine(database_url)
        with Session(engine) as session:
            job = session.get(Job, job_id)
            
            if not job:
                return {"error": f"Job {job_id} não encontrado"}
            
            now = utc_now()
            elapsed = None
            time_since_update = None
            
            if job.started_at:
                elapsed = (now - job.started_at).total_seconds()
            if job.updated_at:
                time_since_update = (now - job.updated_at).total_seconds()
            
            # Buscar logs
            logs = get_docker_logs(tail=2000, job_id=job_id)
            progress = analyze_job_progress(logs, job_id) if logs else {}
            
            return {
                "job": {
                    "id": job.id,
                    "status": str(job.status),
                    "job_type": str(job.job_type),
                    "tenant_id": job.tenant_id,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    "elapsed_seconds": elapsed,
                    "time_since_update": time_since_update,
                    "error_message": job.error_message,
                },
                "progress": progress,
                "logs_available": logs is not None,
            }
    except Exception as e:
        return {"error": f"Erro ao diagnosticar job: {e}"}


def print_diagnosis(diagnosis: Dict, job_id: int):
    """Imprime diagnóstico formatado."""
    print("\n" + "="*70)
    print(f"DIAGNÓSTICO DO JOB {job_id}")
    print("="*70 + "\n")
    
    if "error" in diagnosis:
        print(f"[ERRO] {diagnosis['error']}\n")
        return
    
    job = diagnosis.get("job", {})
    progress = diagnosis.get("progress", {})
    
    # Informações do Job
    print("INFORMAÇÕES DO JOB:")
    print("-" * 70)
    print(f"Status: {job.get('status')}")
    print(f"Tipo: {job.get('job_type')}")
    print(f"Tenant ID: {job.get('tenant_id')}")
    
    if job.get("started_at"):
        print(f"Iniciado em: {job['started_at']}")
        elapsed = job.get("elapsed_seconds", 0)
        print(f"Tempo decorrido: {elapsed:.1f} segundos ({elapsed/60:.1f} minutos)")
        
        # Avisos de tempo
        if elapsed > 600:  # 10 minutos
            print(f"\n[ALERTA] Job rodando há mais de 10 minutos - pode estar travado!")
        elif elapsed > 300:  # 5 minutos
            print(f"\n[AVISO] Job rodando há mais de 5 minutos - verifique logs")
    else:
        print("Iniciado em: N/A")
    
    if job.get("updated_at"):
        time_since_update = job.get("time_since_update", 0)
        print(f"Última atualização: {job['updated_at']} ({time_since_update:.1f}s atrás)")
        
        # Aviso se não atualizou há muito tempo
        if time_since_update > 300:  # 5 minutos
            print(f"\n[ALERTA] Job não atualiza há mais de 5 minutos - provavelmente travado!")
    else:
        print("Última atualização: N/A")
    
    if job.get("error_message"):
        print(f"\nMensagem de erro: {job['error_message']}")
    
    # Progresso
    print("\n" + "="*70)
    print("PROGRESSO DO JOB:")
    print("-" * 70)
    
    if not diagnosis.get("logs_available"):
        print("[AVISO] Logs não disponíveis (Docker pode não estar acessível)")
    else:
        current_step = progress.get("current_step")
        if current_step:
            step_names = {
                "inicio": "Início do processamento",
                "leitura_demandas": "Lendo demandas do banco",
                "demandas_encontradas": "Demandas encontradas",
                "solver_inicio": "Iniciando solver",
                "solver_dia": "Processando dias (solver)",
                "solver_concluido": "Solver concluído",
                "extracao_inicio": "Extraindo alocações individuais",
                "extracao_concluida": "Extração concluída",
                "criacao_registros": "Criando registros",
                "commit": "Fazendo commit no banco",
                "commit_concluido": "Commit concluído",
                "concluido": "Job concluído com sucesso",
            }
            print(f"Etapa atual: {step_names.get(current_step, current_step)}")
        else:
            print("Etapa atual: Não identificada nos logs")
        
        progress_steps = progress.get("progress_steps", [])
        if progress_steps:
            print(f"\nEtapas identificadas: {len(progress_steps)}")
            print("Últimas 5 etapas:")
            for step in progress_steps[-5:]:
                timestamp = step.get("timestamp")
                timestamp_str = timestamp.strftime("%H:%M:%S") if timestamp else "N/A"
                print(f"  [{timestamp_str}] {step['step']}")
        
        last_activity = progress.get("last_activity")
        if last_activity:
            time_since_activity = (datetime.now() - last_activity).total_seconds()
            print(f"\nÚltima atividade nos logs: {time_since_activity:.1f} segundos atrás")
            if time_since_activity > 300:
                print(f"[ALERTA] Sem atividade nos logs há mais de 5 minutos!")
    
    # Detecção de loops
    possible_loop = progress.get("possible_loop", False)
    if possible_loop:
        print("\n" + "="*70)
        print("[ALERTA] POSSÍVEL LOOP DETECTADO!")
        print("-" * 70)
        
        loop_indicators = progress.get("loop_indicators", [])
        for indicator in loop_indicators:
            print(f"  - {indicator['description']}")
            print(f"    {indicator['line'][:100]}...")
    
    # Diagnóstico e recomendações
    print("\n" + "="*70)
    print("DIAGNÓSTICO:")
    print("-" * 70)
    
    issues = []
    recommendations = []
    
    elapsed = job.get("elapsed_seconds", 0)
    time_since_update = job.get("time_since_update", 0)
    
    if elapsed > 600:
        issues.append("Job rodando há mais de 10 minutos")
        recommendations.append("1. Verifique se o worker está processando (docker-compose logs -f worker)")
        recommendations.append("2. Se estiver travado, cancele: python script_cancelar_job.py {job_id} --force")
        recommendations.append("3. Reinicie o worker: docker-compose restart worker")
    
    if time_since_update > 300:
        issues.append("Job não atualiza há mais de 5 minutos")
        recommendations.append("1. Job provavelmente travado - cancele e tente novamente")
    
    if possible_loop:
        issues.append("Possível loop infinito detectado")
        recommendations.append("1. Verifique os logs para identificar onde está o loop")
        recommendations.append("2. Cancele o job: python script_cancelar_job.py {job_id} --force")
        recommendations.append("3. Verifique o código do solver/alocação")
    
    if not diagnosis.get("logs_available"):
        issues.append("Logs não disponíveis")
        recommendations.append("1. Verifique se o Docker está rodando")
        recommendations.append("2. Tente: docker-compose logs worker")
    
    if not issues:
        print("[OK] Job parece estar executando normalmente")
        if current_step:
            print(f"   Etapa atual: {step_names.get(current_step, current_step)}")
    else:
        print("[PROBLEMAS ENCONTRADOS]:")
        for issue in issues:
            print(f"  - {issue}")
        
        if recommendations:
            print("\n[RECOMENDAÇÕES]:")
            for rec in recommendations:
                print(f"  {rec}")
    
    print("\n" + "="*70 + "\n")


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        # Sem argumentos: listar todos os jobs em execução
        print("Buscando jobs em execução...\n")
        running_jobs = check_running_jobs()
        
        if not running_jobs:
            print("[OK] Nenhum job GENERATE_SCHEDULE em execução no momento.\n")
            return 0
        
        print(f"Encontrados {len(running_jobs)} job(s) em execução:\n")
        for job_info in running_jobs:
            job_id = job_info["id"]
            elapsed = job_info.get("elapsed_seconds", 0)
            print(f"  Job {job_id}: rodando há {elapsed:.1f}s ({elapsed/60:.1f} min)")
        
        print("\nPara diagnosticar um job específico, use:")
        print(f"  python script_diagnostico_job_execucao.py <job_id>")
        print(f"\nExemplo:")
        print(f"  python script_diagnostico_job_execucao.py {running_jobs[0]['id']}")
        return 0
    
    try:
        job_id = int(sys.argv[1])
    except ValueError:
        print(f"[ERRO] Job ID inválido: {sys.argv[1]}")
        print("\nUso: python script_diagnostico_job_execucao.py [job_id]")
        print("\nSe não fornecer job_id, lista todos os jobs em execução.")
        return 1
    
    print("Fazendo diagnóstico do job...\n")
    diagnosis = diagnose_job(job_id)
    print_diagnosis(diagnosis, job_id)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
