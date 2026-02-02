from __future__ import annotations

import logging
import os
import tempfile
from datetime import timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.db.session import engine
from app.model.base import utc_now
from app.model.demand import Demand, ScheduleStatus
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.member import Member, MemberStatus
from app.model.tenant import Tenant
from app.storage.client import S3Client

from demand.read import extract_demand
from strategy.greedy.solve import solve_greedy

logger = logging.getLogger(__name__)


_MAX_STALE_WINDOW = timedelta(hours=1)


def _was_cancelled(session: Session, job: Job) -> bool:
    """
    Verifica se o job foi cancelado (status FAILED) durante a execução.
    Faz um refresh no banco para obter o status mais recente.
    Usado para evitar sobrescrever status FAILED com COMPLETED.
    """
    session.refresh(job)
    return job.status == JobStatus.FAILED


def _stale_window_for(session: Session, *, tenant_id: int, job_type: JobType) -> timedelta:
    """
    Janela dinâmica:
      - 10x a média de duração dos últimos 10 jobs COMPLETED do mesmo tipo (tenant + job_type)
      - fallback: 1h se não existir média
      - teto: 1h em qualquer situação
    """
    rows = session.exec(
        select(Job)
        .where(
            Job.tenant_id == tenant_id,
            Job.job_type == job_type,
            Job.status == JobStatus.COMPLETED,
            Job.started_at.is_not(None),  # type: ignore[attr-defined]
            Job.completed_at.is_not(None),
        )
        .order_by(Job.completed_at.desc())  # type: ignore[union-attr]
        .limit(10)
    ).all()

    durations: list[float] = []
    for j in rows:
        if not j.started_at or not j.completed_at:
            continue
        durations.append((j.completed_at - j.started_at).total_seconds())

    if not durations:
        return _MAX_STALE_WINDOW

    avg_seconds = sum(durations) / len(durations)
    window = timedelta(seconds=avg_seconds * 10)
    return min(window, _MAX_STALE_WINDOW)


async def ping_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Job fake para validar fila/worker.
    Atualiza status no banco e grava um payload simples em result_data.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        try:
            job.result_data = {"pong": True}
            # Verificar se foi cancelado antes de marcar como COMPLETED
            if _was_cancelled(session, job):
                return {"ok": False, "error": "job_cancelled", "job_id": job.id}
            job.status = JobStatus.COMPLETED
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": str(e), "job_id": job.id}


def _safe_error_message(e: Exception, max_len: int = 500) -> str:
    msg = f"{type(e).__name__}: {str(e)}".strip()
    return msg[:max_len]


def _parse_vacation_for_solver(
    vacation_iso: list[list[str]],
    period_start_date,
    tenant_tz: ZoneInfo,
) -> tuple[list[tuple[float, float]], list[tuple[int, int]]]:
    """
    Converte vacation de ISO datetime strings para o formato do solver.

    Se o par [início, fim] cai no mesmo dia civil (timezone do tenant): bloco horário
    (hora_inicio, hora_fim) -> vacation.

    Se abrange vários dias: dias inteiros (dia_inicio, dia_fim) -> vacation_days.

    Args:
        vacation_iso: Lista de pares [início, fim] em ISO datetime
        period_start_date: Data de início do período da escala (date)
        tenant_tz: Timezone do tenant para converter horários

    Returns:
        (vacation, vacation_days): blocos em horas e intervalos em dias
    """
    from datetime import datetime

    vacation: list[tuple[float, float]] = []
    vacation_days: list[tuple[int, int]] = []
    seen_hours: set[tuple[float, float]] = set()

    for pair in vacation_iso or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        try:
            start_dt = datetime.fromisoformat(str(pair[0]).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(pair[1]).replace("Z", "+00:00"))
            start_local = start_dt.astimezone(tenant_tz)
            end_local = end_dt.astimezone(tenant_tz)

            if start_local.date() == end_local.date():
                # Mesmo dia: bloco horário (compatível com turna/profissionais.json)
                h_start = start_local.hour + start_local.minute / 60.0 + start_local.second / 3600.0
                h_end = end_local.hour + end_local.minute / 60.0 + end_local.second / 3600.0
                key = (round(h_start, 2), round(h_end, 2))
                if key not in seen_hours:
                    seen_hours.add(key)
                    vacation.append((h_start, h_end))
            else:
                # Vários dias: dias inteiros
                start_day = (start_local.date() - period_start_date).days + 1
                # end exclusivo: último dia = end.date() - 1 dia se end for meia-noite
                end_day = (end_local.date() - period_start_date).days
                if end_day >= 1:
                    vacation_days.append((max(1, start_day), end_day))
        except (ValueError, TypeError, AttributeError):
            continue
    return (vacation, vacation_days)


