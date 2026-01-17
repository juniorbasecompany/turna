import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File as FastAPIFile, Response
from fastapi.responses import StreamingResponse
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.db.session import get_session
from app.model.tenant import Tenant
from pydantic import BaseModel as PydanticBaseModel, field_validator
from app.api.auth import router as auth_router
from app.api.schedule import router as schedule_router
from app.auth.dependencies import get_current_account, get_current_membership, require_role
from app.model.membership import Membership, MembershipRole, MembershipStatus
from app.model.audit_log import AuditLog
from app.model.account import Account
from app.storage.service import StorageService
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.schedule_version import ScheduleVersion, ScheduleStatus
from app.model.hospital import Hospital
from app.services.hospital_service import create_default_hospital_for_tenant
from app.worker.worker_settings import WorkerSettings
from app.model.base import utc_now


router = APIRouter()  # Sem tag padrão - cada endpoint define sua própria tag
router.include_router(auth_router)
router.include_router(schedule_router)

_MAX_STALE_WINDOW = timedelta(hours=1)


def _try_write_audit_log(session: Session, audit: AuditLog) -> None:
    """
    Auditoria best-effort: não deve quebrar a request se falhar.
    """
    try:
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()


def _isoformat_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Diretiva: timestamps sem fuso explícito são inválidos.
        # Como este helper é usado para serialização, falhamos explicitamente para não "assumir UTC".
        raise ValueError("datetime sem timezone (tzinfo=None) é inválido")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/me", tags=["Auth"])
def get_me(
    account: Account = Depends(get_current_account),
    membership: Membership = Depends(get_current_membership),
):
    """
    Retorna os dados da conta autenticada.
    Endpoint na raiz conforme checklist.
    """
    return {
        "id": account.id,
        "email": account.email,
        "name": account.name,
        "role": membership.role.value,
        "tenant_id": membership.tenant_id,
        "auth_provider": account.auth_provider,
        "created_at": _isoformat_utc(account.created_at),
        "updated_at": _isoformat_utc(account.updated_at),
    }


class TenantCreate(PydanticBaseModel):
    name: str
    slug: str
    timezone: str = "America/Sao_Paulo"
    locale: str = "pt-BR"
    currency: str = "BRL"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError("timezone inválido (esperado IANA, ex: America/Sao_Paulo)") from e
        return v

    @field_validator("locale", "currency")
    @classmethod
    def validate_string_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("campo não pode ser vazio")
        return v.strip()


