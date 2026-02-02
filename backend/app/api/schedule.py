from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from app.report.pdf_demand import demands_to_day_schedules
from app.report.pdf_layout import (
    COVER_HEIGHT_PT,
    build_report_cover_only,
    get_report_cover_total_height,
    merge_pdf_cover_with_body_first_page,
    parse_filters_from_frontend,
    query_params_to_filter_parts,
)
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
from app.model.demand import Demand, ScheduleStatus
from app.lib.tenant_format import format_date_for_tenant
from app.model.tenant import Tenant
from app.storage.service import StorageService
from app.worker.worker_settings import WorkerSettings


router = APIRouter(prefix="/schedule", tags=["Schedule"])


def _resolve_schedule_status_filters(
    status: Optional[str], status_list: Optional[str]
) -> tuple[list[ScheduleStatus] | None, list[tuple[str, str]]]:
    """
    Normaliza filtros de status para Schedule, aceitando lista separada por vírgula.
    Parâmetro presente mas vazio (ex: status_list='') significa "nenhum selecionado" → lista vazia (zero resultados).
    """
    filters_parts: list[tuple[str, str]] = []
    values: list[ScheduleStatus] | None = None

    if status_list is not None:
        raw = [s.strip().upper() for s in status_list.split(",") if s.strip()]
        if not raw:
            values = []
        else:
            invalid = [s for s in raw if s not in {"DRAFT", "PUBLISHED", "ARCHIVED"}]
            if invalid:
                raise HTTPException(status_code=400, detail=f"status_list inválido: {', '.join(invalid)}")
            values = [ScheduleStatus[s] for s in raw]
            filters_parts.append(("Status", ", ".join(raw)))
    elif status:
        status_upper = status.strip().upper()
        try:
            values = [ScheduleStatus(status_upper)]
            filters_parts.append(("Status", status_upper))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")

    return values, filters_parts


SCHEDULE_REPORT_PARAM_LABELS = {
    "filter_start_time": "Desde",
    "filter_end_time": "Até",
    "name": "Associado",
    "status": "Status",
    "status_list": "Status",
    "hospital_id": "Hospital",
}


def _schedule_list_queries(
    session: Session,
    tenant_id: int,
    status_values: list[ScheduleStatus] | None,
    filter_start_time: Optional[datetime],
    filter_end_time: Optional[datetime],
    name: Optional[str],
    hospital_id: Optional[int] = None,
):
    """
    Query e count_query para listagem/relatório de escalas (mesmo canal de dados).
    schedule_status considerado igual no painel (card) e no relatório (quadro); dia vem de demand.start_time.
    Filtros: demand.start_time >= filter_start_time, demand.end_time <= filter_end_time.
    name: filtra por member.name (contém), via demand.member_id.
    """
    query = (
        select(Demand)
        .where(Demand.tenant_id == tenant_id)
        .where(Demand.schedule_status.is_not(None))
    )
    count_query = (
        select(func.count(Demand.id))
        .where(Demand.tenant_id == tenant_id)
        .where(Demand.schedule_status.is_not(None))
    )

    if status_values is not None:
        query = query.where(Demand.schedule_status.in_(status_values))
        count_query = count_query.where(Demand.schedule_status.in_(status_values))
    if filter_start_time is not None:
        query = query.where(Demand.start_time >= filter_start_time)
        count_query = count_query.where(Demand.start_time >= filter_start_time)
    if filter_end_time is not None:
        query = query.where(Demand.end_time <= filter_end_time)
        count_query = count_query.where(Demand.end_time <= filter_end_time)
    if name and name.strip():
        term = f"%{name.strip()}%"
        member_subq = select(Member.id).where(Member.tenant_id == tenant_id, Member.name.ilike(term))
        query = query.where(Demand.member_id.in_(member_subq))
        count_query = count_query.where(Demand.member_id.in_(member_subq))
    if hospital_id is not None:
        query = query.where(Demand.hospital_id == hospital_id)
        count_query = count_query.where(Demand.hospital_id == hospital_id)

    return query, count_query


class SchedulePublishResponse(PydanticBaseModel):
    schedule_id: int
    status: str
    pdf_file_id: int
    presigned_url: str