def _load_pros_from_member_table(
    session: Session,
    tenant_id: int,
    period_start_date=None,
) -> list[dict]:
    """
    Carrega profissionais da tabela member para o tenant.
    Usa diretamente as colunas can_peds, sequence, vacation do model Member.

    Retorna lista no formato esperado pelo solver:
    - id: identificador = str(member.id) para lookup e gravação de demand.member_id
    - name: nome (string)
    - sequence: ordem de prioridade (int)
    - can_peds: se pode atender pediatria (bool)
    - vacation: lista de tuplas (hora_inicio, hora_fim) — blocos horários; vazio para member (usa vacation_days)
    - vacation_days: lista de tuplas (dia_inicio, dia_fim) — dias do período em férias

    Args:
        session: Sessão do banco
        tenant_id: ID do tenant
        period_start_date: Data de início do período (para converter vacation para dias relativos).
                           Se None, vacation será lista vazia.

    Filtra por tenant_id, status ACTIVE e sequence > 0 (apenas membros com ordem de prioridade).
    """
    logger.info(f"[LOAD_PROFESSIONALS] Carregando profissionais do tenant_id={tenant_id}")
    rows = session.exec(
        select(Member)
        .where(
            Member.tenant_id == tenant_id,
            Member.status == MemberStatus.ACTIVE,
            Member.sequence > 0,
        )
    ).all()

    tenant = session.get(Tenant, tenant_id)
    tenant_tz = ZoneInfo(tenant.timezone) if tenant and tenant.timezone else ZoneInfo("UTC")

    pros: list[dict] = []
    for m in rows:
        pro_id = str(m.id)
        name = (m.label or m.name or pro_id).strip()

        # Converter vacation: mesmo dia -> blocos horários; vários dias -> vacation_days
        if period_start_date is not None:
            vacation_hours, vacation_days = _parse_vacation_for_solver(
                m.vacation, period_start_date, tenant_tz
            )
        else:
            vacation_hours = []
            vacation_days = []

        pros.append({
            "id": pro_id,
            "name": name,
            "sequence": m.sequence,
            "can_peds": m.can_peds,
            "vacation": vacation_hours,
            "vacation_days": vacation_days,
            "member_db_id": m.id,
        })

    pros.sort(key=lambda p: p["sequence"])
    logger.info(f"[LOAD_PROFESSIONALS] {len(pros)} profissionais carregados")
    return pros


def _extract_individual_allocations(
    per_day: list[dict],
    pros_by_sequence: list[dict],
) -> list[dict]:
    """
    Extrai alocações individuais do resultado do solver.

    Transforma a estrutura agregada (per_day) em uma lista de alocações individuais,
    onde cada alocação representa um profissional alocado a uma demanda específica.

    Args:
        per_day: Lista de dicts com estrutura do solver (day_number, pros_for_day, assigned_demands_by_pro, etc.)
        pros_by_sequence: Lista de profissionais (para obter nomes completos)

    Returns:
        Lista de dicts, cada um representando uma alocação individual:
        {
            "member": str,            # nome do profissional
            "member_id": str,         # ID do profissional
            "id": str,               # ID da demanda
            "day": int,              # dia (1..N)
            "start": float,          # hora início
            "end": float,            # hora fim
            "is_pediatric": bool,
        }
    """
    allocations = []

    # Criar mapa profissional_id -> nome completo e member_db_id (busca em pros_by_sequence primeiro)
    pro_id_to_name: dict[str, str] = {}
    pro_id_to_member_db_id: dict[str, int] = {}
    for pro in pros_by_sequence:
        pro_id = str(pro.get("id") or "").strip()
        pro_name = str(pro.get("name") or pro_id).strip()
        if pro_id:
            pro_id_to_name[pro_id] = pro_name
        member_db_id = pro.get("member_db_id")
        if member_db_id is not None and isinstance(member_db_id, int):
            pro_id_to_member_db_id[pro_id] = member_db_id

    for day_item in per_day:
        if not isinstance(day_item, dict):
            continue

        day_number = day_item.get("day_number", 0)
        if day_number <= 0:
            continue

        pros_for_day = day_item.get("pros_for_day", [])
        assigned_demands_by_pro = day_item.get("assigned_demands_by_pro", {})

        logger.debug(f"[EXTRACT_ALLOCATIONS] Dia {day_number}: {len(pros_for_day)} profissionais, {len(assigned_demands_by_pro)} profissionais com alocações")

        # Atualizar mapa com profissionais do dia (pode ter nomes diferentes)
        for pro in pros_for_day:
            if not isinstance(pro, dict):
                continue
            # pro_id pode ser string ou outro tipo - normalizar para string
            pro_id_raw = pro.get("id")
            pro_id = str(pro_id_raw).strip() if pro_id_raw is not None else ""
            if pro_id:
                # Priorizar nome do pros_for_day, fallback para pros_by_sequence
                pro_name = str(pro.get("name") or pro_id_to_name.get(pro_id, pro_id)).strip()
                pro_id_to_name[pro_id] = pro_name

        # Iterar sobre alocações por profissional
        for pro_id_raw, demand_list in assigned_demands_by_pro.items():
            # Normalizar pro_id para string (pode vir como int ou outro tipo)
            pro_id = str(pro_id_raw).strip() if pro_id_raw is not None else ""
            if not pro_id:
                logger.debug(f"[EXTRACT_ALLOCATIONS] pro_id_raw inválido: {pro_id_raw} (tipo: {type(pro_id_raw)})")
                continue

            if not isinstance(demand_list, list):
                logger.warning(f"[EXTRACT_ALLOCATIONS] Demand list não é lista para pro_id={pro_id}, tipo={type(demand_list)}, valor={demand_list}")
                continue

            # Buscar nome do profissional (tentar com pro_id como string e também como tipo original)
            member_name = pro_id_to_name.get(pro_id)
            if member_name is None:
                # Tentar buscar com o valor original também
                member_name = pro_id_to_name.get(str(pro_id_raw), pro_id)
            logger.debug(f"[EXTRACT_ALLOCATIONS] Profissional {pro_id} ({member_name}): {len(demand_list)} demandas")

            for demand in demand_list:
                if not isinstance(demand, dict):
                    continue

                # Extrair dados da demanda
                demand_id = demand.get("id")
                if not demand_id:
                    logger.debug(f"[EXTRACT_ALLOCATIONS] Demanda sem ID, pulando: {demand}")
                    continue

                member_db_id = pro_id_to_member_db_id.get(pro_id)
                allocation = {
                    "member": member_name,
                    # member_id no JSON = PK do member (int) quando temos member_db_id; evita gravar nome
                    "member_id": member_db_id if member_db_id is not None else pro_id,
                    "member_db_id": member_db_id,  # PK member para demand.member_id
                    "id": str(demand_id),
                    "day": int(day_number),
                    "start": float(demand.get("start", 0)),
                    "end": float(demand.get("end", 0)),
                    "is_pediatric": bool(demand.get("is_pediatric", False)),
                    "demand_id": demand.get("demand_id"),  # ID do registro Demand
                    "hospital_id": demand.get("hospital_id"),  # hospital_id da demanda (para referência)
                }
                allocations.append(allocation)
                logger.debug(f"[EXTRACT_ALLOCATIONS] Alocação criada: {allocation['member']} - Dia {allocation['day']} - {allocation['id']} - Demand {allocation['demand_id']}")

    logger.info(f"[EXTRACT_ALLOCATIONS] Total de alocações extraídas: {len(allocations)}")
    return allocations


