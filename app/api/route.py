import os
from datetime import datetime, timezone
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
from app.auth.dependencies import get_current_account
from app.model.user import Account
from app.storage.service import StorageService
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.worker.worker_settings import WorkerSettings


router = APIRouter()  # Sem tag padrão - cada endpoint define sua própria tag
router.include_router(auth_router)


def _isoformat_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/me", tags=["Auth"])
def get_me(account: Account = Depends(get_current_account)):
    """
    Retorna os dados da conta autenticada.
    Endpoint na raiz conforme checklist.
    """
    return {
        "id": account.id,
        "email": account.email,
        "name": account.name,
        "role": account.role,
        "tenant_id": account.tenant_id,
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
def create_tenant(tenant_data: TenantCreate, session: Session = Depends(get_session)):
    """Cria um novo tenant."""
    # Verifica se já existe um tenant com o mesmo slug
    existing = session.exec(select(Tenant).where(Tenant.slug == tenant_data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant com este slug já existe")

    tenant = Tenant(name=tenant_data.name, slug=tenant_data.slug, timezone=tenant_data.timezone)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    return tenant


class JobPingResponse(PydanticBaseModel):
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
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


@router.post("/job/ping", response_model=JobPingResponse, status_code=201, tags=["Job"])
async def create_ping_job(
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    if not account.tenant_id:
        raise HTTPException(status_code=400, detail="Account não possui tenant_id associado")

    job = Job(
        tenant_id=account.tenant_id,
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


@router.get("/job/{job_id}", response_model=JobResponse, tags=["Job"])
def get_job(
    job_id: int,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != account.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return job


class FileUploadResponse(PydanticBaseModel):
    file_id: int
    filename: str
    content_type: str
    file_size: int
    s3_url: str
    presigned_url: str

    class Config:
        from_attributes = True


@router.post("/file/upload", response_model=FileUploadResponse, status_code=201, tags=["File"])
def upload_file(
    file: UploadFile = FastAPIFile(...),
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """
    Faz upload de arquivo para MinIO/S3 e cria registro File no banco.

    Retorna file_id, s3_url e presigned_url para acesso ao arquivo.
    """
    if not account.tenant_id:
        raise HTTPException(
            status_code=400, detail="Account não possui tenant_id associado"
        )

    storage_service = StorageService()

    try:
        # Upload arquivo e criar registro
        file_model = storage_service.upload_imported_file(
            session=session,
            tenant_id=account.tenant_id,
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