class ScheduleResponse(PydanticBaseModel):
    """Resposta de escala: id é demand_id (Demand concentra demanda + escala)."""
    id: int  # demand_id (mesmo que demand_id para compatibilidade)
    tenant_id: int
    demand_id: int
    hospital_id: int
    hospital_name: str
    hospital_color: Optional[str]
    name: Optional[str] = None  # schedule_name
    period_start_at: Optional[datetime] = None  # não persistido; pode usar start_time para exibição
    period_end_at: Optional[datetime] = None
    status: Optional[str] = None  # schedule_status
    version_number: int = 1
    job_id: Optional[int] = None
    pdf_file_id: Optional[int] = None
    generated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleListResponse(PydanticBaseModel):
    items: list[ScheduleResponse]
    total: int


class ScheduleCreateRequest(PydanticBaseModel):
    """Inicia escala para uma demanda (atualiza Demand com schedule_status DRAFT)."""
    demand_id: int
    name: str
    version_number: int = 1


class ScheduleUpdateRequest(PydanticBaseModel):
    """Atualiza campos de escala na Demand."""
    name: str
    version_number: int = 1
    status: Optional[str] = None  # DRAFT | ARCHIVED (PUBLISHED só via /publish)


class ScheduleGenerateFromDemandsRequest(PydanticBaseModel):
    hospital_id: Optional[int] = None  # Usado apenas como filtro de demandas
    name: Optional[str] = None  # Se não informado, será gerado automaticamente
    period_start_at: datetime
    period_end_at: datetime
    allocation_mode: str = "greedy"  # "greedy" | "cp-sat"
    pros_by_sequence: Optional[list[dict[str, Any]]] = None
    version_number: int = 1


class ScheduleGenerateFromDemandsResponse(PydanticBaseModel):
    job_id: int
    schedule_id: Optional[int]  # None quando modo from_demands (registros criados pelo worker)


def _build_schedule_response(demand: Demand, session: Session) -> ScheduleResponse:
    """
    Constrói um ScheduleResponse a partir de Demand (id = demand_id).
    """
    if not demand.hospital_id:
        raise HTTPException(status_code=500, detail=f"Demand {demand.id} não possui hospital_id")
    hospital = session.get(Hospital, demand.hospital_id)
    if not hospital:
        raise HTTPException(status_code=500, detail=f"Hospital {demand.hospital_id} não encontrado")
    return ScheduleResponse(
        id=demand.id,
        tenant_id=demand.tenant_id,
        demand_id=demand.id,
        hospital_id=demand.hospital_id,
        hospital_name=hospital.label or hospital.name,
        hospital_color=hospital.color,
        name=demand.schedule_name,
        period_start_at=demand.start_time,
        period_end_at=demand.end_time,
        status=demand.schedule_status.value if demand.schedule_status else None,
        version_number=demand.schedule_version_number,
        job_id=demand.job_id,
        pdf_file_id=demand.pdf_file_id,
        generated_at=demand.generated_at,
        published_at=demand.published_at,
        created_at=demand.created_at,
        updated_at=demand.updated_at,
    )


def _to_minutes(h: int | float) -> int:
    return int(round(float(h) * 60))


def _reconstruct_per_day_from_fragments(fragments: list[Demand]) -> list[dict]:
    """
    Reconstrói a estrutura per_day a partir de Demand com schedule_result_data.

    Args:
        fragments: Lista de Demand com alocações individuais em schedule_result_data

    Returns:
        Lista de dicts no formato per_day (compatível com formato original do solver)
    """
    # Agrupar por dia
    by_day: dict[int, dict] = {}

    # Mapa de profissionais já vistos (para evitar duplicatas em pros_for_day)
    pros_seen: dict[tuple[int, str], dict] = {}

    for fragment in fragments:
        result_data = fragment.schedule_result_data or {}
        if not isinstance(result_data, dict):
            continue

        day = result_data.get("day")
        member_id = result_data.get("member_id")
        member = result_data.get("member")

        if not day or not member_id:
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
        pro_key = (day_num, member_id)
        if pro_key not in pros_seen:
            pros_seen[pro_key] = {
                "id": member_id,
                "name": member,
                "can_peds": False,  # Não temos essa info nos fragmentos
                "vacation": [],
            }
            by_day[day_num]["pros_for_day"].append(pros_seen[pro_key])

        # Adicionar demanda a assigned_demands_by_pro (hospital_id para cor no PDF)
        demand_data = {
            "id": result_data.get("id"),
            "day": day_num,
            "start": result_data.get("start"),
            "end": result_data.get("end"),
            "is_pediatric": result_data.get("is_pediatric", False),
            "hospital_id": fragment.hospital_id,
        }
        by_day[day_num]["assigned_demands_by_pro"][member_id].append(demand_data)

        # Adicionar a demands_day também
        by_day[day_num]["demands_day"].append(demand_data)
        by_day[day_num]["assigned_pids"].append(member_id)

    # Converter defaultdict para dict normal e ordenar por dia
    result = []
    for day_num in sorted(by_day.keys()):
        day_data = by_day[day_num]
        # Converter assigned_demands_by_pro de defaultdict para dict normal
        if isinstance(day_data["assigned_demands_by_pro"], defaultdict):
            day_data["assigned_demands_by_pro"] = dict(day_data["assigned_demands_by_pro"])
        result.append(day_data)

    return result


