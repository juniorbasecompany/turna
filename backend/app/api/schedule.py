from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel as PydanticBaseModel
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlmodel import Session, select
from sqlalchemy import func

from zoneinfo import ZoneInfo

from app.auth.dependencies import get_current_member
from app.db.session import get_session
from app.model.base import utc_now
from app.model.demand import Demand
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.member import Member
from app.model.hospital import Hospital
from app.model.schedule import ScheduleStatus, Schedule
from app.model.tenant import Tenant
from app.storage.service import StorageService
from app.worker.worker_settings import WorkerSettings


router = APIRouter(prefix="/schedule", tags=["Schedule"])


class SchedulePublishResponse(PydanticBaseModel):
    schedule_id: int
    status: str
    pdf_file_id: int
    presigned_url: str


class ScheduleResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    hospital_id: int
    hospital_name: str
    hospital_color: Optional[str]  # Cor do hospital em formato hexadecimal (#RRGGBB)
    name: str
    period_start_at: datetime
    period_end_at: datetime
    status: str
    version_number: int
    job_id: Optional[int]
    pdf_file_id: Optional[int]
    generated_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleListResponse(PydanticBaseModel):
    items: list[ScheduleResponse]
    total: int


class ScheduleCreateRequest(PydanticBaseModel):
    hospital_id: int
    name: str
    period_start_at: datetime
    period_end_at: datetime
    version_number: int = 1


class ScheduleGenerateFromDemandsRequest(PydanticBaseModel):
    hospital_id: int
    name: str
    period_start_at: datetime
    period_end_at: datetime
    allocation_mode: str = "greedy"  # "greedy" | "cp-sat"
    pros_by_sequence: Optional[list[dict[str, Any]]] = None
    version_number: int = 1


class ScheduleGenerateFromDemandsResponse(PydanticBaseModel):
    job_id: int
    schedule_id: Optional[int]  # None quando modo from_demands (registros criados pelo worker)


