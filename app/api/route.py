import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlmodel import Session, select
from app.db.session import get_session
from app.model.tenant import Tenant
from pydantic import BaseModel as PydanticBaseModel, field_validator
from app.api.auth import router as auth_router
from app.api.schedule import router as schedule_router
from app.auth.dependencies import get_current_account, get_current_membership, require_role
from app.model.membership import Membership, MembershipRole, MembershipStatus
from app.model.user import Account
from app.storage.service import StorageService
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.schedule_version import ScheduleVersion, ScheduleStatus
from app.worker.worker_settings import WorkerSettings
from app.model.base import utc_now


router = APIRouter()  # Sem tag padrão - cada endpoint define sua própria tag
router.include_router(auth_router)
router.include_router(schedule_router)

_MAX_STALE_WINDOW = timedelta(hours=1)


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
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError("timezone inválido (esperado IANA, ex: America/Sao_Paulo)") from e
        return v


class TenantResponse(PydanticBaseModel):
    id: int
    name: str
    slug: str
    timezone: str
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

    tenant = Tenant(name=tenant_data.name, slug=tenant_data.slug, timezone=tenant_data.timezone)
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

    return tenant


class TenantInviteRequest(PydanticBaseModel):
    email: str
    role: str = "user"  # MVP: user/admin
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
    if role_raw not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="role inválida (esperado: user|admin)")
    role = MembershipRole.ADMIN if role_raw == "admin" else MembershipRole.USER

    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    account = session.exec(select(Account).where(Account.email == email)).first()
    if not account:
        account = Account(
            email=email,
            name=body.name or email,
            role="user",
            tenant_id=tenant.id,  # compatibilidade (até remover account.tenant_id)
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
        if membership.status in {MembershipStatus.REJECTED, MembershipStatus.REMOVED}:
            membership.status = MembershipStatus.PENDING
        if membership.status == MembershipStatus.PENDING:
            membership.role = role
        session.add(membership)
        session.commit()
        session.refresh(membership)
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
    session.commit()
    session.refresh(membership)
    return TenantInviteResponse(
        membership_id=membership.id,
        email=account.email,
        status=membership.status.value,
        role=membership.role.value,
    )


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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Faz upload de arquivo para MinIO/S3 e cria registro File no banco.

    Retorna file_id, s3_url e presigned_url para acesso ao arquivo.
    """
    storage_service = StorageService()

    try:
        # Upload arquivo e criar registro
        file_model = storage_service.upload_imported_file(
            session=session,
            tenant_id=membership.tenant_id,
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