def _day_schedules_from_result(*, demand: Demand, session: Optional[Session] = None) -> list:
    """
    Converte schedule_result_data da Demand (formato do solver) para uma lista de DaySchedule.

    Suporta dois formatos:
    1. Estrutura completa com `per_day` (formato original)
    2. Registro fragmentado - busca Demand relacionados pelo job_id e reconstrói estrutura

    Args:
        demand: Demand com escala a ser processada
        session: Session do banco (necessário apenas se precisar buscar registros fragmentados)
    """
    try:
        from output.day import DaySchedule, Event, Interval, Row, Vacation, _hex_to_rgb
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar gerador de PDF: {e}") from e

    result_data = demand.schedule_result_data or {}
    per_day = result_data.get("per_day") or []

    # Locale do tenant para formatação de data no título (formato da região)
    tenant = session.get(Tenant, demand.tenant_id) if session else None
    tenant_locale = (tenant.locale if tenant else None) or "pt-BR"

    # Se não tem per_day, pode ser fragmentado - buscar Demand pelo job_id e reconstruir
    if (not isinstance(per_day, list) or not per_day) and session is not None and demand.job_id is not None:
        from sqlmodel import select
        related_records = session.exec(
            select(Demand)
            .where(Demand.job_id == demand.job_id)
            .where(Demand.tenant_id == demand.tenant_id)
            .where(Demand.id != demand.id)
        ).all()
        if related_records:
            per_day = _reconstruct_per_day_from_fragments(related_records)

    if not isinstance(per_day, list) or not per_day:
        raise HTTPException(
            status_code=400,
            detail="Demand não possui schedule_result_data.per_day e não foi possível reconstruir a partir de registros fragmentados"
        )

    # Mapa hospital_id -> cor (hex) para pintar quadros pelo hospital
    hospital_color_by_id: dict[int, Optional[str]] = {}
    if session is not None:
        hospital_ids_in_result: set[int] = set()
        for item in per_day:
            if not isinstance(item, dict):
                continue
            for d in (item.get("assigned_demands_by_pro") or {}).values():
                if isinstance(d, list):
                    for x in d:
                        if isinstance(x, dict) and x.get("hospital_id") is not None:
                            hospital_ids_in_result.add(int(x["hospital_id"]))
            for x in item.get("demands_day") or []:
                if isinstance(x, dict) and x.get("hospital_id") is not None:
                    hospital_ids_in_result.add(int(x["hospital_id"]))
        if hospital_ids_in_result:
            for h in session.exec(select(Hospital).where(Hospital.id.in_(hospital_ids_in_result))).all():
                hospital_color_by_id[h.id] = h.color if getattr(h, "color", None) else None

    def _color_rgb_for_demand_dict(d: dict, title: str) -> Optional[tuple[float, float, float]]:
        """Cor do quadro: hospital.color se existir; se estiver sem cor, retorna None (quadro sem cor)."""
        hid = d.get("hospital_id")
        if hid is not None and hid in hospital_color_by_id and hospital_color_by_id[hid]:
            try:
                return _hex_to_rgb(hospital_color_by_id[hid])
            except (ValueError, TypeError):
                pass
        return None

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
                        color_rgb=_color_rgb_for_demand_dict(d, title),
                    )
                )
            evs.sort(key=lambda e: (e.interval.start_min, e.interval.end_min, e.title))
            rows.append(Row(name=pid, events=evs, vacations=vacs))

        # Linha extra para demandas descobertas (sem alocação); cor = hospital ou marrom.
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
            rgb = _color_rgb_for_demand_dict(d, title)
            uncovered.append(
                Event(
                    interval=Interval(_to_minutes(d["start"]), _to_minutes(d["end"])),
                    title=title,
                    subtitle="DESC",
                    color_rgb=rgb,
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

        # Título com data no formato da região do tenant
        day_date = (demand.start_time + timedelta(days=day_number - 1)).date() if demand.start_time else None
        date_str = format_date_for_tenant(day_date, tenant_locale) if day_date else str(day_number)
        title = f"{(demand.schedule_name or 'Escala')} - {date_str}"

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
        raise HTTPException(status_code=400, detail="Demand não possui dias válidos para PDF")
    return schedules


@router.post("/{schedule_id}/publish", response_model=SchedulePublishResponse, tags=["Schedule"])
def publish_schedule(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Publica escala da Demand (schedule_id = demand_id)."""
    demand = session.get(Demand, schedule_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if demand.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    storage_service = StorageService()

    if demand.pdf_file_id is not None and demand.schedule_status == ScheduleStatus.PUBLISHED:
        file_model = session.get(File, demand.pdf_file_id)
        if not file_model:
            raise HTTPException(status_code=500, detail="pdf_file_id aponta para um File inexistente")
        presigned_url = storage_service.get_file_presigned_url(file_model.s3_key, expiration=3600)
        return SchedulePublishResponse(
            schedule_id=demand.id,
            status=str(demand.schedule_status),
            pdf_file_id=file_model.id,
            presigned_url=presigned_url,
        )

    schedules = _day_schedules_from_result(demand=demand, session=session)
    try:
        from output.day import render_multi_day_pdf_body_bytes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar gerador de PDF: {e}") from e

    pdf_bytes = render_multi_day_pdf_body_bytes(schedules)
    file_model = storage_service.upload_demand_pdf(
        session=session,
        tenant_id=member.tenant_id,
        demand_id=demand.id,
        pdf_bytes=pdf_bytes,
    )

    demand.pdf_file_id = file_model.id
    demand.schedule_status = ScheduleStatus.PUBLISHED
    demand.published_at = utc_now()
    demand.updated_at = utc_now()
    session.add(demand)
    session.commit()
    session.refresh(demand)

    presigned_url = storage_service.get_file_presigned_url(file_model.s3_key, expiration=3600)
    return SchedulePublishResponse(
        schedule_id=demand.id,
        status=str(demand.schedule_status),
        pdf_file_id=file_model.id,
        presigned_url=presigned_url,
    )


@router.get("/{schedule_id}/pdf", tags=["Schedule"])
def download_schedule_pdf(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Download do PDF da escala (schedule_id = demand_id)."""
    demand = session.get(Demand, schedule_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if demand.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if not demand.pdf_file_id:
        raise HTTPException(status_code=404, detail="PDF não encontrado (escala ainda não publicada)")

    file_model = session.get(File, demand.pdf_file_id)
    if not file_model:
        raise HTTPException(status_code=500, detail="pdf_file_id aponta para um File inexistente")

    presigned_url = StorageService().get_file_presigned_url(file_model.s3_key, expiration=3600)
    return RedirectResponse(url=presigned_url, status_code=302)


@router.get("/report", tags=["Schedule"])
def report_schedule_pdf(
    filter_start_time: Optional[datetime] = Query(None, description="Filtrar demandas com start_time >= (timestamptz ISO 8601)"),
    filter_end_time: Optional[datetime] = Query(None, description="Filtrar demandas com end_time <= (timestamptz ISO 8601)"),
    status: Optional[str] = Query(None, description="Filtrar por status (DRAFT, PUBLISHED, ARCHIVED)"),
    status_list: Optional[str] = Query(None, description="Filtrar por lista de status (separado por vírgula)"),
    name: Optional[str] = Query(None, description="Filtrar por nome do associado (contém)"),
    hospital_id: Optional[int] = Query(None, description="Filtrar por hospital (demand.hospital_id)"),
    filters: Optional[str] = Query(None, description="JSON: lista {label, value} do painel para o cabeçalho do PDF"),
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Relatório PDF: todas as escalas no período (formato escala_dia1), um dia por página, respeitando filtros do painel."""
    if filter_start_time is not None and filter_start_time.tzinfo is None:
        raise HTTPException(status_code=400, detail="filter_start_time deve ter timezone explícito")
    if filter_end_time is not None and filter_end_time.tzinfo is None:
        raise HTTPException(status_code=400, detail="filter_end_time deve ter timezone explícito")
    if filter_start_time is not None and filter_end_time is not None and filter_start_time > filter_end_time:
        raise HTTPException(status_code=400, detail="filter_start_time deve ser menor ou igual a filter_end_time")
    if hospital_id is not None:
        hospital = session.get(Hospital, hospital_id)
        if not hospital or hospital.tenant_id != member.tenant_id:
            raise HTTPException(status_code=400, detail="hospital_id inválido ou não pertence ao tenant")

    try:
        status_values, _ = _resolve_schedule_status_filters(status, status_list)
        query, _ = _schedule_list_queries(
            session,
            member.tenant_id,
            status_values=status_values,
            filter_start_time=filter_start_time,
            filter_end_time=filter_end_time,
            name=name,
            hospital_id=hospital_id,
        )
        demands = session.exec(query.order_by(Demand.start_time)).all()
        all_schedules = demands_to_day_schedules(
            demands, session, member.tenant_id, title_prefix="Escalas", group_by="member"
        )
        if not all_schedules:
            raise HTTPException(status_code=400, detail="Nenhuma escala no período selecionado")
        try:
            import os
            from reportlab.lib.pagesizes import A4, landscape

            from output.day import expand_schedule_rows_for_test, render_multi_day_pdf_body_bytes
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        # Para teste: triplicar linhas por member e forçar quebra de página no mesmo dia.
        if os.environ.get("TURNA_TEST_TRIPLE_SCHEDULE_ROWS") == "1":
            all_schedules = expand_schedule_rows_for_test(all_schedules, factor=3)
        filters_parts = parse_filters_from_frontend(filters)
        if not filters_parts:
            params = {
                "filter_start_time": filter_start_time,
                "filter_end_time": filter_end_time,
                "name": name,
                "status": status,
                "status_list": status_list,
                "hospital_id": hospital_id,
            }
            formatters = {
                "filter_start_time": lambda v: v.strftime("%d/%m/%Y %H:%M") if hasattr(v, "strftime") else str(v),
                "filter_end_time": lambda v: v.strftime("%d/%m/%Y %H:%M") if hasattr(v, "strftime") else str(v),
            }
            filters_parts = query_params_to_filter_parts(params, SCHEDULE_REPORT_PARAM_LABELS, formatters=formatters)
        tenant = session.get(Tenant, member.tenant_id)
        tenant_name = tenant.name if tenant else None
        cover_bytes = build_report_cover_only(
            report_title="Relatório de escalas",
            filters=filters_parts,
            pagesize=landscape(A4),
            header_title=tenant_name,
        )
        _, page_h = landscape(A4)
        try:
            cover_total_height = get_report_cover_total_height(
                report_title="Relatório de escalas",
                filters=filters_parts,
                pagesize=landscape(A4),
                header_title=tenant_name,
            )
        except Exception:
            cover_total_height = COVER_HEIGHT_PT
        first_page_content_top_y = page_h - cover_total_height
        body_bytes = render_multi_day_pdf_body_bytes(
            all_schedules,
            first_page_content_top_y=first_page_content_top_y,
        )
        pdf_bytes = merge_pdf_cover_with_body_first_page(
            cover_bytes,
            body_bytes,
            capa_height_pt=cover_total_height,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="relatorio-escalas.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list", response_model=ScheduleListResponse, tags=["Schedule"])
def list_schedules(
    status: Optional[str] = Query(None, description="Filtrar por schedule_status (DRAFT, PUBLISHED, ARCHIVED)"),
    status_list: Optional[str] = Query(None, description="Filtrar por lista de status (separado por vírgula)"),
    filter_start_time: Optional[datetime] = Query(None, description="Filtrar demandas com start_time >= (timestamptz ISO 8601)"),
    filter_end_time: Optional[datetime] = Query(None, description="Filtrar demandas com end_time <= (timestamptz ISO 8601)"),
    name: Optional[str] = Query(None, description="Filtrar por nome do associado (contém)"),
    hospital_id: Optional[int] = Query(None, description="Filtrar por hospital (demand.hospital_id)"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Lista Demand com escala (schedule_status não nulo) do tenant atual.
    Filtros: demand.start_time >= filter_start_time, demand.end_time <= filter_end_time.
    """
    status_values, _ = _resolve_schedule_status_filters(status, status_list)
    if filter_start_time is not None and filter_start_time.tzinfo is None:
        raise HTTPException(status_code=400, detail="filter_start_time deve ter timezone explícito")
    if filter_end_time is not None and filter_end_time.tzinfo is None:
        raise HTTPException(status_code=400, detail="filter_end_time deve ter timezone explícito")
    if filter_start_time is not None and filter_end_time is not None and filter_start_time > filter_end_time:
        raise HTTPException(status_code=400, detail="filter_start_time deve ser menor ou igual a filter_end_time")
    if hospital_id is not None:
        hospital = session.get(Hospital, hospital_id)
        if not hospital or hospital.tenant_id != member.tenant_id:
            raise HTTPException(status_code=400, detail="hospital_id inválido ou não pertence ao tenant")

    query, count_query = _schedule_list_queries(
        session,
        member.tenant_id,
        status_values=status_values,
        filter_start_time=filter_start_time,
        filter_end_time=filter_end_time,
        name=name,
        hospital_id=hospital_id,
    )
    total = session.exec(count_query).one()
    items = session.exec(
        query.order_by(Demand.created_at.desc()).limit(limit).offset(offset)
    ).all()

    schedule_responses = []
    for demand in items:
        try:
            schedule_responses.append(_build_schedule_response(demand, session))
        except HTTPException:
            raise
    return ScheduleListResponse(items=schedule_responses, total=total)


@router.post("/generate-from-demands", response_model=ScheduleGenerateFromDemandsResponse, status_code=201, tags=["Schedule"])
async def generate_schedule_from_demands(
    body: ScheduleGenerateFromDemandsRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Gera escalas a partir de demandas da tabela demand.

    Lê demandas do banco de dados no período informado e cria um job assíncrono
    para gerar as escalas usando o solver (greedy ou cp-sat).

    O worker atualiza cada Demand com o resultado da alocação (schedule_status,
    schedule_result_data, etc.). O hospital_id informado no body é usado apenas
    como filtro para selecionar as demandas; cada Demand mantém seu hospital_id.

    Se name não for informado, será gerado automaticamente.
    """
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

    # filter_hospital_id: usado apenas para filtrar demandas (opcional)
    filter_hospital_id = body.hospital_id

    # Validar hospital do filtro (se informado)
    if filter_hospital_id:
        filter_hospital = session.get(Hospital, filter_hospital_id)
        if not filter_hospital:
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if filter_hospital.tenant_id != member.tenant_id:
            raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    # Contar demandas no período (aplicando filtro de hospital se informado)
    # As datas já estão em UTC (timestamptz), então a comparação direta funciona
    demands_query = select(func.count(Demand.id)).where(
        Demand.tenant_id == member.tenant_id,
        Demand.start_time >= body.period_start_at,
        Demand.start_time < body.period_end_at,
    )
    if filter_hospital_id:
        demands_query = demands_query.where(Demand.hospital_id == filter_hospital_id)

    demands_count = session.exec(demands_query).one()

    # Verificar se todas as demandas têm hospital_id (obrigatório para a escala)
    demands_without_hospital = session.exec(
        select(func.count(Demand.id)).where(
            Demand.tenant_id == member.tenant_id,
            Demand.start_time >= body.period_start_at,
            Demand.start_time < body.period_end_at,
            Demand.hospital_id.is_(None),
        )
    ).one()

    if demands_without_hospital > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {demands_without_hospital} demanda(s) no período sem hospital associado. "
                   "Todas as demandas precisam ter hospital definido para gerar a escala."
        )

    # Buscar primeira demanda para obter informações do hospital (para nome da escala)
    first_demand_query = (
        select(Demand)
        .where(
            Demand.tenant_id == member.tenant_id,
            Demand.start_time >= body.period_start_at,
            Demand.start_time < body.period_end_at,
        )
        .order_by(Demand.start_time.asc())
    )
    if filter_hospital_id:
        first_demand_query = first_demand_query.where(Demand.hospital_id == filter_hospital_id)
    first_demand_query = first_demand_query.limit(1)

    first_demand = session.exec(first_demand_query).first()
    hospital: Optional[Hospital] = None
    if first_demand and first_demand.hospital_id:
        hospital = session.get(Hospital, first_demand.hospital_id)

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

    # Gerar nome automático se não informado
    schedule_name = body.name
    if not schedule_name:
        hospital_name = (hospital.label or hospital.name) if hospital else "Geral"
        start_local = body.period_start_at.astimezone(tenant_tz)
        end_local = body.period_end_at.astimezone(tenant_tz)
        schedule_name = f"{hospital_name} - {start_local.strftime('%d/%m/%Y')} a {end_local.strftime('%d/%m/%Y')}"

    # Criar Job; o worker atualiza cada Demand com o resultado da alocação.
    job = Job(
        tenant_id=member.tenant_id,
        job_type=JobType.GENERATE_SCHEDULE,
        status=JobStatus.PENDING,
        input_data={
            "mode": "from_demands",
            "filter_hospital_id": filter_hospital_id,  # Hospital usado apenas para filtro (opcional)
            "name": schedule_name,
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
    """Retorna detalhes da escala da Demand (schedule_id = demand_id)."""
    demand = session.get(Demand, schedule_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if demand.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if demand.schedule_status is None:
        raise HTTPException(status_code=404, detail="Demanda não possui escala (schedule_status nulo)")
    return _build_schedule_response(demand, session)


@router.post("", response_model=ScheduleResponse, status_code=201, tags=["Schedule"])
def create_schedule(
    body: ScheduleCreateRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Inicia escala para uma demanda (atualiza Demand com schedule_status DRAFT)."""
    demand = session.get(Demand, body.demand_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if demand.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Demanda não pertence ao tenant atual")
    if not demand.hospital_id:
        raise HTTPException(status_code=400, detail="Demanda não possui hospital associado")
    if demand.schedule_status is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe escala para esta demanda (schedule_status={demand.schedule_status})"
        )

    demand.schedule_status = ScheduleStatus.DRAFT
    demand.schedule_name = body.name
    demand.schedule_version_number = body.version_number
    demand.updated_at = utc_now()
    session.add(demand)
    session.commit()
    session.refresh(demand)
    return _build_schedule_response(demand, session)


@router.put("/{schedule_id}", response_model=ScheduleResponse, tags=["Schedule"])
def update_schedule(
    schedule_id: int,
    body: ScheduleUpdateRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Atualiza campos de escala na Demand (nome, versão, status ARCHIVED)."""
    demand = session.get(Demand, schedule_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if demand.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if demand.schedule_status is None:
        raise HTTPException(status_code=404, detail="Demanda não possui escala")

    if demand.schedule_status == ScheduleStatus.DRAFT:
        demand.schedule_name = body.name
        demand.schedule_version_number = body.version_number

    if body.status is not None:
        try:
            new_status = ScheduleStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="status inválido")
        if new_status == ScheduleStatus.ARCHIVED and demand.schedule_status == ScheduleStatus.PUBLISHED:
            demand.schedule_status = ScheduleStatus.ARCHIVED
        elif new_status != demand.schedule_status and new_status != ScheduleStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail="Alteração de status permitida apenas para ARCHIVED (escala publicada)"
            )

    demand.updated_at = utc_now()
    session.add(demand)
    session.commit()
    session.refresh(demand)
    return _build_schedule_response(demand, session)


@router.delete("/{schedule_id}", status_code=204, tags=["Schedule"])
def delete_schedule(
    schedule_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Reseta o estado de escala da Demand (apenas DRAFT). Publicadas devem ser arquivadas."""
    demand = session.get(Demand, schedule_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if demand.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if demand.schedule_status is None:
        raise HTTPException(status_code=404, detail="Demanda não possui escala")
    if demand.schedule_status == ScheduleStatus.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma escala publicada. Arquive-a em vez disso."
        )

    demand.schedule_status = None
    demand.schedule_name = None
    demand.schedule_version_number = 1
    demand.schedule_result_data = None
    demand.generated_at = None
    demand.published_at = None
    demand.pdf_file_id = None
    demand.job_id = None
    demand.member_id = None
    demand.updated_at = utc_now()
    session.add(demand)
    session.commit()
    return None