def _build_schedule_response(schedule: Schedule, session: Session) -> ScheduleResponse:
    """
    Constrói um ScheduleResponse incluindo dados do hospital (nome e cor).
    """
    hospital = session.get(Hospital, schedule.hospital_id)
    if not hospital:
        raise HTTPException(status_code=500, detail=f"Hospital {schedule.hospital_id} não encontrado")

    return ScheduleResponse(
        id=schedule.id,
        tenant_id=schedule.tenant_id,
        hospital_id=schedule.hospital_id,
        hospital_name=hospital.name,
        hospital_color=hospital.color,
        name=schedule.name,
        period_start_at=schedule.period_start_at,
        period_end_at=schedule.period_end_at,
        status=schedule.status.value,
        version_number=schedule.version_number,
        job_id=schedule.job_id,
        pdf_file_id=schedule.pdf_file_id,
        generated_at=schedule.generated_at,
        published_at=schedule.published_at,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def _to_minutes(h: int | float) -> int:
    return int(round(float(h) * 60))


def _reconstruct_per_day_from_fragments(fragments: list[Schedule]) -> list[dict]:
    """
    Reconstrói a estrutura per_day a partir de registros fragmentados.

    Args:
        fragments: Lista de Schedule com alocações individuais em result_data

    Returns:
        Lista de dicts no formato per_day (compatível com formato original do solver)
    """
    # Agrupar por dia
    by_day: dict[int, dict] = {}

    # Mapa de profissionais já vistos (para evitar duplicatas em pros_for_day)
    pros_seen: dict[tuple[int, str], dict] = {}

    for fragment in fragments:
        result_data = fragment.result_data or {}
        if not isinstance(result_data, dict):
            continue

        day = result_data.get("day")
        professional_id = result_data.get("professional_id")
        professional = result_data.get("professional")

        if not day or not professional_id:
            continue

        day_num = int(day)

        # Inicializar estrutura do dia se não existir
        if day_num not in by_day:
            by_day[day_num] = {
                "day_number": day_num,
                "pros_for_day": [],
                "assigned_demands_by_pro": defaultdict(list),
                "demands_day": [],
                "assigned_pids": [],
            }

        # Adicionar profissional a pros_for_day (se ainda não foi adicionado)
        pro_key = (day_num, professional_id)
        if pro_key not in pros_seen:
            pros_seen[pro_key] = {
                "id": professional_id,
                "name": professional,
                "can_peds": False,  # Não temos essa info nos fragmentos
                "vacation": [],
            }
            by_day[day_num]["pros_for_day"].append(pros_seen[pro_key])

        # Adicionar demanda a assigned_demands_by_pro
        demand_data = {
            "id": result_data.get("id"),
            "day": day_num,
            "start": result_data.get("start"),
            "end": result_data.get("end"),
            "is_pediatric": result_data.get("is_pediatric", False),
            "source": result_data.get("source", {}),
        }
        by_day[day_num]["assigned_demands_by_pro"][professional_id].append(demand_data)

        # Adicionar a demands_day também
        by_day[day_num]["demands_day"].append(demand_data)
        by_day[day_num]["assigned_pids"].append(professional_id)

    # Converter defaultdict para dict normal e ordenar por dia
    result = []
    for day_num in sorted(by_day.keys()):
        day_data = by_day[day_num]
        # Converter assigned_demands_by_pro de defaultdict para dict normal
        if isinstance(day_data["assigned_demands_by_pro"], defaultdict):
            day_data["assigned_demands_by_pro"] = dict(day_data["assigned_demands_by_pro"])
        result.append(day_data)

    return result


def _day_schedules_from_result(*, sv: Schedule, session: Optional[Session] = None) -> list:
    """
    Converte `Schedule.result_data` (formato do solver) para uma lista de DaySchedule.

    Suporta dois formatos:
    1. Estrutura completa com `per_day` (formato original)
    2. Registro fragmentado - busca registros relacionados pelo job_id e reconstrói estrutura

    Args:
        sv: Schedule a ser processado
        session: Session do banco (necessário apenas se precisar buscar registros fragmentados)
    """
    try:
        from output.day import DaySchedule, Event, Interval, Row, Vacation, _pick_color_from_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar gerador de PDF: {e}") from e

    result_data = sv.result_data or {}
    per_day = result_data.get("per_day") or []

    # Se não tem per_day, pode ser um registro fragmentado - tentar reconstruir
    if (not isinstance(per_day, list) or not per_day) and session is not None and sv.job_id is not None:
        # Buscar registros relacionados pelo job_id
        from sqlmodel import select
        related_records = session.exec(
            select(Schedule)
            .where(Schedule.job_id == sv.job_id)
            .where(Schedule.tenant_id == sv.tenant_id)
            .where(Schedule.id != sv.id)  # Excluir o próprio registro
        ).all()

        if related_records:
            # Reconstruir estrutura per_day a partir dos registros fragmentados
            per_day = _reconstruct_per_day_from_fragments(related_records)

    if not isinstance(per_day, list) or not per_day:
        raise HTTPException(
            status_code=400,
            detail="Schedule não possui result_data.per_day e não foi possível reconstruir a partir de registros fragmentados"
        )

    # Gera um DaySchedule por item de per_day.
    schedules: list[DaySchedule] = []
    for item in per_day:
        if not isinstance(item, dict):
            continue

        day_number = int(item.get("day_number") or 0)
        pros_for_day = item.get("pros_for_day") or []
        assigned_demands_by_pro = item.get("assigned_demands_by_pro") or {}
        demands_day = item.get("demands_day") or []
        assigned_pids = item.get("assigned_pids") or []

        if day_number <= 0:
            continue
        if not isinstance(pros_for_day, list):
            raise HTTPException(status_code=400, detail="result_data.per_day[].pros_for_day inválido")
        if not isinstance(assigned_demands_by_pro, dict):
            raise HTTPException(status_code=400, detail="result_data.per_day[].assigned_demands_by_pro inválido")
        if not isinstance(demands_day, list) or not isinstance(assigned_pids, list):
            raise HTTPException(status_code=400, detail="result_data.per_day[].demands_day/assigned_pids inválido")

        # Janela do dia (mantém um padrão parecido com 06–22 quando possível)
        min_h = min((d.get("start", 6) for d in demands_day if isinstance(d, dict)), default=6)
        max_h = max((d.get("end", 22) for d in demands_day if isinstance(d, dict)), default=22)
        for p in pros_for_day:
            if not isinstance(p, dict):
                continue
            for vs, ve in p.get("vacation", []) or []:
                min_h = min(min_h, vs)
                max_h = max(max_h, ve)

        day_start_h = max(0, min(6, int(min_h)))
        day_end_h = min(24, max(22, int(max_h)))

        rows: list[Row] = []
        for p in pros_for_day:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id") or "").strip()
            if not pid:
                continue

            vacs: list[Vacation] = []
            for vs, ve in p.get("vacation", []) or []:
                vacs.append(Vacation(interval=Interval(_to_minutes(vs), _to_minutes(ve)), label="FÉRIAS"))

            evs: list[Event] = []
            for d in assigned_demands_by_pro.get(pid, []) or []:
                if not isinstance(d, dict):
                    continue
                # Filtra por dia quando o solver guardar demandas multi-dia.
                if int(d.get("day", day_number) or day_number) != day_number:
                    continue
                title = str(d.get("id") or "").strip()
                if not title:
                    continue
                if d.get("is_pediatric"):
                    title += " (PED)"
                evs.append(
                    Event(
                        interval=Interval(_to_minutes(d["start"]), _to_minutes(d["end"])),
                        title=title,
                        subtitle=None,
                        color_rgb=_pick_color_from_text(title),
                    )
                )
            evs.sort(key=lambda e: (e.interval.start_min, e.interval.end_min, e.title))
            rows.append(Row(name=pid, events=evs, vacations=vacs))

        # Linha extra para demandas descobertas (sem alocação).
        uncovered: list[Event] = []
        for d, ap in zip(demands_day, assigned_pids, strict=True):
            if ap is not None:
                continue
            if not isinstance(d, dict):
                continue
            title = str(d.get("id") or "").strip()
            if not title:
                continue
            if d.get("is_pediatric"):
                title += " (PED)"
            uncovered.append(
                Event(
                    interval=Interval(_to_minutes(d["start"]), _to_minutes(d["end"])),
                    title=title,
                    subtitle="DESC",
                    color_rgb=(0.55, 0.14, 0.10),
                )
            )
        uncovered.sort(key=lambda e: (e.interval.start_min, e.interval.end_min, e.title))
        if uncovered:
            lanes: list[list[Event]] = []
            for ev in uncovered:
                placed = False
                for lane in lanes:
                    last = lane[-1]
                    if last.interval.end_min <= ev.interval.start_min:
                        lane.append(ev)
                        placed = True
                        break
                if not placed:
                    lanes.append([ev])

            for i, lane in enumerate(lanes):
                name = "Descobertas" if i == 0 else f"Descobertas {i + 1}"
                rows.append(Row(name=name, events=lane, vacations=[]))

        # Título com data (quando possível) usando o timezone do próprio período.
        day_date = (sv.period_start_at + timedelta(days=day_number - 1)).date()
        title = f"{sv.name} - {day_date.isoformat()}"

        schedules.append(
            DaySchedule(
                title=title,
                day_start_min=_to_minutes(day_start_h),
                day_end_min=_to_minutes(day_end_h),
                rows=rows,
            )
        )

    schedules.sort(key=lambda s: s.title)
    if not schedules:
        raise HTTPException(status_code=400, detail="Schedule não possui dias válidos para PDF")
    return schedules


@router.post("/{schedule_id}/publish", response_model=SchedulePublishResponse, tags=["Schedule"])
def publish_schedule(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    sv = session.get(Schedule, schedule_id)
    if not sv:
        raise HTTPException(status_code=404, detail="Schedule não encontrado")
    if sv.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    storage_service = StorageService()

    # Idempotência: se já existe PDF, apenas retorna URL.
    if sv.pdf_file_id is not None and sv.status == ScheduleStatus.PUBLISHED:
        file_model = session.get(File, sv.pdf_file_id)
        if not file_model:
            raise HTTPException(status_code=500, detail="pdf_file_id aponta para um File inexistente")
        presigned_url = storage_service.get_file_presigned_url(file_model.s3_key, expiration=3600)
        return SchedulePublishResponse(
            schedule_id=sv.id,
            status=str(sv.status),
            pdf_file_id=file_model.id,
            presigned_url=presigned_url,
        )

    schedules = _day_schedules_from_result(sv=sv, session=session)
    try:
        from output.day import render_multi_day_pdf_bytes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar gerador de PDF: {e}") from e

    pdf_bytes = render_multi_day_pdf_bytes(schedules)
    file_model = storage_service.upload_schedule_pdf(
        session=session,
        tenant_id=member.tenant_id,
        schedule_id=sv.id,
        pdf_bytes=pdf_bytes,
    )

    sv.pdf_file_id = file_model.id
    sv.status = ScheduleStatus.PUBLISHED
    sv.published_at = utc_now()
    sv.updated_at = utc_now()
    session.add(sv)
    session.commit()
    session.refresh(sv)

    presigned_url = storage_service.get_file_presigned_url(file_model.s3_key, expiration=3600)
    return SchedulePublishResponse(
        schedule_id=sv.id,
        status=str(sv.status),
        pdf_file_id=file_model.id,
        presigned_url=presigned_url,
    )


@router.get("/{schedule_id}/pdf", tags=["Schedule"])
def download_schedule_pdf(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    sv = session.get(Schedule, schedule_id)
    if not sv:
        raise HTTPException(status_code=404, detail="Schedule não encontrado")
    if sv.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if not sv.pdf_file_id:
        raise HTTPException(status_code=404, detail="PDF não encontrado (schedule ainda não publicada)")

    file_model = session.get(File, sv.pdf_file_id)
    if not file_model:
        raise HTTPException(status_code=500, detail="pdf_file_id aponta para um File inexistente")

    presigned_url = StorageService().get_file_presigned_url(file_model.s3_key, expiration=3600)
    return RedirectResponse(url=presigned_url, status_code=302)


@router.get("/list", response_model=ScheduleListResponse, tags=["Schedule"])
def list_schedules(
    status: Optional[str] = Query(None, description="Filtrar por status (DRAFT, PUBLISHED, ARCHIVED)"),
    period_start_at: Optional[datetime] = Query(None, description="Filtrar por period_start_at >= period_start_at (timestamptz em ISO 8601)"),
    period_end_at: Optional[datetime] = Query(None, description="Filtrar por period_end_at <= period_end_at (timestamptz em ISO 8601)"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Lista Schedules do tenant atual, com filtros opcionais.
    """
    # Validar status se fornecido
    status_enum = None
    if status:
        try:
            status_enum = ScheduleStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")

    # Validar filtros de período
    if period_start_at is not None:
        if period_start_at.tzinfo is None:
            raise HTTPException(status_code=400, detail="period_start_at deve ter timezone explícito (timestamptz)")
    if period_end_at is not None:
        if period_end_at.tzinfo is None:
            raise HTTPException(status_code=400, detail="period_end_at deve ter timezone explícito (timestamptz)")
    if period_start_at is not None and period_end_at is not None:
        if period_start_at > period_end_at:
            raise HTTPException(status_code=400, detail="period_start_at deve ser menor ou igual a period_end_at")

    # Query base
    query = select(Schedule).where(Schedule.tenant_id == member.tenant_id)
    if status_enum:
        query = query.where(Schedule.status == status_enum)

    # Filtrar por período: escala aparece se seu período se sobrepõe ao filtro
    # Uma escala se sobrepõe se: period_start_at (escala) <= period_end_at (filtro) E period_end_at (escala) >= period_start_at (filtro)
    if period_start_at is not None:
        query = query.where(Schedule.period_end_at >= period_start_at)
    if period_end_at is not None:
        query = query.where(Schedule.period_start_at <= period_end_at)

    # Contar total antes de aplicar paginação
    count_query = select(func.count(Schedule.id)).where(Schedule.tenant_id == member.tenant_id)
    if status_enum:
        count_query = count_query.where(Schedule.status == status_enum)
    if period_start_at is not None:
        count_query = count_query.where(Schedule.period_end_at >= period_start_at)
    if period_end_at is not None:
        count_query = count_query.where(Schedule.period_start_at <= period_end_at)
    total = session.exec(count_query).one()

    # Aplicar ordenação e paginação
    query = query.order_by(Schedule.created_at.desc()).limit(limit).offset(offset)

    items = session.exec(query).all()

    # Buscar hospitais das escalas para incluir hospital_name e hospital_color
    hospital_ids = {item.hospital_id for item in items}
    hospital_dict = {}
    if hospital_ids:
        hospital_query = select(Hospital).where(
            Hospital.tenant_id == member.tenant_id,
            Hospital.id.in_(hospital_ids),
        )
        hospital_list = session.exec(hospital_query).all()
        hospital_dict = {h.id: h for h in hospital_list}

    # Construir resposta com hospital_id, hospital_name e hospital_color
    schedule_responses = []
    for item in items:
        hospital = hospital_dict.get(item.hospital_id)
        if not hospital:
            raise HTTPException(status_code=500, detail=f"Hospital {item.hospital_id} não encontrado")
        schedule_response = ScheduleResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            hospital_id=item.hospital_id,
            hospital_name=hospital.name,
            hospital_color=hospital.color,
            name=item.name,
            period_start_at=item.period_start_at,
            period_end_at=item.period_end_at,
            status=item.status.value,
            version_number=item.version_number,
            job_id=item.job_id,
            pdf_file_id=item.pdf_file_id,
            generated_at=item.generated_at,
            published_at=item.published_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        schedule_responses.append(schedule_response)

    return ScheduleListResponse(
        items=schedule_responses,
        total=total,
    )


@router.post("/generate-from-demands", response_model=ScheduleGenerateFromDemandsResponse, status_code=201, tags=["Schedule"])
async def generate_schedule_from_demands(
    body: ScheduleGenerateFromDemandsRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Gera escala a partir de demandas da tabela demand (campo source).

    Lê demandas do banco de dados no período informado e cria um job assíncrono
    para gerar a escala usando o solver (greedy ou cp-sat).
    """
    # Validar hospital
    hospital = session.get(Hospital, body.hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital não encontrado")
    if hospital.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    # Validar período
    if body.period_end_at <= body.period_start_at:
        raise HTTPException(status_code=400, detail="period_end_at deve ser maior que period_start_at")
    if body.period_start_at.tzinfo is None or body.period_end_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="period_start_at/period_end_at devem ter timezone explícito")

    # Buscar timezone do tenant para formatação das datas
    tenant = session.get(Tenant, member.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    tenant_tz = ZoneInfo(tenant.timezone)

    # Validar que há demandas no período (query rápida)
    # As datas já estão em UTC (timestamptz), então a comparação direta funciona
    demands_count = session.exec(
        select(func.count(Demand.id)).where(
            Demand.tenant_id == member.tenant_id,
            Demand.start_time >= body.period_start_at,
            Demand.start_time < body.period_end_at,
        )
    ).one()

    # Se não encontrou, buscar informações para ajudar no debug
    if demands_count == 0:
        # Buscar total de demandas do tenant para contexto
        total_demands = session.exec(
            select(func.count(Demand.id)).where(
                Demand.tenant_id == member.tenant_id,
            )
        ).one()

        # Construir mensagem detalhada
        detail_msg = "Nenhuma demanda encontrada no período informado."

        if total_demands == 0:
            detail_msg += " Não há demandas cadastradas para este tenant. Cadastre demandas antes de gerar a escala."
        else:
            # Buscar primeira e última demanda do tenant para referência
            first_demand = session.exec(
                select(Demand)
                .where(Demand.tenant_id == member.tenant_id)
                .order_by(Demand.start_time.asc())
                .limit(1)
            ).first()

            last_demand = session.exec(
                select(Demand)
                .where(Demand.tenant_id == member.tenant_id)
                .order_by(Demand.start_time.desc())
                .limit(1)
            ).first()

            # Formatar datas usando o timezone da clínica
            def format_datetime_for_user(dt: datetime) -> str:
                """Formata datetime para exibição ao usuário no timezone da clínica"""
                # Converter para timezone da clínica
                dt_local = dt.astimezone(tenant_tz)
                return dt_local.strftime("%d/%m/%Y %H:%M")

            detail_msg += f"\n\nPeríodo selecionado (fuso horário {tenant.timezone}):"
            detail_msg += f"\n- Início: {format_datetime_for_user(body.period_start_at)}"
            detail_msg += f"\n- Fim: {format_datetime_for_user(body.period_end_at)}"

            if first_demand and last_demand:
                detail_msg += f"\n\nDemandas disponíveis no sistema (fuso horário {tenant.timezone}):"
                detail_msg += f"\n- Primeira demanda: {format_datetime_for_user(first_demand.start_time)}"
                detail_msg += f"\n- Última demanda: {format_datetime_for_user(last_demand.start_time)}"
                detail_msg += f"\n\nTotal de demandas cadastradas: {total_demands}"
                detail_msg += "\n\nDica: Ajuste o período para incluir as demandas disponíveis."

        raise HTTPException(
            status_code=400,
            detail=detail_msg,
        )

    # Validar allocation_mode
    if body.allocation_mode not in ("greedy", "cp-sat"):
        raise HTTPException(
            status_code=400,
            detail=f"allocation_mode inválido: {body.allocation_mode}. Use 'greedy' ou 'cp-sat'",
        )

    # Criar Job (sem criar registro mestre de Schedule - apenas registros fragmentados serão criados pelo worker)
    job = Job(
        tenant_id=member.tenant_id,
        job_type=JobType.GENERATE_SCHEDULE,
        status=JobStatus.PENDING,
        input_data={
            "mode": "from_demands",
            "hospital_id": body.hospital_id,
            "name": body.name,
            "period_start_at": body.period_start_at.isoformat(),
            "period_end_at": body.period_end_at.isoformat(),
            "allocation_mode": body.allocation_mode,
            "pros_by_sequence": body.pros_by_sequence,
            "version_number": body.version_number,
        },
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Enfileirar job no Arq
    redis_dsn = WorkerSettings.redis_dsn()
    try:
        redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
        await redis.enqueue_job("generate_schedule_job", job.id)
    except (RedisTimeoutError, RedisConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível (REDIS_URL={redis_dsn}): {str(e)}",
        ) from e

    return ScheduleGenerateFromDemandsResponse(job_id=job.id, schedule_id=None)


@router.get("/{schedule_id}", response_model=ScheduleResponse, tags=["Schedule"])
def get_schedule(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Retorna detalhes de uma Schedule específica.
    """
    sv = session.get(Schedule, schedule_id)
    if not sv:
        raise HTTPException(status_code=404, detail="Schedule não encontrado")
    if sv.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return _build_schedule_response(sv, session)


@router.post("", response_model=ScheduleResponse, status_code=201, tags=["Schedule"])
def create_schedule(
    body: ScheduleCreateRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Cria uma Schedule manualmente (sem job de geração).
    Útil para criar escalas vazias ou importar de outras fontes.
    """
    # Validar hospital
    hospital = session.get(Hospital, body.hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital não encontrado")
    if hospital.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    # Validar período
    if body.period_end_at <= body.period_start_at:
        raise HTTPException(status_code=400, detail="period_end_at deve ser maior que period_start_at")
    if body.period_start_at.tzinfo is None or body.period_end_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="period_start_at/period_end_at devem ter timezone explícito")

    sv = Schedule(
        tenant_id=member.tenant_id,
        hospital_id=body.hospital_id,
        name=body.name,
        period_start_at=body.period_start_at,
        period_end_at=body.period_end_at,
        status=ScheduleStatus.DRAFT,
        version_number=body.version_number,
    )
    session.add(sv)
    session.commit()
    session.refresh(sv)

    return _build_schedule_response(sv, session)


@router.delete("/{schedule_id}", status_code=204, tags=["Schedule"])
def delete_schedule(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Exclui uma Schedule.

    Apenas escalas em status DRAFT podem ser excluídas.
    Escalas publicadas devem ser arquivadas em vez de excluídas.
    """
    sv = session.get(Schedule, schedule_id)
    if not sv:
        raise HTTPException(status_code=404, detail="Schedule não encontrado")
    if sv.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Impedir exclusão de escalas publicadas
    if sv.status == ScheduleStatus.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma escala publicada. Arquive-a em vez disso."
        )

    session.delete(sv)
    session.commit()

    return None