class TenantResponse(PydanticBaseModel):
    id: int
    name: str
    slug: str
    timezone: str
    locale: str
    currency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/health", tags=["System"])
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/tenant", response_model=TenantResponse, status_code=201, tags=["Tenant"])
def create_tenant(
    tenant_data: TenantCreate,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """Cria um novo tenant e cria Membership ADMIN para o criador."""
    # Verifica se já existe um tenant com o mesmo slug
    existing = session.exec(select(Tenant).where(Tenant.slug == tenant_data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant com este slug já existe")

    tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        timezone=tenant_data.timezone,
        locale=tenant_data.locale,
        currency=tenant_data.currency,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    membership = Membership(
        tenant_id=tenant.id,
        account_id=account.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    )
    session.add(membership)
    session.commit()

    # Criar hospital default para o tenant
    create_default_hospital_for_tenant(session, tenant.id)

    return tenant


@router.get("/tenant/me", response_model=TenantResponse, tags=["Tenant"])
def get_current_tenant_info(
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Retorna informações do tenant atual do usuário autenticado.
    """
    tenant = session.get(Tenant, membership.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return tenant


class TenantInviteRequest(PydanticBaseModel):
    email: str
    role: str = "account"  # MVP: account/admin
    name: str | None = None


class TenantInviteResponse(PydanticBaseModel):
    membership_id: int
    email: str
    status: str
    role: str


@router.post("/tenant/{tenant_id}/invite", response_model=TenantInviteResponse, status_code=201, tags=["Tenant"])
def invite_to_tenant(
    tenant_id: int,
    body: TenantInviteRequest,
    admin_membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria/atualiza um convite (Membership PENDING) para um email no tenant atual.

    Regras:
      - O caller deve ser ADMIN e o tenant do token deve bater com o tenant_id do path.
      - Idempotente por (tenant_id, account_id).
    """
    if admin_membership.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    role_raw = body.role.strip().lower()
    if role_raw not in {"account", "admin"}:
        raise HTTPException(status_code=400, detail="role inválida (esperado: account|admin)")
    role = MembershipRole.ADMIN if role_raw == "admin" else MembershipRole.ACCOUNT

    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    account = session.exec(select(Account).where(Account.email == email)).first()
    if not account:
        account = Account(
            email=email,
            name=body.name or email,
            role="account",
            auth_provider="invite",
        )
        session.add(account)
        session.commit()
        session.refresh(account)

    membership = session.exec(
        select(Membership).where(
            Membership.tenant_id == tenant.id,
            Membership.account_id == account.id,
        )
    ).first()

    if membership:
        # Não duplica. Se já estiver ACTIVE, apenas devolve.
        prev_status = membership.status
        prev_role = membership.role
        if membership.status in {MembershipStatus.REJECTED, MembershipStatus.REMOVED}:
            membership.status = MembershipStatus.PENDING
        if membership.status == MembershipStatus.PENDING:
            membership.role = role
        membership.updated_at = utc_now()
        session.add(membership)
        session.commit()
        session.refresh(membership)

        if prev_status != membership.status or prev_role != membership.role:
            _try_write_audit_log(
                session,
                AuditLog(
                    tenant_id=tenant.id,
                    actor_account_id=admin_membership.account_id,
                    membership_id=membership.id,
                    event_type="membership_invited",
                    data={
                        "target_account_id": account.id,
                        "email": account.email,
                        "from_status": prev_status.value,
                        "to_status": membership.status.value,
                        "from_role": prev_role.value,
                        "to_role": membership.role.value,
                    },
                ),
            )
        return TenantInviteResponse(
            membership_id=membership.id,
            email=account.email,
            status=membership.status.value,
            role=membership.role.value,
        )

    membership = Membership(
        tenant_id=tenant.id,
        account_id=account.id,
        role=role,
        status=MembershipStatus.PENDING,
    )
    session.add(membership)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Membership duplicado (tenant_id, account_id) não permitido",
        ) from e
    session.refresh(membership)
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=tenant.id,
            actor_account_id=admin_membership.account_id,
            membership_id=membership.id,
            event_type="membership_invited",
            data={
                "target_account_id": account.id,
                "email": account.email,
                "from_status": None,
                "to_status": membership.status.value,
                "from_role": None,
                "to_role": membership.role.value,
            },
        ),
    )
    return TenantInviteResponse(
        membership_id=membership.id,
        email=account.email,
        status=membership.status.value,
        role=membership.role.value,
    )


class MembershipRemoveResponse(PydanticBaseModel):
    membership_id: int
    status: str


@router.post(
    "/tenant/{tenant_id}/memberships/{membership_id}/remove",
    response_model=MembershipRemoveResponse,
    status_code=200,
    tags=["Tenant"],
)
def remove_membership(
    tenant_id: int,
    membership_id: int,
    admin_membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove (soft-delete) um membership do tenant (status -> REMOVED).

    Regra de segurança:
      - não permitir remover o último membership ACTIVE de um account.
    """
    if admin_membership.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    membership = session.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership não encontrado")
    if membership.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if membership.status == MembershipStatus.ACTIVE:
        active_count = session.exec(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.account_id == membership.account_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        ).one()
        if int(active_count or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Não é permitido remover o último membership ACTIVE da conta. "
                    "Antes, garanta outro acesso (ex.: outro tenant) ou transfira permissões."
                ),
            )

    prev_status = membership.status
    membership.status = MembershipStatus.REMOVED
    membership.updated_at = utc_now()
    session.add(membership)
    session.commit()
    session.refresh(membership)
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=tenant_id,
            actor_account_id=admin_membership.account_id,
            membership_id=membership.id,
            event_type="membership_status_changed",
            data={
                "from_status": prev_status.value,
                "to_status": membership.status.value,
                "target_account_id": membership.account_id,
            },
        ),
    )
    return MembershipRemoveResponse(membership_id=membership.id, status=membership.status.value)


class JobPingResponse(PydanticBaseModel):
    job_id: int


class JobExtractRequest(PydanticBaseModel):
    file_id: int


class JobExtractResponse(PydanticBaseModel):
    job_id: int


class JobResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    job_type: str
    status: str
    input_data: dict | None = None
    result_data: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class JobRequeueRequest(PydanticBaseModel):
    force: bool = False
    wipe_result: bool = False


class JobRequeueResponse(PydanticBaseModel):
    job_id: int
    enqueued_function: str


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


@router.post("/job/ping", response_model=JobPingResponse, status_code=201, tags=["Job"])
async def create_ping_job(
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    job = Job(
        tenant_id=membership.tenant_id,
        job_type=JobType.PING,
        status=JobStatus.PENDING,
        input_data={"ping": True},
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    redis_dsn = WorkerSettings.redis_dsn()
    try:
        redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
        await redis.enqueue_job("ping_job", job.id)
    except (RedisTimeoutError, RedisConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível (REDIS_URL={redis_dsn}): {str(e)}",
        ) from e

    return JobPingResponse(job_id=job.id)


@router.post("/job/extract", response_model=JobExtractResponse, status_code=201, tags=["Job"])
async def create_extract_job(
    body: JobExtractRequest,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    file_model = session.get(File, body.file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="File não encontrado")
    if file_model.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    job = Job(
        tenant_id=membership.tenant_id,
        job_type=JobType.EXTRACT_DEMAND,
        status=JobStatus.PENDING,
        input_data={"file_id": body.file_id},
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    redis_dsn = WorkerSettings.redis_dsn()
    try:
        redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
        await redis.enqueue_job("extract_demand_job", job.id)
    except (RedisTimeoutError, RedisConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível (REDIS_URL={redis_dsn}): {str(e)}",
        ) from e

    return JobExtractResponse(job_id=job.id)


class JobListResponse(PydanticBaseModel):
    items: list[JobResponse]
    total: int


@router.get("/job/list", response_model=JobListResponse, tags=["Job"])
def list_jobs(
    job_type: Optional[str] = Query(None, description="Filtrar por tipo (PING, EXTRACT_DEMAND, GENERATE_SCHEDULE)"),
    status: Optional[str] = Query(None, description="Filtrar por status (PENDING, RUNNING, COMPLETED, FAILED)"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista jobs do tenant atual, com filtros opcionais.
    """
    # Validar filtros se fornecidos
    job_type_enum = None
    if job_type:
        try:
            job_type_enum = JobType(job_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Job type inválido: {job_type}")

    status_enum = None
    if status:
        try:
            status_enum = JobStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")

    # Query base
    query = select(Job).where(Job.tenant_id == membership.tenant_id)
    if job_type_enum:
        query = query.where(Job.job_type == job_type_enum)
    if status_enum:
        query = query.where(Job.status == status_enum)

    # Contar total antes de aplicar paginação
    count_query = select(func.count(Job.id)).where(Job.tenant_id == membership.tenant_id)
    if job_type_enum:
        count_query = count_query.where(Job.job_type == job_type_enum)
    if status_enum:
        count_query = count_query.where(Job.status == status_enum)
    total = session.exec(count_query).one()

    # Aplicar ordenação e paginação
    query = query.order_by(Job.created_at.desc()).limit(limit).offset(offset)

    items = session.exec(query).all()
    return JobListResponse(
        items=[JobResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/job/{job_id}", response_model=JobResponse, tags=["Job"])
def get_job(
    job_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return job


@router.post("/job/{job_id}/requeue", response_model=JobRequeueResponse, status_code=202, tags=["Job"])
async def requeue_job(
    job_id: int,
    body: JobRequeueRequest,
    _admin: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Reenfileira um job (ex.: quando ficou órfão em PENDING por restart/worker antigo).

    Regras:
      - Apenas admin
      - Mesmo tenant
      - Por padrão só permite requeue se status estiver PENDING/FAILED (use force=true para ignorar)
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != _admin.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Por padrão, requeue só é permitido para:
    # - FAILED (manual)
    # - PENDING "stale" e ainda não iniciado (started_at is NULL)
    # Sem heartbeat, não auto-tratamos RUNNING.
    now = utc_now()
    window = _stale_window_for(session, tenant_id=job.tenant_id, job_type=job.job_type)
    is_pending_stale = (
        job.status == JobStatus.PENDING
        and job.started_at is None  # type: ignore[attr-defined]
        and (now - job.created_at) > window
    )

    if not body.force:
        if job.job_type == JobType.PING:
            raise HTTPException(
                status_code=400,
                detail="Job transiente (PING) não deve ser reenfileirado; prefira expirar/cancelar.",
            )
        if job.status == JobStatus.FAILED:
            pass
        elif is_pending_stale:
            pass
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Requeue permitido apenas para FAILED ou PENDING stale (started_at ausente). "
                    "Use force=true para ignorar."
                ),
            )
    else:
        # Com force, permitimos requeue mesmo para RUNNING/COMPLETED (alto risco de duplicação/custo).
        # Mantemos result_data por padrão; wipe_result controla limpeza explícita.
        pass

    if job.job_type == JobType.PING:
        fn = "ping_job"
    elif job.job_type == JobType.EXTRACT_DEMAND:
        fn = "extract_demand_job"
    else:
        raise HTTPException(status_code=400, detail=f"job_type não suportado para requeue: {job.job_type}")

    # Reseta campos de execução para evitar confusão na leitura do job.
    job.status = JobStatus.PENDING
    job.error_message = None
    if body.wipe_result:
        job.result_data = None
    job.completed_at = None
    job.started_at = None  # type: ignore[attr-defined]
    job.updated_at = utc_now()
    session.add(job)
    session.commit()

    redis_dsn = WorkerSettings.redis_dsn()
    try:
        redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
        await redis.enqueue_job(fn, job.id)
    except (RedisTimeoutError, RedisConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível (REDIS_URL={redis_dsn}): {str(e)}",
        ) from e

    return JobRequeueResponse(job_id=job.id, enqueued_function=fn)


class FileUploadResponse(PydanticBaseModel):
    file_id: int
    filename: str
    content_type: str
    file_size: int
    s3_url: str
    presigned_url: str

    class Config:
        from_attributes = True


class FileResponse(PydanticBaseModel):
    """Resposta de arquivo para listagem (sem presigned_url)."""
    id: int
    filename: str
    content_type: str
    file_size: int
    created_at: datetime
    hospital_id: int
    hospital_name: str
    can_delete: bool  # True se não possui job EXTRACT_DEMAND COMPLETED
    job_status: Optional[str] = None  # Status do job mais recente EXTRACT_DEMAND (PENDING, RUNNING, COMPLETED, FAILED) ou None se não houver job

    class Config:
        from_attributes = True


class FileListResponse(PydanticBaseModel):
    items: list[FileResponse]
    total: int


class FileDownloadResponse(PydanticBaseModel):
    """Resposta de download de arquivo com URL presignada."""
    id: int
    filename: str
    content_type: str
    presigned_url: str

    class Config:
        from_attributes = True


class ScheduleGenerateRequest(PydanticBaseModel):
    extract_job_id: int
    period_start_at: datetime
    period_end_at: datetime
    name: str = "Schedule"
    allocation_mode: str = "greedy"  # MVP: greedy
    pros_by_sequence: list[dict] | None = None


class ScheduleGenerateResponse(PydanticBaseModel):
    job_id: int
    schedule_version_id: int


@router.post("/file/upload", response_model=FileUploadResponse, status_code=201, tags=["File"])
def upload_file(
    file: UploadFile = FastAPIFile(...),
    hospital_id: int = Query(..., description="ID do hospital (obrigatório)"),
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Faz upload de arquivo para MinIO/S3 e cria registro File no banco.
    Requer hospital_id obrigatório.

    Retorna file_id, s3_url e presigned_url para acesso ao arquivo.
    """
    # Validar que o hospital existe e pertence ao tenant
    hospital = session.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital não encontrado")
    if hospital.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    storage_service = StorageService()

    try:
        # Upload arquivo e criar registro
        file_model = storage_service.upload_imported_file(
            session=session,
            tenant_id=membership.tenant_id,
            hospital_id=hospital_id,
            file=file,
        )

        # Gerar URL presignada
        presigned_url = storage_service.get_file_presigned_url(
            s3_key=file_model.s3_key,
            expiration=3600,  # 1 hora
        )

        return FileUploadResponse(
            file_id=file_model.id,
            filename=file_model.filename,
            content_type=file_model.content_type,
            file_size=file_model.file_size,
            s3_url=file_model.s3_url,
            presigned_url=presigned_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao fazer upload do arquivo: {str(e)}"
        # Em desenvolvimento, incluir traceback completo
        if os.getenv("APP_ENV", "dev") == "dev":
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.get("/file/list", response_model=FileListResponse, tags=["File"])
def list_files(
    start_at: Optional[datetime] = Query(None, description="Filtrar por created_at >= start_at (timestamptz em ISO 8601)"),
    end_at: Optional[datetime] = Query(None, description="Filtrar por created_at <= end_at (timestamptz em ISO 8601)"),
    hospital_id: Optional[int] = Query(None, description="Filtrar por hospital_id (opcional)"),
    limit: int = Query(21, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista arquivos do tenant atual, com filtros opcionais por período, hospital e paginação.

    Filtra exclusivamente pelo campo created_at (não usa uploaded_at ou updated_at).
    Sempre filtra por tenant_id do JWT (via membership).
    Ordena por created_at decrescente.
    Retorna hospital_id e hospital_name para cada arquivo.
    """
    # Validar hospital_id se fornecido
    if hospital_id is not None:
        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != membership.tenant_id:
            raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    # Query base - sempre filtrar por tenant_id
    query = select(File).where(File.tenant_id == membership.tenant_id)

    # Aplicar filtros de período (created_at)
    if start_at is not None:
        if start_at.tzinfo is None:
            raise HTTPException(status_code=400, detail="start_at deve ter timezone explícito (timestamptz)")
        query = query.where(File.created_at >= start_at)

    if end_at is not None:
        if end_at.tzinfo is None:
            raise HTTPException(status_code=400, detail="end_at deve ter timezone explícito (timestamptz)")
        query = query.where(File.created_at <= end_at)

    # Aplicar filtro por hospital_id se fornecido
    if hospital_id is not None:
        query = query.where(File.hospital_id == hospital_id)

    # Validar intervalo
    if start_at is not None and end_at is not None:
        if start_at > end_at:
            raise HTTPException(status_code=400, detail="start_at deve ser menor ou igual a end_at")

    # Contar total antes de aplicar paginação
    count_query = select(func.count(File.id)).where(File.tenant_id == membership.tenant_id)
    if start_at is not None:
        count_query = count_query.where(File.created_at >= start_at)
    if end_at is not None:
        count_query = count_query.where(File.created_at <= end_at)
    if hospital_id is not None:
        count_query = count_query.where(File.hospital_id == hospital_id)
    total = session.exec(count_query).one()

    # Aplicar ordenação e paginação (created_at decrescente)
    query = query.order_by(File.created_at.desc()).limit(limit).offset(offset)

    items = session.exec(query).all()

    # Buscar todos os jobs EXTRACT_DEMAND COMPLETED do tenant para verificar quais arquivos podem ser deletados
    completed_jobs_query = select(Job).where(
        Job.tenant_id == membership.tenant_id,
        Job.job_type == JobType.EXTRACT_DEMAND,
        Job.status == JobStatus.COMPLETED,
    )
    completed_jobs = session.exec(completed_jobs_query).all()

    # Criar set com file_ids que têm job COMPLETED
    file_ids_with_completed_job = set()
    for job in completed_jobs:
        if job.input_data and "file_id" in job.input_data:
            job_file_id = job.input_data["file_id"]
            # Converter para int para garantir comparação correta (pode vir como string do JSON)
            if isinstance(job_file_id, str):
                try:
                    job_file_id = int(job_file_id)
                except (ValueError, TypeError):
                    continue
            file_ids_with_completed_job.add(job_file_id)

    # Buscar todos os jobs EXTRACT_DEMAND do tenant para obter o status mais recente de cada arquivo
    all_jobs_query = select(Job).where(
        Job.tenant_id == membership.tenant_id,
        Job.job_type == JobType.EXTRACT_DEMAND,
    ).order_by(Job.created_at.desc())
    all_jobs = session.exec(all_jobs_query).all()

    # Criar dict com file_id -> job_status do job mais recente
    file_id_to_latest_job_status = {}
    for job in all_jobs:
        if job.input_data and "file_id" in job.input_data:
            job_file_id = job.input_data["file_id"]
            # Converter para int para garantir comparação correta (pode vir como string do JSON)
            if isinstance(job_file_id, str):
                try:
                    job_file_id = int(job_file_id)
                except (ValueError, TypeError):
                    continue
            # Usar o primeiro job encontrado (mais recente devido ao order_by)
            if job_file_id not in file_id_to_latest_job_status:
                file_id_to_latest_job_status[job_file_id] = job.status.value

    # Buscar hospitais dos arquivos para incluir hospital_name
    hospital_ids = {item.hospital_id for item in items}
    hospital_dict = {}
    if hospital_ids:
        hospital_query = select(Hospital).where(
            Hospital.tenant_id == membership.tenant_id,
            Hospital.id.in_(hospital_ids),
        )
        hospital_list = session.exec(hospital_query).all()
        hospital_dict = {h.id: h for h in hospital_list}

    # Construir resposta com can_delete, job_status, hospital_id e hospital_name
    file_responses = []
    for item in items:
        can_delete = item.id not in file_ids_with_completed_job
        job_status = file_id_to_latest_job_status.get(item.id)
        hospital = hospital_dict.get(item.hospital_id)
        hospital_name = hospital.name if hospital else f"Hospital {item.hospital_id}"
        # Criar FileResponse manualmente incluindo can_delete, job_status, hospital_id e hospital_name
        file_response = FileResponse(
            id=item.id,
            filename=item.filename,
            content_type=item.content_type,
            file_size=item.file_size,
            created_at=item.created_at,
            hospital_id=item.hospital_id,
            hospital_name=hospital_name,
            can_delete=can_delete,
            job_status=job_status,
        )
        file_responses.append(file_response)

    return FileListResponse(
        items=file_responses,
        total=total,
    )


@router.get("/file/{file_id}", response_model=FileDownloadResponse, tags=["File"])
def get_file(
    file_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Retorna informações do arquivo e URL presignada para download.
    """
    # Buscar arquivo
    file_model = session.get(File, file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Validar tenant_id
    if file_model.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Gerar URL presignada
    storage_service = StorageService()
    presigned_url = storage_service.get_file_presigned_url(
        s3_key=file_model.s3_key,
        expiration=3600,  # 1 hora
    )

    return FileDownloadResponse(
        id=file_model.id,
        filename=file_model.filename,
        content_type=file_model.content_type,
        presigned_url=presigned_url,
    )


@router.get("/file/{file_id}/download", tags=["File"])
def download_file(
    file_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Faz download direto do arquivo do MinIO.
    Retorna o arquivo como stream para o cliente.
    """
    # Buscar arquivo
    file_model = session.get(File, file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Validar tenant_id
    if file_model.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Obter arquivo do MinIO
    storage_service = StorageService()
    s3_client = storage_service.client

    try:
        # Obter objeto do S3/MinIO
        response = s3_client._client.get_object(
            Bucket=storage_service.config.bucket_name,
            Key=file_model.s3_key,
        )

        # Retornar como stream com inline para permitir visualização no navegador
        return StreamingResponse(
            response['Body'].iter_chunks(chunk_size=8192),
            media_type=file_model.content_type,
            headers={
                "Content-Disposition": f'inline; filename="{file_model.filename}"',
            },
        )
    except Exception as e:
        import logging
        logging.error(f"Erro ao fazer download do arquivo {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao fazer download do arquivo: {str(e)}")


@router.delete("/file/{file_id}", status_code=204, tags=["File"])
def delete_file(
    file_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Deleta arquivo do banco e do S3/MinIO.
    """
    # Buscar arquivo
    file_model = session.get(File, file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Validar tenant_id
    if file_model.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Deletar arquivo do S3/MinIO
    storage_service = StorageService()
    try:
        storage_service.delete_file(file_model.s3_key)
    except Exception as e:
        # Log erro mas continua com exclusão do banco (arquivo pode já ter sido deletado)
        import logging
        logging.warning(f"Erro ao deletar arquivo do S3 (continuando com exclusão do banco): {e}")
        # Em desenvolvimento, log mais detalhado
        if os.getenv("APP_ENV", "dev") == "dev":
            import traceback
            logging.warning(f"Traceback ao deletar do S3:\n{traceback.format_exc()}")

    # Deletar registro do banco
    try:
        session.delete(file_model)
        session.commit()
    except Exception as e:
        session.rollback()
        import logging
        import traceback
        error_detail = f"Erro ao deletar arquivo do banco: {str(e)}"
        if os.getenv("APP_ENV", "dev") == "dev":
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        logging.error(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)

    # Retornar 204 No Content
    return Response(status_code=204)


@router.post("/schedule/generate", response_model=ScheduleGenerateResponse, status_code=201, tags=["Schedule"])
async def schedule_generate(
    body: ScheduleGenerateRequest,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    # Validar período (intervalo meio-aberto [start, end))
    if body.period_end_at <= body.period_start_at:
        raise HTTPException(status_code=400, detail="period_end_at deve ser maior que period_start_at")
    if body.period_start_at.tzinfo is None or body.period_end_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="period_start_at/period_end_at devem ter timezone explícito")

    extract_job = session.get(Job, body.extract_job_id)
    if not extract_job:
        raise HTTPException(status_code=404, detail="Job de extração não encontrado")
    if extract_job.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if extract_job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job de extração deve estar COMPLETED")
    if not extract_job.result_data:
        raise HTTPException(status_code=400, detail="Job de extração não possui result_data")

    sv = ScheduleVersion(
        tenant_id=membership.tenant_id,
        name=body.name,
        period_start_at=body.period_start_at,
        period_end_at=body.period_end_at,
        status=ScheduleStatus.DRAFT,
        version_number=1,
        result_data=None,
    )
    session.add(sv)
    session.commit()
    session.refresh(sv)

    job = Job(
        tenant_id=membership.tenant_id,
        job_type=JobType.GENERATE_SCHEDULE,
        status=JobStatus.PENDING,
        input_data={
            "schedule_version_id": sv.id,
            "extract_job_id": body.extract_job_id,
            "allocation_mode": body.allocation_mode,
            "pros_by_sequence": body.pros_by_sequence,
        },
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Atualiza vínculo ScheduleVersion -> Job (útil para rastreabilidade)
    sv.job_id = job.id
    sv.updated_at = utc_now()
    session.add(sv)
    session.commit()

    redis_dsn = WorkerSettings.redis_dsn()
    try:
        redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
        await redis.enqueue_job("generate_schedule_job", job.id)
    except (RedisTimeoutError, RedisConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível (REDIS_URL={redis_dsn}): {str(e)}",
        ) from e

    return ScheduleGenerateResponse(job_id=job.id, schedule_version_id=sv.id)


# ============================================================================
# Hospital Endpoints
# ============================================================================

class HospitalCreate(PydanticBaseModel):
    name: str
    prompt: str

    @field_validator("name", "prompt")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode estar vazio")
        return v.strip()


class HospitalUpdate(PydanticBaseModel):
    name: str | None = None
    prompt: str | None = None

    @field_validator("name", "prompt")
    @classmethod
    def validate_not_empty(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Campo não pode estar vazio")
        return v.strip() if v else None


class HospitalResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    name: str
    prompt: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HospitalListResponse(PydanticBaseModel):
    items: list[HospitalResponse]
    total: int


@router.post("/hospital", response_model=HospitalResponse, status_code=201, tags=["Hospital"])
def create_hospital(
    body: HospitalCreate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo hospital (apenas admin).
    Hospital sempre pertence ao tenant atual (do membership).
    """
    # Verificar se já existe hospital com mesmo nome no tenant
    existing = session.exec(
        select(Hospital).where(
            Hospital.tenant_id == membership.tenant_id,
            Hospital.name == body.name,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Hospital com nome '{body.name}' já existe neste tenant",
        )

    hospital = Hospital(
        tenant_id=membership.tenant_id,
        name=body.name,
        prompt=body.prompt,
    )
    session.add(hospital)
    try:
        session.commit()
        session.refresh(hospital)
        return hospital
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Hospital com nome '{body.name}' já existe neste tenant",
        ) from e


@router.get("/hospital/list", response_model=HospitalListResponse, tags=["Hospital"])
def list_hospital(
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista todos os hospitais do tenant atual.
    """
    query = select(Hospital).where(Hospital.tenant_id == membership.tenant_id)
    items = session.exec(query.order_by(Hospital.name)).all()
    total = len(items)

    return HospitalListResponse(
        items=[HospitalResponse.model_validate(h) for h in items],
        total=total,
    )


@router.get("/hospital/{hospital_id}", response_model=HospitalResponse, tags=["Hospital"])
def get_hospital(
    hospital_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Obtém detalhes de um hospital específico.
    Valida que o hospital pertence ao tenant atual.
    """
    hospital = session.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital não encontrado")
    if hospital.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return hospital


@router.put("/hospital/{hospital_id}", response_model=HospitalResponse, tags=["Hospital"])
def update_hospital(
    hospital_id: int,
    body: HospitalUpdate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um hospital (apenas admin).
    Valida que o hospital pertence ao tenant atual.
    """
    hospital = session.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital não encontrado")
    if hospital.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Verificar se novo nome já existe (se estiver alterando)
    if body.name is not None and body.name != hospital.name:
        existing = session.exec(
            select(Hospital).where(
                Hospital.tenant_id == membership.tenant_id,
                Hospital.name == body.name,
                Hospital.id != hospital_id,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Hospital com nome '{body.name}' já existe neste tenant",
            )

    # Atualizar campos
    if body.name is not None:
        hospital.name = body.name
    if body.prompt is not None:
        hospital.prompt = body.prompt
    hospital.updated_at = utc_now()

    session.add(hospital)
    try:
        session.commit()
        session.refresh(hospital)
        return hospital
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Hospital com nome '{body.name}' já existe neste tenant",
        ) from e