def _demands_from_extract_result(result_data: dict, *, period_start_at, period_end_at) -> tuple[list[dict], int]:
    """
    Converte `result_data` do EXTRACT_DEMAND para o formato esperado pelos solvers:
      - day: 1..N
      - start/end: horas em float (ex.: 9.5 = 09:30)
      - is_pediatric: bool (default False)
    """
    from datetime import datetime

    demands_raw = (result_data or {}).get("demands") or []
    if not isinstance(demands_raw, list):
        raise RuntimeError("result_data.demand list inválido")

    # Assume timestamps com offset/Z (diretiva).
    start_date = period_start_at.date()
    end_date = period_end_at.date()
    days = (end_date - start_date).days
    if days <= 0:
        raise RuntimeError("Período inválido: period_end_at deve ser maior que period_start_at")

    def parse_dt(s: str) -> datetime:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    out: list[dict] = []
    for i, d in enumerate(demands_raw):
        if not isinstance(d, dict):
            continue
        st = parse_dt(str(d.get("start_time")))
        en = parse_dt(str(d.get("end_time")))
        if en <= st:
            continue

        # Dia relativo ao period_start_at (mesma data do start_time).
        day_idx = (st.date() - start_date).days + 1
        if day_idx < 1 or day_idx > days:
            continue

        start_h = st.hour + (st.minute / 60.0)
        end_h = en.hour + (en.minute / 60.0)
        did = str(d.get("room") or f"D{i+1}")
        out.append(
            {
                "id": did,
                "day": int(day_idx),
                "start": float(start_h),
                "end": float(end_h),
                "is_pediatric": bool(d.get("is_pediatric") or False),
            }
        )

    return out, days


def _demands_from_database(
    session: Session,
    *,
    tenant_id: int,
    period_start_at,
    period_end_at,
    filter_hospital_id: Optional[int] = None,
) -> tuple[list[dict], int]:
    """
    Lê demandas do banco de dados (tabela demand) e converte para o formato esperado pelos solvers:
      - day: 1..N
      - start/end: horas em float (ex.: 9.5 = 09:30)
      - is_pediatric: bool (default False)

    Filtra por tenant_id e período (start_time dentro do intervalo).
    Opcionalmente filtra por hospital_id (filter_hospital_id).
    Usa o timezone da clínica para calcular dias e horas relativas.
    """
    from datetime import datetime

    logger.debug(f"[_demands_from_database] Iniciando - tenant_id={tenant_id}, period_start_at={period_start_at}, period_end_at={period_end_at}, filter_hospital_id={filter_hospital_id}")

    # Buscar timezone do tenant
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise RuntimeError(f"Tenant não encontrado (id={tenant_id})")

    tenant_tz = ZoneInfo(tenant.timezone)
    logger.debug(f"[_demands_from_database] Timezone do tenant: {tenant.timezone}")

    # Converter períodos para timezone da clínica para cálculo de datas
    period_start_local = period_start_at.astimezone(tenant_tz)
    period_end_local = period_end_at.astimezone(tenant_tz)
    logger.debug(f"[_demands_from_database] Período no timezone local: {period_start_local} até {period_end_local}")

    # Validar período usando datas no timezone da clínica
    start_date = period_start_local.date()
    end_date = period_end_local.date()
    days = (end_date - start_date).days
    logger.debug(f"[_demands_from_database] start_date={start_date}, end_date={end_date}, days={days}")

    if days <= 0:
        raise RuntimeError(f"Período inválido: period_end_at deve ser maior que period_start_at (days={days})")

    # Buscar demandas do banco no período
    # Filtra por tenant_id (segurança multi-tenant) e start_time dentro do intervalo
    # Opcionalmente filtra por hospital_id (filter_hospital_id)
    # As datas de comparação já estão em UTC (timestamptz), então a comparação direta funciona
    query = (
        select(Demand)
        .where(
            Demand.tenant_id == tenant_id,
            Demand.start_time >= period_start_at,
            Demand.start_time < period_end_at,
        )
    )
    if filter_hospital_id is not None:
        query = query.where(Demand.hospital_id == filter_hospital_id)
    query = query.order_by(Demand.start_time)
    demands_db = session.exec(query).all()

    if not demands_db:
        raise RuntimeError("Nenhuma demanda encontrada no período informado")

    out: list[dict] = []
    logger.debug(f"[_demands_from_database] Processando {len(demands_db)} demandas do banco")

    for i, d in enumerate(demands_db):
        # Converter para timezone da clínica para cálculos de dia e hora
        st_local = d.start_time.astimezone(tenant_tz)
        en_local = d.end_time.astimezone(tenant_tz)

        if en_local <= st_local:
            logger.warning(f"[_demands_from_database] Demanda {i} ignorada: end_time <= start_time")
            continue

        # Dia relativo ao period_start_at usando data no timezone da clínica
        day_idx = (st_local.date() - start_date).days + 1
        logger.debug(f"[_demands_from_database] Demanda {i}: day_idx={day_idx} (st_local.date()={st_local.date()}, start_date={start_date})")

        if day_idx is None:
            raise RuntimeError(f"day_idx é None para demanda {i} (st_local.date()={st_local.date()}, start_date={start_date})")

        if day_idx < 1 or day_idx > days:
            logger.warning(f"[_demands_from_database] Demanda {i} ignorada: day_idx={day_idx} fora do intervalo [1, {days}]")
            continue

        # Converter para horas float usando hora no timezone da clínica (ex.: 9.5 = 09:30)
        start_h = st_local.hour + (st_local.minute / 60.0) + (st_local.second / 3600.0)
        end_h = en_local.hour + (en_local.minute / 60.0) + (en_local.second / 3600.0)

        # ID da demanda: usar room se disponível, senão usar procedure ou índice
        did = str(d.room or d.procedure or f"D{i+1}")

        try:
            day_int = int(day_idx)
        except (ValueError, TypeError) as e:
            raise RuntimeError(
                f"Erro ao converter day_idx para int: day_idx={day_idx} (tipo: {type(day_idx)}), "
                f"st_local.date()={st_local.date()}, start_date={start_date}, days={days}. "
                f"Erro: {str(e)}"
            ) from e

        out.append(
            {
                "id": did,
                "day": day_int,
                "start": float(start_h),
                "end": float(end_h),
                "is_pediatric": bool(d.is_pediatric),
                "demand_id": d.id,  # ID do registro Demand
                "hospital_id": d.hospital_id,  # hospital_id da demanda (para referência)
            }
        )

    logger.info(f"[_demands_from_database] Retornando {len(out)} demandas processadas em {days} dias")
    return out, days


