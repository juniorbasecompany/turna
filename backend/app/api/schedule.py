from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel as PydanticBaseModel
from sqlmodel import Session, select
from sqlalchemy import func

from app.auth.dependencies import get_current_member
from app.db.session import get_session
from app.model.base import utc_now
from app.model.file import File
from app.model.member import Member
from app.model.schedule_version import ScheduleStatus, ScheduleVersion
from app.storage.service import StorageService


router = APIRouter(prefix="/schedule", tags=["Schedule"])


class SchedulePublishResponse(PydanticBaseModel):
    schedule_version_id: int
    status: str
    pdf_file_id: int
    presigned_url: str


class ScheduleVersionResponse(PydanticBaseModel):
    id: int
    tenant_id: int
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
    items: list[ScheduleVersionResponse]
    total: int


class ScheduleCreateRequest(PydanticBaseModel):
    name: str
    period_start_at: datetime
    period_end_at: datetime
    version_number: int = 1


def _to_minutes(h: int | float) -> int:
    return int(round(float(h) * 60))


def _day_schedules_from_result(*, sv: ScheduleVersion) -> list:
    """
    Converte `ScheduleVersion.result_data` (formato do solver) para uma lista de DaySchedule.
    """
    try:
        from output.day import DaySchedule, Event, Interval, Row, Vacation, _pick_color_from_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar gerador de PDF: {e}") from e

    result_data = sv.result_data or {}
    per_day = result_data.get("per_day") or []
    if not isinstance(per_day, list) or not per_day:
        raise HTTPException(status_code=400, detail="ScheduleVersion não possui result_data.per_day")

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
        raise HTTPException(status_code=400, detail="ScheduleVersion não possui dias válidos para PDF")
    return schedules


@router.post("/{schedule_version_id}/publish", response_model=SchedulePublishResponse, tags=["Schedule"])
def publish_schedule(
    schedule_version_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    sv = session.get(ScheduleVersion, schedule_version_id)
    if not sv:
        raise HTTPException(status_code=404, detail="ScheduleVersion não encontrado")
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
            schedule_version_id=sv.id,
            status=str(sv.status),
            pdf_file_id=file_model.id,
            presigned_url=presigned_url,
        )

    schedules = _day_schedules_from_result(sv=sv)
    try:
        from output.day import render_multi_day_pdf_bytes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar gerador de PDF: {e}") from e

    pdf_bytes = render_multi_day_pdf_bytes(schedules)
    file_model = storage_service.upload_schedule_pdf(
        session=session,
        tenant_id=member.tenant_id,
        schedule_version_id=sv.id,
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
        schedule_version_id=sv.id,
        status=str(sv.status),
        pdf_file_id=file_model.id,
        presigned_url=presigned_url,
    )


@router.get("/{schedule_version_id}/pdf", tags=["Schedule"])
def download_schedule_pdf(
    schedule_version_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    sv = session.get(ScheduleVersion, schedule_version_id)
    if not sv:
        raise HTTPException(status_code=404, detail="ScheduleVersion não encontrado")
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
    Lista ScheduleVersions do tenant atual, com filtros opcionais.
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
    query = select(ScheduleVersion).where(ScheduleVersion.tenant_id == member.tenant_id)
    if status_enum:
        query = query.where(ScheduleVersion.status == status_enum)
    
    # Filtrar por período: escala aparece se seu período se sobrepõe ao filtro
    # Uma escala se sobrepõe se: period_start_at (escala) <= period_end_at (filtro) E period_end_at (escala) >= period_start_at (filtro)
    if period_start_at is not None:
        query = query.where(ScheduleVersion.period_end_at >= period_start_at)
    if period_end_at is not None:
        query = query.where(ScheduleVersion.period_start_at <= period_end_at)

    # Contar total antes de aplicar paginação
    count_query = select(func.count(ScheduleVersion.id)).where(ScheduleVersion.tenant_id == member.tenant_id)
    if status_enum:
        count_query = count_query.where(ScheduleVersion.status == status_enum)
    if period_start_at is not None:
        count_query = count_query.where(ScheduleVersion.period_end_at >= period_start_at)
    if period_end_at is not None:
        count_query = count_query.where(ScheduleVersion.period_start_at <= period_end_at)
    total = session.exec(count_query).one()

    # Aplicar ordenação e paginação
    query = query.order_by(ScheduleVersion.created_at.desc()).limit(limit).offset(offset)

    items = session.exec(query).all()
    return ScheduleListResponse(
        items=[ScheduleVersionResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{schedule_version_id}", response_model=ScheduleVersionResponse, tags=["Schedule"])
def get_schedule(
    schedule_version_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Retorna detalhes de uma ScheduleVersion específica.
    """
    sv = session.get(ScheduleVersion, schedule_version_id)
    if not sv:
        raise HTTPException(status_code=404, detail="ScheduleVersion não encontrado")
    if sv.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return ScheduleVersionResponse.model_validate(sv)


@router.post("", response_model=ScheduleVersionResponse, status_code=201, tags=["Schedule"])
def create_schedule(
    body: ScheduleCreateRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Cria uma ScheduleVersion manualmente (sem job de geração).
    Útil para criar escalas vazias ou importar de outras fontes.
    """
    # Validar período
    if body.period_end_at <= body.period_start_at:
        raise HTTPException(status_code=400, detail="period_end_at deve ser maior que period_start_at")
    if body.period_start_at.tzinfo is None or body.period_end_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="period_start_at/period_end_at devem ter timezone explícito")

    sv = ScheduleVersion(
        tenant_id=member.tenant_id,
        name=body.name,
        period_start_at=body.period_start_at,
        period_end_at=body.period_end_at,
        status=ScheduleStatus.DRAFT,
        version_number=body.version_number,
    )
    session.add(sv)
    session.commit()
    session.refresh(sv)

    return ScheduleVersionResponse.model_validate(sv)