async def generate_schedule_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Gera escala e atualiza Demand (schedule_status, schedule_result_data, etc.).

    Suporta dois modos:
    - "from_demands": Lê demandas da tabela demand; atualiza cada Demand com resultado da alocação.
    - "from_extract": Lê demandas de Job de extração; não persiste em Demand (sem demand_id); apenas job.result_data mínimo.

    MVP: usa solver greedy.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        try:
            job_start_time = utc_now()
            elapsed_seconds = 0
            logger.info(f"[GENERATE_SCHEDULE] Iniciando job_id={job_id}, tenant_id={job.tenant_id} às {job_start_time.isoformat()}")
            input_data = job.input_data or {}
            logger.debug(f"[GENERATE_SCHEDULE] input_data keys: {list(input_data.keys()) if input_data else 'None'}")
            logger.debug(f"[GENERATE_SCHEDULE] input_data completo: {input_data}")

            mode = str(input_data.get("mode") or "from_extract").strip().lower()
            allocation_mode = str(input_data.get("allocation_mode") or "greedy").strip().lower()
            logger.debug(f"[GENERATE_SCHEDULE] mode={mode}, allocation_mode={allocation_mode}")

            if allocation_mode != "greedy":
                raise RuntimeError("allocation_mode não suportado no MVP (apenas greedy)")

            schedule_name = None
            schedule_period_start_at = None
            schedule_period_end_at = None
            schedule_version_number = 1
            extract_job_id = None

            # Obter período (necessário antes de carregar profissionais para converter vacation)
            from datetime import datetime
            period_start_at = input_data.get("period_start_at")
            period_end_at = input_data.get("period_end_at")

            if not period_start_at or not period_end_at:
                raise RuntimeError("period_start_at e period_end_at são obrigatórios")

            if isinstance(period_start_at, str):
                period_start_at = datetime.fromisoformat(period_start_at.replace("Z", "+00:00"))
            if isinstance(period_end_at, str):
                period_end_at = datetime.fromisoformat(period_end_at.replace("Z", "+00:00"))

            schedule_period_start_at = period_start_at
            schedule_period_end_at = period_end_at

            # Obter timezone do tenant para converter datas
            tenant = session.get(Tenant, job.tenant_id)
            if not tenant:
                raise RuntimeError(f"Tenant não encontrado (id={job.tenant_id})")
            tenant_tz = ZoneInfo(tenant.timezone)
            period_start_date = period_start_at.astimezone(tenant_tz).date()

            logger.debug(f"[GENERATE_SCHEDULE] period_start_at: {period_start_at}, period_start_date: {period_start_date}")

            # Profissionais: no modo from_demands sempre carregar da tabela member (para ter member_db_id e gravar demand.member_id)
            # No modo from_extract usa payload se enviado, senão carrega da tabela
            if mode == "from_demands":
                pros_by_sequence = _load_pros_from_member_table(session, job.tenant_id, period_start_date)
            else:
                pros_by_sequence = input_data.get("pros_by_sequence")
                if pros_by_sequence is None:
                    pros_by_sequence = _load_pros_from_member_table(session, job.tenant_id, period_start_date)
            if not isinstance(pros_by_sequence, list) or not pros_by_sequence:
                raise RuntimeError("Nenhum profissional encontrado para o tenant")

            # Carregar demandas conforme o modo
            if mode == "from_demands":
                logger.info(f"[GENERATE_SCHEDULE] Modo 'from_demands' - lendo demandas do banco (sem registro mestre)")

                # Obter dados do input_data (não há registro mestre no modo from_demands)
                # O worker atualiza cada Demand com o resultado da sua alocação.
                schedule_name = input_data.get("name") or f"Escala Job {job_id}"
                schedule_version_number = int(input_data.get("version_number") or 1)

                # Obter filtro de hospital (opcional)
                filter_hospital_id = input_data.get("filter_hospital_id")

                logger.info(f"[GENERATE_SCHEDULE] Chamando _demands_from_database com período: {period_start_at} até {period_end_at}, filter_hospital_id={filter_hospital_id}")
                elapsed_seconds = (utc_now() - job_start_time).total_seconds()
                logger.info(f"[GENERATE_SCHEDULE] Tempo decorrido até leitura de demandas: {elapsed_seconds:.2f}s")
                demand_list, days = _demands_from_database(
                    session,
                    tenant_id=job.tenant_id,
                    period_start_at=period_start_at,
                    period_end_at=period_end_at,
                    filter_hospital_id=filter_hospital_id,
                )
                elapsed_seconds = (utc_now() - job_start_time).total_seconds()
                logger.info(f"[GENERATE_SCHEDULE] Encontradas {len(demand_list)} demandas em {days} dias. Tempo decorrido: {elapsed_seconds:.2f}s")
            else:
                # Modo from_extract: ler de job de extração (período já parseado acima)
                schedule_name = input_data.get("name") or f"Escala Job {job_id}"
                schedule_version_number = int(input_data.get("version_number") or 1)

                extract_job_id_raw = input_data.get("extract_job_id")
                if extract_job_id_raw is None:
                    raise RuntimeError("extract_job_id ausente no input_data para modo 'from_extract'")
                try:
                    extract_job_id = int(extract_job_id_raw)
                    logger.debug(f"[GENERATE_SCHEDULE] extract_job_id: {extract_job_id}")
                except (ValueError, TypeError) as e:
                    raise RuntimeError(f"extract_job_id inválido: {extract_job_id_raw}") from e

                extract_job = session.get(Job, extract_job_id)
                if not extract_job:
                    raise RuntimeError(f"Job de extração não encontrado (id={extract_job_id})")
                if extract_job.tenant_id != job.tenant_id:
                    raise RuntimeError("Acesso negado (tenant mismatch)")
                if extract_job.status != JobStatus.COMPLETED or not isinstance(extract_job.result_data, dict):
                    raise RuntimeError("Job de extração não está COMPLETED (ou result_data ausente)")

                demand_list, days = _demands_from_extract_result(
                    extract_job.result_data,
                    period_start_at=schedule_period_start_at,
                    period_end_at=schedule_period_end_at,
                )

            if not demand_list:
                raise RuntimeError("Nenhuma demanda dentro do período informado")

            logger.info(f"[GENERATE_SCHEDULE] Iniciando solver greedy: {len(demand_list)} demandas, {days} dias, {len(pros_by_sequence)} profissionais")
            solve_start_time = utc_now()
            per_day, total_cost = solve_greedy(
                demands=demand_list,
                pros_by_sequence=pros_by_sequence,
                days=days,
                unassigned_penalty=1000,
                ped_unassigned_extra_penalty=1000,
                base_shift=0,
            )
            solve_duration = (utc_now() - solve_start_time).total_seconds()
            elapsed_seconds = (utc_now() - job_start_time).total_seconds()
            logger.info(f"[GENERATE_SCHEDULE] Solver greedy concluído em {solve_duration:.2f} segundos. Total cost: {total_cost}, Dias processados: {len(per_day)}. Tempo total decorrido: {elapsed_seconds:.2f}s")

            # Extrair alocações individuais
            extract_start_time = utc_now()
            logger.info(f"[GENERATE_SCHEDULE] Iniciando extração de alocações individuais. per_day tem {len(per_day)} dias")

            # Log detalhado da estrutura antes da extração
            total_assigned = 0
            for idx, day_item in enumerate(per_day):
                if isinstance(day_item, dict):
                    assigned = day_item.get("assigned_demands_by_pro", {})
                    day_num = day_item.get("day_number", idx + 1)
                    logger.debug(f"[GENERATE_SCHEDULE] Dia {day_num}: assigned_demands_by_pro tem {len(assigned)} profissionais com alocações")
                    for pro_id, demands_list in assigned.items():
                        if isinstance(demands_list, list):
                            total_assigned += len(demands_list)
                            logger.debug(f"[GENERATE_SCHEDULE]   - Profissional {pro_id} (tipo: {type(pro_id)}): {len(demands_list)} demandas")
                        else:
                            logger.warning(f"[GENERATE_SCHEDULE]   - Profissional {pro_id}: demands_list não é lista (tipo: {type(demands_list)})")
            logger.info(f"[GENERATE_SCHEDULE] Total de demandas alocadas encontradas: {total_assigned}")

            individual_allocations = _extract_individual_allocations(
                per_day=per_day,
                pros_by_sequence=pros_by_sequence,
            )

            extract_duration = (utc_now() - extract_start_time).total_seconds()
            elapsed_seconds = (utc_now() - job_start_time).total_seconds()
            logger.info(f"[GENERATE_SCHEDULE] Extraídas {len(individual_allocations)} alocações individuais em {extract_duration:.2f}s. Tempo total decorrido: {elapsed_seconds:.2f}s")

            if len(individual_allocations) == 0:
                logger.warning(f"[GENERATE_SCHEDULE] Nenhuma alocação individual extraída! Total de demandas alocadas era {total_assigned}")

            # Atualizar Demand com resultado da alocação (apenas quando allocation tem demand_id, ex.: from_demands)
            updated_demand_count = 0
            create_records_start_time = utc_now()
            for idx, allocation in enumerate(individual_allocations):
                if (idx + 1) % 100 == 0:
                    logger.debug(f"[GENERATE_SCHEDULE] Atualizando demanda {idx + 1}/{len(individual_allocations)}")
                allocation_with_metadata = {
                    **allocation,
                    "metadata": {
                        "allocation_mode": "greedy",
                        "total_cost": total_cost,
                        "mode": mode,
                        "generated_at": now.isoformat(),
                        "job_id": job.id,
                        "sequence": idx + 1,
                    }
                }
                if extract_job_id is not None:
                    allocation_with_metadata["metadata"]["extract_job_id"] = extract_job_id

                allocation_demand_id = allocation.get("demand_id")
                if not allocation_demand_id:
                    logger.warning(f"[GENERATE_SCHEDULE] Alocação {idx + 1} sem demand_id, pulando")
                    continue

                demand_row = session.get(Demand, allocation_demand_id)
                if not demand_row or demand_row.tenant_id != job.tenant_id:
                    logger.warning(f"[GENERATE_SCHEDULE] Demand {allocation_demand_id} não encontrada ou tenant mismatch, pulando")
                    continue

                member_db_id = allocation.get("member_db_id")
                demand_row.schedule_status = ScheduleStatus.DRAFT
                demand_row.schedule_name = f"{schedule_name} - {allocation['member']} - Dia {allocation['day']}"
                demand_row.schedule_version_number = schedule_version_number
                demand_row.schedule_result_data = allocation_with_metadata
                demand_row.generated_at = now
                demand_row.job_id = job.id
                demand_row.member_id = member_db_id  # member atribuído no cálculo da escala
                demand_row.updated_at = now
                session.add(demand_row)
                if member_db_id is None:
                    logger.warning(
                        f"[GENERATE_SCHEDULE] demand_id={allocation_demand_id} sem member_db_id na alocação "
                        f"(pro_id na alocação: {allocation.get('member_id')!r})"
                    )
                updated_demand_count += 1

            create_records_duration = (utc_now() - create_records_start_time).total_seconds()
            logger.info(f"[GENERATE_SCHEDULE] Atualização de {updated_demand_count} demandas concluída em {create_records_duration:.2f} segundos")

            if _was_cancelled(session, job):
                logger.warning(f"[GENERATE_SCHEDULE] Job {job.id} foi cancelado durante execução")
                return {"ok": False, "error": "job_cancelled", "job_id": job.id}
            job.status = JobStatus.COMPLETED
            job.completed_at = utc_now()
            job.updated_at = job.completed_at
            job.result_data = {"allocation_count": len(individual_allocations)}
            job.error_message = None
            session.add(job)

            logger.info(f"[GENERATE_SCHEDULE] Fazendo commit: {updated_demand_count} demandas atualizadas")
            commit_start_time = utc_now()
            session.commit()
            commit_duration = (utc_now() - commit_start_time).total_seconds()
            logger.info(f"[GENERATE_SCHEDULE] Commit concluído em {commit_duration:.2f} segundos")

            session.refresh(job)
            total_duration = (utc_now() - job_start_time).total_seconds()
            logger.info(f"[GENERATE_SCHEDULE] Job {job_id} CONCLUÍDO com sucesso em {total_duration:.2f} segundos")
            return {"ok": True, "job_id": job.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = _safe_error_message(e)
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": job.error_message, "job_id": job.id}

async def extract_demand_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Extrai demandas (OpenAI) a partir de um File (PDF/JPEG/PNG) já armazenado no S3/MinIO.
    Persistência:
      - `Job.result_data`: JSON com o resultado
      - `Job.status`: RUNNING -> COMPLETED/FAILED
      - `Job.completed_at`: UTC
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        tmp_path: str | None = None
        try:
            input_data = job.input_data or {}
            file_id = int(input_data.get("file_id"))

            file_model = session.get(File, file_id)
            if not file_model:
                raise RuntimeError(f"File não encontrado (file_id={file_id})")
            if file_model.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")

            # Carregar hospital via file.hospital_id
            from app.model.hospital import Hospital
            hospital = session.get(Hospital, file_model.hospital_id)
            if not hospital:
                raise RuntimeError(f"Hospital não encontrado (hospital_id={file_model.hospital_id})")
            if hospital.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (hospital tenant mismatch)")

            # Usar prompt do hospital
            hospital_prompt = hospital.prompt

            filename = file_model.filename or "file"
            _, ext = os.path.splitext(filename)
            ext = (ext or "").lower()
            if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
                # Fallback: o extractor suporta PDF/JPEG/PNG; assume PDF quando extensão desconhecida.
                ext = ".pdf"

            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp_path = tmp.name

            # Download do S3/MinIO para arquivo temporário
            s3 = S3Client()
            s3.download_file(file_model.s3_key, tmp_path)

            # Executa extração usando prompt do hospital (retorna dict JSON-serializável)
            result = extract_demand(tmp_path, custom_user_prompt=hospital_prompt)
            if isinstance(result, dict):
                meta = result.setdefault("meta", {})
                meta.pop("pdf_path", None)
                meta["file_id"] = file_id
                meta["filename"] = filename
                meta["hospital_id"] = hospital.id
                meta["hospital_name"] = hospital.name

            job.result_data = result
            # Verificar se foi cancelado antes de marcar como COMPLETED
            if _was_cancelled(session, job):
                logger.warning(f"[EXTRACT_DEMAND] Job {job.id} foi cancelado durante execução")
                return {"ok": False, "error": "job_cancelled", "job_id": job.id}
            job.status = JobStatus.COMPLETED
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            job.error_message = None
            session.add(job)
            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = _safe_error_message(e)
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": job.error_message, "job_id": job.id}
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


async def generate_thumbnail_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Gera thumbnail WebP 500x500 para arquivo (PNG/JPEG/PDF).
    Thumbnail é salvo no MinIO com chave: {original_key}.thumbnail.webp
    Idempotente: se thumbnail já existe, não regenera.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        tmp_path: str | None = None
        file_id: int | None = None
        try:
            import logging
            logger = logging.getLogger(__name__)

            input_data = job.input_data or {}
            file_id = int(input_data.get("file_id"))

            file_model = session.get(File, file_id)
            if not file_model:
                raise RuntimeError(f"File não encontrado (file_id={file_id})")
            if file_model.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")

            # Calcular thumbnail_key: original_key + ".thumbnail.webp"
            original_key = file_model.s3_key
            thumbnail_key = original_key + ".thumbnail.webp"

            # Idempotência: verificar se thumbnail já existe
            s3 = S3Client()
            if s3.file_exists(thumbnail_key):
                # Thumbnail já existe, não regenerar
                # Verificar se foi cancelado antes de marcar como COMPLETED
                if _was_cancelled(session, job):
                    return {"ok": False, "error": "job_cancelled", "job_id": job.id}
                job.status = JobStatus.COMPLETED
                job.completed_at = utc_now()
                job.updated_at = job.completed_at
                job.result_data = {
                    "file_id": file_id,
                    "original_key": original_key,
                    "thumbnail_key": thumbnail_key,
                    "skipped": True,
                    "reason": "thumbnail já existe",
                }
                job.error_message = None
                session.add(job)
                session.commit()
                session.refresh(job)
                return {"ok": True, "job_id": job.id, "skipped": True}

            # Detectar mime type
            mime = file_model.content_type or ""
            filename = file_model.filename or "file"
            _, ext = os.path.splitext(filename)
            ext = (ext or "").lower()

            # Determinar se é imagem, PDF ou Excel
            is_image = mime.startswith("image/") or ext in {".png", ".jpg", ".jpeg"}
            is_pdf = mime == "application/pdf" or ext == ".pdf"
            # MIME types comuns para Excel
            excel_mime_types = {
                "application/vnd.ms-excel",  # XLS antigo
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
                "application/excel",  # Alternativo para XLS
                "application/x-excel",  # Alternativo para XLS
                "application/x-msexcel",  # Alternativo para XLS
            }
            is_excel = (
                mime in excel_mime_types
                or ext in {".xls", ".xlsx"}
            )

            if not (is_image or is_pdf or is_excel):
                # Outro tipo: não gerar thumbnail (frontend exibirá fallback)
                logger.warning(f"[THUMBNAIL] Tipo não suportado para file_id={file_id}: mime={mime}, ext={ext}")
                # Verificar se foi cancelado antes de marcar como COMPLETED
                if _was_cancelled(session, job):
                    return {"ok": False, "error": "job_cancelled", "job_id": job.id}
                job.status = JobStatus.COMPLETED
                job.completed_at = utc_now()
                job.updated_at = job.completed_at
                job.result_data = {
                    "file_id": file_id,
                    "original_key": original_key,
                    "thumbnail_key": thumbnail_key,
                    "skipped": True,
                    "reason": f"tipo não suportado (mime={mime}, ext={ext})",
                }
                job.error_message = None
                session.add(job)
                session.commit()
                session.refresh(job)
                return {"ok": True, "job_id": job.id, "skipped": True}

            # Download do arquivo original para arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp_path = tmp.name

            s3.download_file(original_key, tmp_path)

            # Gerar imagem base
            from PIL import Image
            image: Image.Image | None = None

            if is_pdf:
                # PDF: renderizar página 1 com PyMuPDF
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(tmp_path)
                if len(pdf_doc) == 0:
                    raise RuntimeError("PDF vazio")
                page = pdf_doc[0]  # Primeira página
                # Renderizar em alta resolução (zoom 2.0 para melhor qualidade)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                # Converter para PIL Image
                img_data = pix.tobytes("png")
                import io
                image = Image.open(io.BytesIO(img_data))
                pdf_doc.close()
            elif is_excel:
                # Excel (XLS/XLSX): renderizar primeira planilha como tabela

                import pandas as pd
                import matplotlib
                matplotlib.use('Agg')  # Backend sem GUI
                import matplotlib.pyplot as plt
                import io

                # Ler primeira planilha (limitado a 50 linhas para performance)
                try:
                    if ext == ".xls":
                        df = pd.read_excel(tmp_path, engine='xlrd', nrows=50)
                    else:
                        # XLSX ou extensão não reconhecida: tentar openpyxl primeiro
                        try:
                            df = pd.read_excel(tmp_path, engine='openpyxl', nrows=50)
                        except Exception as e1:
                            logger.warning(f"[THUMBNAIL] Erro com openpyxl, tentando xlrd: {e1}")
                            # Fallback para xlrd se openpyxl falhar
                            df = pd.read_excel(tmp_path, engine='xlrd', nrows=50)
                except Exception as e:
                    logger.error(f"[THUMBNAIL] Erro ao ler Excel: {e}", exc_info=True)
                    raise RuntimeError(f"Erro ao ler Excel: {e}")

                if df.empty:
                    logger.warning(f"[THUMBNAIL] Planilha Excel vazia para file_id={file_id}")
                    raise RuntimeError("Planilha Excel vazia")

                # Criar figura matplotlib
                logger.info(f"[THUMBNAIL] Criando figura matplotlib")
                fig, ax = plt.subplots(figsize=(10, 8), dpi=100)
                ax.axis('tight')
                ax.axis('off')

                # Criar tabela (limitado a 20 colunas para não ficar muito largo)
                df_display = df.iloc[:, :20]  # Primeiras 20 colunas

                # Limitar número de linhas exibidas (máximo 30 para não ficar muito grande)
                df_display = df_display.iloc[:30]

                # Converter valores para string (matplotlib table precisa de strings)
                # Substituir NaN por string vazia e truncar valores muito longos
                def format_cell_value(val):
                    if pd.isna(val):
                        return ''
                    s = str(val)
                    # Truncar valores muito longos (máximo 50 caracteres)
                    if len(s) > 50:
                        return s[:47] + '...'
                    return s

                # Usar apply com função para cada célula (applymap está deprecated)
                df_display_str = df_display.map(format_cell_value)

                table = ax.table(
                    cellText=df_display_str.values.tolist(),
                    colLabels=[str(col)[:30] for col in df_display_str.columns.tolist()],  # Truncar nomes de colunas também
                    cellLoc='left',
                    loc='center',
                    bbox=[0, 0, 1, 1]
                )
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.5)

                # Converter figura para PIL Image
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, pad_inches=0.1)
                buf.seek(0)
                image = Image.open(buf)
                plt.close(fig)
            elif is_image:
                # PNG/JPEG: abrir com Pillow
                image = Image.open(tmp_path)
                # Converter para RGB se necessário (WebP não suporta RGBA diretamente)
                if image.mode in ("RGBA", "LA", "P"):
                    # Criar fundo branco para imagens com transparência
                    rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        # Converter paleta para RGBA primeiro
                        image = image.convert("RGBA")
                    if image.mode in ("RGBA", "LA"):
                        # Usar canal alpha como máscara
                        rgb_image.paste(image, mask=image.split()[-1])
                    else:
                        # Sem transparência, apenas colar
                        rgb_image.paste(image)
                    image = rgb_image
                elif image.mode != "RGB":
                    image = image.convert("RGB")

            if not image:
                raise RuntimeError("Falha ao gerar imagem base")

            # Transformar para 500x500 (fit + fundo branco)
            target_size = (500, 500)
            # Calcular tamanho mantendo proporção (fit)
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            # Criar imagem 500x500 com fundo branco
            thumbnail = Image.new("RGB", target_size, (255, 255, 255))
            # Centralizar imagem original
            x_offset = (target_size[0] - image.size[0]) // 2
            y_offset = (target_size[1] - image.size[1]) // 2
            thumbnail.paste(image, (x_offset, y_offset))

            # Salvar thumbnail como WebP em BytesIO
            import io
            webp_buffer = io.BytesIO()
            thumbnail.save(webp_buffer, format="WEBP", quality=85)
            webp_buffer.seek(0)

            # Upload para MinIO
            s3.upload_fileobj(
                webp_buffer,
                thumbnail_key,
                content_type="image/webp",
            )

            # Sucesso
            # Verificar se foi cancelado antes de marcar como COMPLETED
            if _was_cancelled(session, job):
                logger.warning(f"[THUMBNAIL] Job {job.id} foi cancelado durante execução")
                return {"ok": False, "error": "job_cancelled", "job_id": job.id}
            job.status = JobStatus.COMPLETED
            job.completed_at = utc_now()
            job.updated_at = job.completed_at
            job.result_data = {
                "file_id": file_id,
                "original_key": original_key,
                "thumbnail_key": thumbnail_key,
                "skipped": False,
            }
            job.error_message = None
            session.add(job)
            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id, "thumbnail_key": thumbnail_key}
        except Exception as e:
            error_msg = _safe_error_message(e)
            logger.error(f"[THUMBNAIL] Erro ao gerar thumbnail (job_id={job_id}, file_id={file_id if file_id else 'N/A'}): {error_msg}", exc_info=True)

            job.status = JobStatus.FAILED
            job.error_message = error_msg
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": job.error_message, "job_id": job.id}
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


async def reconcile_pending_orphans(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Auto-fail de jobs órfãos/stale:
      - apenas `PENDING`
      - apenas quando `started_at IS NULL` (nunca virou RUNNING)
      - usa janela dinâmica (10x média últimos 10 COMPLETED do mesmo tipo), com teto 1h
    """
    now = utc_now()
    failed = 0
    scanned = 0

    with Session(engine) as session:
        pending = session.exec(
            select(Job).where(
                Job.status == JobStatus.PENDING,
                Job.started_at.is_(None),  # type: ignore[attr-defined]
            )
        ).all()

        window_cache: dict[tuple[int, JobType], timedelta] = {}
        for job in pending:
            scanned += 1
            key = (job.tenant_id, job.job_type)
            window = window_cache.get(key)
            if window is None:
                window = _stale_window_for(session, tenant_id=job.tenant_id, job_type=job.job_type)
                window_cache[key] = window

            if now - job.created_at <= window:
                continue

            job.status = JobStatus.FAILED
            job.error_message = (
                "orphan/stale: job permaneceu PENDING (started_at ausente) por tempo acima do esperado; "
                "requeue manual (admin)"
            )
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            failed += 1

        if failed:
            session.commit()

    return {"ok": True, "scanned": scanned, "failed": failed}
