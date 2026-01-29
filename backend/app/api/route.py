import asyncio
import os
import logging
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

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
from pydantic import BaseModel as PydanticBaseModel, field_validator, model_validator
from app.api.auth import router as auth_router
from app.api.schedule import router as schedule_router
from app.auth.dependencies import get_current_account, get_current_member, require_role
from app.model.member import Member, MemberRole, MemberStatus
from app.model.audit_log import AuditLog
from app.model.account import Account
from app.storage.service import StorageService
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.demand import ScheduleStatus
from app.model.hospital import Hospital
from app.model.demand import Demand
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


def _sanitize_error_message(error: Exception, default_message: str = "Ocorreu um erro inesperado") -> str:
    """
    Sanitiza mensagens de erro removendo detalhes técnicos desnecessários.
    Remove SQL queries, stack traces, e outros detalhes que não são úteis para o usuário final.
    """
    error_str = str(error)

    # Se a mensagem contém SQL, tenta extrair apenas a parte relevante
    if "[SQL:" in error_str:
        # Remove a parte do SQL query
        parts = error_str.split("[SQL:")
        if parts:
            error_str = parts[0].strip()

    # Remove detalhes de parâmetros SQL
    if "[parameters:" in error_str:
        parts = error_str.split("[parameters:")
        if parts:
            error_str = parts[0].strip()

    # Remove referências a stack traces
    if "(Background on this error" in error_str:
        parts = error_str.split("(Background on this error")
        if parts:
            error_str = parts[0].strip()

    # Remove detalhes técnicos de psycopg
    if "psycopg.errors." in error_str:
        # Extrai apenas a parte após o último ponto, se houver
        if "DETAIL:" in error_str:
            # Tenta extrair a mensagem do DETAIL
            detail_parts = error_str.split("DETAIL:")
            if len(detail_parts) > 1:
                detail = detail_parts[1].split("[")[0].strip()
                if detail:
                    error_str = detail

    # Remove informações de constraint muito técnicas
    if "duplicate key value violates unique constraint" in error_str.lower():
        # Já tratado nos handlers específicos de IntegrityError
        pass

    # Limita o tamanho da mensagem
    max_length = 200
    if len(error_str) > max_length:
        error_str = error_str[:max_length] + "..."

    # Se a mensagem ficou vazia ou muito curta, usa a mensagem padrão
    if not error_str or len(error_str.strip()) < 10:
        return default_message

    return error_str.strip()


@router.get("/me", tags=["Auth"])
def get_me(
    account: Account = Depends(get_current_account),
    member: Member = Depends(get_current_member),
):
    """
    Retorna os dados da conta autenticada.
    Endpoint na raiz conforme checklist.

    Retorna name (privado) e member_name (público na clínica).
    """
    return {
        "id": account.id,
        "email": account.email,
        "name": account.name,  # Nome privado do usuário
        "member_name": member.name,  # Nome público na clínica (pode ser NULL)
        "role": member.role.value,
        "tenant_id": member.tenant_id,
        "auth_provider": account.auth_provider,
        "created_at": _isoformat_utc(account.created_at),
        "updated_at": _isoformat_utc(account.updated_at),
    }


class AccountOption(PydanticBaseModel):
    id: int
    email: str
    name: str


class AccountResponse(PydanticBaseModel):
    id: int
    email: str
    name: str
    role: str
    tenant_id: int
    auth_provider: str
    created_at: str
    updated_at: str


class AccountListResponse(PydanticBaseModel):
    items: list[AccountResponse]
    total: int


class AccountCreate(PydanticBaseModel):
    name: str
    email: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo nome não pode estar vazio")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo email não pode estar vazio")
        # Normalizar email para lowercase
        return v.strip().lower()


class AccountUpdate(PydanticBaseModel):
    name: str | None = None
    email: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Campo nome não pode estar vazio")
        return v.strip() if v else None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip() if isinstance(v, str) else v
        if not stripped:
            return None
        # Normalizar email para lowercase
        return stripped.lower()


@router.post("/account", response_model=AccountResponse, status_code=201, tags=["Account"])
def create_account(
    body: AccountCreate,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo account (apenas admin).
    """
    try:
        logger.info(f"Criando account: email={body.email}, tenant_id={member.tenant_id}")

        # Verificar se já existe account com este email
        existing_account = session.exec(
            select(Account).where(Account.email == body.email)
        ).first()
        if existing_account:
            logger.warning(f"Account com email '{body.email}' já existe (id={existing_account.id})")
            raise HTTPException(
                status_code=409,
                detail=f"Account com email '{body.email}' já existe",
            )

        # Criar account
        account = Account(
            email=body.email,
            name=body.name,
            role="account",
            auth_provider="invite",
        )
        session.add(account)
        session.commit()
        session.refresh(account)

        return AccountResponse(
            id=account.id,
            email=account.email,
            name=account.name,
            role=account.role,
            tenant_id=member.tenant_id,
            auth_provider=account.auth_provider,
            created_at=_isoformat_utc(account.created_at),
            updated_at=_isoformat_utc(account.updated_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao criar account: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar account: {str(e)}",
        ) from e


@router.get("/account/list", response_model=AccountListResponse, tags=["Account"])
def list_accounts(
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """
    Lista account list do tenant atual (via Member ACTIVE) com paginação.
    """
    try:
        # Query base para buscar (LEFT JOIN para incluir members sem Account)
        base_query = (
            select(Member, Account)
            .outerjoin(Account, Member.account_id == Account.id)
            .where(
                Member.tenant_id == member.tenant_id,
                Member.status == MemberStatus.ACTIVE,
            )
        )

        # Contar total
        count_query = select(func.count(Member.id)).where(
            Member.tenant_id == member.tenant_id,
            Member.status == MemberStatus.ACTIVE,
        )
        total = session.exec(count_query).one()

        # Buscar account list com paginação
        # Filtrar apenas members com Account (não mostrar convites pendentes sem Account)
        members = session.exec(
            base_query
            .where(Account.id.isnot(None))  # Apenas members com Account vinculado
            .order_by(Account.name)
            .limit(limit)
            .offset(offset)
        ).all()

        account_list = []
        for member_obj, account in members:
            # Account não pode ser None aqui devido ao filtro acima
            if account:
                account_list.append(AccountResponse(
                    id=account.id,
                    email=account.email,
                    name=account.name,
                    role=account.role,
                    tenant_id=member.tenant_id,
                    auth_provider=account.auth_provider,
                    created_at=_isoformat_utc(account.created_at),
                    updated_at=_isoformat_utc(account.updated_at),
                ))

        return AccountListResponse(
            items=account_list,
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar account list: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar account list: {str(e)}",
        ) from e


@router.put("/account/{account_id}", response_model=AccountResponse, tags=["Account"])
def update_account(
    account_id: int,
    body: AccountUpdate,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um account (apenas admin).
    Valida que o account pertence ao tenant atual (via Member ACTIVE).
    """
    try:
        logger.info(f"Atualizando account: id={account_id}, tenant_id={member.tenant_id}")

        account = session.get(Account, account_id)
        if not account:
            logger.warning(f"Account não encontrado: id={account_id}")
            raise HTTPException(status_code=404, detail="Account não encontrado")

        # Validar que o account pertence ao tenant atual via Member
        account_member = session.exec(
            select(Member).where(
                Member.account_id == account_id,
                Member.tenant_id == member.tenant_id,
                Member.status == MemberStatus.ACTIVE,
            )
        ).first()
        if not account_member:
            logger.warning(f"Account {account_id} não possui member ACTIVE no tenant {member.tenant_id}")
            raise HTTPException(
                status_code=403,
                detail=f"Account {account_id} não pertence ao tenant atual",
            )

        # Verificar se email está sendo alterado e se já existe outro com o mesmo email
        if body.email is not None and body.email != account.email:
            existing = session.exec(
                select(Account).where(
                    Account.email == body.email,
                    Account.id != account_id,
                )
            ).first()
            if existing:
                logger.warning(f"Account com email '{body.email}' já existe (id={existing.id})")
                raise HTTPException(
                    status_code=409,
                    detail=f"Account com email '{body.email}' já existe",
                )

        # Atualizar campos
        if body.name is not None:
            account.name = body.name
        if body.email is not None:
            account.email = body.email

        account.updated_at = utc_now()
        session.add(account)
        session.commit()
        session.refresh(account)

        logger.info(f"Account atualizado com sucesso: id={account.id}")
        return AccountResponse(
            id=account.id,
            email=account.email,
            name=account.name,
            role=account.role,
            tenant_id=member.tenant_id,
            auth_provider=account.auth_provider,
            created_at=_isoformat_utc(account.created_at),
            updated_at=_isoformat_utc(account.updated_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar account: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar account: {str(e)}",
        ) from e


@router.delete("/account/{account_id}", status_code=204, tags=["Account"])
def delete_account(
    account_id: int,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove um account do tenant atual removendo o Member (apenas admin).
    Valida que o account pertence ao tenant atual (via Member ACTIVE).
    """
    try:
        logger.info(f"Removendo account: id={account_id}, tenant_id={member.tenant_id}")

        account = session.get(Account, account_id)
        if not account:
            logger.warning(f"Account não encontrado: id={account_id}")
            raise HTTPException(status_code=404, detail="Account não encontrado")

        # Validar que o account pertence ao tenant atual via Member
        account_member = session.exec(
            select(Member).where(
                Member.account_id == account_id,
                Member.tenant_id == member.tenant_id,
                Member.status == MemberStatus.ACTIVE,
            )
        ).first()
        if not account_member:
            logger.warning(f"Account {account_id} não possui member ACTIVE no tenant {member.tenant_id}")
            raise HTTPException(
                status_code=403,
                detail=f"Account {account_id} não pertence ao tenant atual",
            )

        # Validar regra de segurança: não permitir remover o último member ACTIVE de um account
        active_count = session.exec(
            select(func.count())
            .select_from(Member)
            .where(
                Member.account_id == account_id,
                Member.status == MemberStatus.ACTIVE,
            )
        ).one()
        if int(active_count or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Não é permitido remover o último member ACTIVE da conta. "
                    "Antes, garanta outro acesso (ex.: outro tenant) ou transfira permissões."
                ),
            )

        # Remover member (soft-delete: status -> REMOVED)
        prev_status = account_member.status
        account_member.status = MemberStatus.REMOVED
        account_member.updated_at = utc_now()
        session.add(account_member)
        session.commit()
        session.refresh(account_member)

        # Log de auditoria
        _try_write_audit_log(
            session,
            AuditLog(
                tenant_id=member.tenant_id,
                actor_account_id=member.account_id,
                member_id=account_member.id,
                event_type="member_status_changed",
                data={
                    "target_account_id": account_id,
                    "from_status": prev_status.value,
                    "to_status": account_member.status.value,
                },
            ),
        )

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao remover account: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao remover account: {str(e)}",
        ) from e


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


class TenantUpdate(PydanticBaseModel):
    name: str | None = None
    slug: str | None = None
    timezone: str | None = None
    locale: str | None = None
    currency: str | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError("timezone inválido (esperado IANA, ex: America/Sao_Paulo)") from e
        return v

    @field_validator("locale", "currency", "name", "slug")
    @classmethod
    def validate_string_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v or not v.strip():
            raise ValueError("campo não pode estar vazio")
        return v.strip()


class TenantListResponse(PydanticBaseModel):
    items: list[TenantResponse]
    total: int


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
    """Cria um novo tenant e cria Member ADMIN para o criador."""
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

    member = Member(
        tenant_id=tenant.id,
        account_id=account.id,
        role=MemberRole.ADMIN,
        status=MemberStatus.ACTIVE,
    )
    session.add(member)
    session.commit()

    # Criar hospital default para o tenant
    create_default_hospital_for_tenant(session, tenant.id)


    return tenant


@router.get("/tenant/list", response_model=TenantListResponse, tags=["Tenant"])
def list_tenants(
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """
    Lista todos os tenants (apenas admin) com paginação.
    """
    try:
        logger.info(f"Listando tenants, limit={limit}, offset={offset}")
        query = select(Tenant)

        # Contar total antes de aplicar paginação
        count_query = select(func.count(Tenant.id))
        total = session.exec(count_query).one()

        # Aplicar ordenação e paginação
        items = session.exec(query.order_by(Tenant.name).limit(limit).offset(offset)).all()

        response_items = []
        for t in items:
            response_items.append(TenantResponse(
                id=t.id,
                name=t.name,
                slug=t.slug,
                timezone=t.timezone,
                locale=t.locale,
                currency=t.currency,
                created_at=t.created_at,
                updated_at=t.updated_at,
            ))

        return TenantListResponse(
            items=response_items,
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar tenants: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar tenants: {str(e)}",
        ) from e


@router.get("/tenant/me", response_model=TenantResponse, tags=["Tenant"])
def get_current_tenant_info(
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Retorna informações do tenant atual do usuário autenticado.
    """
    tenant = session.get(Tenant, member.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return tenant


@router.put("/tenant/{tenant_id}", response_model=TenantResponse, tags=["Tenant"])
def update_tenant(
    tenant_id: int,
    body: TenantUpdate,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um tenant (apenas admin).
    """
    try:
        logger.info(f"Atualizando tenant: id={tenant_id}")

        tenant = session.get(Tenant, tenant_id)
        if not tenant:
            logger.warning(f"Tenant não encontrado: id={tenant_id}")
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        # Verificar se slug está sendo alterado e se já existe outro com o mesmo slug
        if body.slug is not None and body.slug != tenant.slug:
            existing = session.exec(
                select(Tenant).where(
                    Tenant.slug == body.slug,
                    Tenant.id != tenant_id,
                )
            ).first()
            if existing:
                logger.warning(f"Tenant com slug '{body.slug}' já existe (id={existing.id})")
                raise HTTPException(
                    status_code=409,
                    detail=f"Tenant com slug '{body.slug}' já existe",
                )

        # Atualizar campos
        if body.name is not None:
            tenant.name = body.name
        if body.slug is not None:
            tenant.slug = body.slug
        if body.timezone is not None:
            tenant.timezone = body.timezone
        if body.locale is not None:
            tenant.locale = body.locale
        if body.currency is not None:
            tenant.currency = body.currency

        tenant.updated_at = utc_now()
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            timezone=tenant.timezone,
            locale=tenant.locale,
            currency=tenant.currency,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar tenant: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar tenant: {str(e)}",
        ) from e


@router.delete("/tenant/{tenant_id}", status_code=204, tags=["Tenant"])
def delete_tenant(
    tenant_id: int,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove um tenant (apenas admin).
    """
    try:
        logger.info(f"Removendo tenant: id={tenant_id}")

        tenant = session.get(Tenant, tenant_id)
        if not tenant:
            logger.warning(f"Tenant não encontrado: id={tenant_id}")
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        # Verificar se há members ativos para este tenant
        active_members = session.exec(
            select(func.count())
            .select_from(Member)
            .where(
                Member.tenant_id == tenant_id,
                Member.status == MemberStatus.ACTIVE,
            )
        ).one()

        if int(active_members or 0) > 0:
            raise HTTPException(
                status_code=409,
                detail="Não é permitido remover um tenant que possui members ativos. Remova ou desative os members primeiro.",
            )

        session.delete(tenant)
        session.commit()

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao remover tenant: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao remover tenant: {str(e)}",
        ) from e


class TenantInviteRequest(PydanticBaseModel):
    email: str
    role: str = "account"  # MVP: account/admin
    name: str | None = None


class TenantInviteResponse(PydanticBaseModel):
    member_id: int
    email: str
    status: str
    role: str


@router.post("/tenant/{tenant_id}/invite", response_model=TenantInviteResponse, status_code=201, tags=["Tenant"])
def invite_to_tenant(
    tenant_id: int,
    body: TenantInviteRequest,
    admin_member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria/atualiza um convite (Member PENDING) para um email no tenant atual.

    Regras:
      - O caller deve ser ADMIN e o tenant do token deve bater com o tenant_id do path.
      - NÃO cria Account - apenas cria Member PENDING com account_id NULL.
      - Idempotente por (tenant_id, email) quando account_id é NULL, ou (tenant_id, account_id) quando account existe.
    """
    if admin_member.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    role_raw = body.role.strip().lower()
    if role_raw not in {"account", "admin"}:
        raise HTTPException(status_code=400, detail="role inválida (esperado: account|admin)")
    role = MemberRole.ADMIN if role_raw == "admin" else MemberRole.ACCOUNT

    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Verificar se Account já existe (pode ter sido criado por outro tenant ou login anterior)
    account = session.exec(select(Account).where(Account.email == email)).first()

    # Buscar member existente:
    # - Se account existe: buscar por (tenant_id, account_id)
    # - Se account não existe: buscar por (tenant_id, email) onde account_id IS NULL
    if account:
        member_existing = session.exec(
            select(Member).where(
                Member.tenant_id == tenant.id,
                Member.account_id == account.id,
            )
        ).first()
    else:
        member_existing = session.exec(
            select(Member).where(
                Member.tenant_id == tenant.id,
                Member.email == email,
                Member.account_id.is_(None),
            )
        ).first()

    if member_existing:
        # Não duplica. Se já estiver ACTIVE, apenas devolve.
        prev_status = member_existing.status
        prev_role = member_existing.role
        if member_existing.status in {MemberStatus.REJECTED, MemberStatus.REMOVED}:
            member_existing.status = MemberStatus.PENDING
        if member_existing.status == MemberStatus.PENDING:
            member_existing.role = role
        # Atualizar member.name se fornecido no body (não sobrescrever se já existir)
        if body.name and (member_existing.name is None or member_existing.name == ""):
            member_existing.name = body.name
        member_existing.updated_at = utc_now()
        session.add(member_existing)
        session.commit()
        session.refresh(member_existing)

        if prev_status != member_existing.status or prev_role != member_existing.role:
            _try_write_audit_log(
                session,
                AuditLog(
                    tenant_id=tenant.id,
                    actor_account_id=admin_member.account_id,
                    member_id=member_existing.id,
                    event_type="member_invited",
                    data={
                        "target_account_id": account.id if account else None,
                        "email": account.email if account else email,
                        "from_status": prev_status.value,
                        "to_status": member_existing.status.value,
                        "from_role": prev_role.value,
                        "to_role": member_existing.role.value,
                    },
                ),
            )
        return TenantInviteResponse(
            member_id=member_existing.id,
            email=account.email if account else email,
            status=member_existing.status.value,
            role=member_existing.role.value,
        )

    member_new = Member(
        tenant_id=tenant.id,
        account_id=account.id if account else None,
        role=role,
        status=MemberStatus.PENDING,
        name=body.name,  # Salvar name em member.name (não em account.name)
        email=email,  # Sempre usar email do body
    )
    session.add(member_new)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Member duplicado (tenant_id, email) não permitido",
        ) from e
    session.refresh(member_new)
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=tenant.id,
            actor_account_id=admin_member.account_id,
            member_id=member_new.id,
            event_type="member_invited",
            data={
                "target_account_id": account.id if account else None,
                "email": email,
                "from_status": None,
                "to_status": member_new.status.value,
                "from_role": None,
                "to_role": member_new.role.value,
            },
        ),
    )
    return TenantInviteResponse(
        member_id=member_new.id,
        email=email,
        status=member_new.status.value,
        role=member_new.role.value,
    )


class MemberRemoveResponse(PydanticBaseModel):
    member_id: int
    status: str


@router.post(
    "/tenant/{tenant_id}/members/{member_id}/remove",
    response_model=MemberRemoveResponse,
    status_code=200,
    tags=["Tenant"],
)
def remove_member(
    tenant_id: int,
    member_id: int,
    admin_member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove (soft-delete) um member do tenant (status -> REMOVED).

    Regra de segurança:
      - não permitir remover o último member ACTIVE de um account.
    """
    if admin_member.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    member_to_remove = session.get(Member, member_id)
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="Member não encontrado")
    if member_to_remove.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if member_to_remove.status == MemberStatus.ACTIVE:
        active_count = session.exec(
            select(func.count())
            .select_from(Member)
            .where(
                Member.account_id == member_to_remove.account_id,
                Member.status == MemberStatus.ACTIVE,
            )
        ).one()
        if int(active_count or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Não é permitido remover o último member ACTIVE da conta. "
                    "Antes, garanta outro acesso (ex.: outro tenant) ou transfira permissões."
                ),
            )

    prev_status = member_to_remove.status
    member_to_remove.status = MemberStatus.REMOVED
    member_to_remove.updated_at = utc_now()
    session.add(member_to_remove)
    session.commit()
    session.refresh(member_to_remove)
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=tenant_id,
            actor_account_id=admin_member.account_id,
            member_id=member_to_remove.id,
            event_type="member_status_changed",
            data={
                "from_status": prev_status.value,
                "to_status": member_to_remove.status.value,
                "target_account_id": member_to_remove.account_id,
            },
        ),
    )
    return MemberRemoveResponse(member_id=member_to_remove.id, status=member_to_remove.status.value)


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
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    job = Job(
                    tenant_id=member.tenant_id,
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
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    file_model = session.get(File, body.file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="File não encontrado")
    if file_model.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    job = Job(
                    tenant_id=member.tenant_id,
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
    started_at_from: Optional[str] = Query(None, description="Filtrar jobs iniciados a partir desta data (ISO 8601)"),
    started_at_to: Optional[str] = Query(None, description="Filtrar jobs iniciados até esta data (ISO 8601)"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    member: Member = Depends(get_current_member),
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

    # Parsear datas de filtro
    started_from_dt = None
    if started_at_from:
        try:
            started_from_dt = datetime.fromisoformat(started_at_from.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Data inválida para started_at_from: {started_at_from}")

    started_to_dt = None
    if started_at_to:
        try:
            started_to_dt = datetime.fromisoformat(started_at_to.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Data inválida para started_at_to: {started_at_to}")

    # Query base
    query = select(Job).where(Job.tenant_id == member.tenant_id)
    if job_type_enum:
        query = query.where(Job.job_type == job_type_enum)
    if status_enum:
        query = query.where(Job.status == status_enum)
    if started_from_dt:
        query = query.where(Job.started_at >= started_from_dt)  # type: ignore[attr-defined]
    if started_to_dt:
        query = query.where(Job.started_at <= started_to_dt)  # type: ignore[attr-defined]

    # Contar total antes de aplicar paginação
    count_query = select(func.count(Job.id)).where(Job.tenant_id == member.tenant_id)
    if job_type_enum:
        count_query = count_query.where(Job.job_type == job_type_enum)
    if status_enum:
        count_query = count_query.where(Job.status == status_enum)
    if started_from_dt:
        count_query = count_query.where(Job.started_at >= started_from_dt)  # type: ignore[attr-defined]
    if started_to_dt:
        count_query = count_query.where(Job.started_at <= started_to_dt)  # type: ignore[attr-defined]
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
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return job


class JobUpdate(PydanticBaseModel):
    result_data: dict | None = None


@router.put("/job/{job_id}", response_model=JobResponse, tags=["Job"])
def update_job(
    job_id: int,
    body: JobUpdate,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Atualiza um job (apenas result_data).
    Valida que o job pertence ao tenant atual.
    """
    try:
        logger.info(f"Atualizando job id={job_id} para tenant_id={member.tenant_id}")

        job = session.get(Job, job_id)
        if not job:
            logger.warning(f"Job não encontrado: id={job_id}")
            raise HTTPException(status_code=404, detail="Job não encontrado")
        if job.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: job.tenant_id={job.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Atualizar result_data se fornecido
        if body.result_data is not None:
            job.result_data = body.result_data
            logger.info(f"result_data atualizado para job id={job_id}")

        job.updated_at = utc_now()

        session.add(job)
        session.commit()
        session.refresh(job)
        logger.info(f"Job atualizado com sucesso: id={job.id}")
        return job
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar job: {str(e)}",
        ) from e


@router.get("/job/{job_id}/stream", tags=["Job"])
async def stream_job_status(
    job_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Stream SSE (Server-Sent Events) para aguardar conclusão de um job.

    O cliente abre esta conexão e recebe um evento quando o job terminar
    (status COMPLETED ou FAILED). A conexão fecha automaticamente após
    enviar o evento de conclusão.

    Eventos enviados:
    - event: status, data: {"status": "PENDING"|"RUNNING"|"COMPLETED"|"FAILED", "result_data": ...}

    Uso no frontend:
    ```javascript
    const eventSource = new EventSource(`/api/job/${jobId}/stream`);
    eventSource.addEventListener('status', (e) => {
        const data = JSON.parse(e.data);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            eventSource.close();
            // Recarregar dados...
        }
    });
    ```
    """
    import json

    # Validar acesso ao job
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    async def event_generator():
        """Gerador de eventos SSE que aguarda conclusão do job."""
        # Backoff progressivo: começa em 1s, aumenta até máximo de 5s
        min_interval = 1.0
        max_interval = 5.0
        check_interval = min_interval
        # Timeout máximo (5 minutos)
        max_wait_seconds = 300
        elapsed = 0.0
        check_count = 0

        while elapsed < max_wait_seconds:
            # Buscar status atualizado do job (nova sessão para evitar cache)
            from app.db.session import get_session_context
            with get_session_context() as fresh_session:
                current_job = fresh_session.get(Job, job_id)
                if not current_job:
                    # Job foi deletado
                    yield f"event: error\ndata: {json.dumps({'error': 'Job não encontrado'})}\n\n"
                    return

                status = current_job.status.value
                result_data = current_job.result_data

                # Enviar evento de status
                event_data = {"status": status, "result_data": result_data}
                yield f"event: status\ndata: {json.dumps(event_data)}\n\n"

                # Se job terminou, encerrar stream
                if current_job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    return

            # Aguardar antes de próxima verificação
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            check_count += 1

            # Backoff progressivo: aumenta intervalo a cada 3 verificações
            # 1s (checks 1-3) → 2s (checks 4-6) → 3s (checks 7-9) → 4s (checks 10-12) → 5s (checks 13+)
            if check_count % 3 == 0 and check_interval < max_interval:
                check_interval = min(check_interval + 1.0, max_interval)

        # Timeout - enviar evento de timeout
        yield f"event: timeout\ndata: {json.dumps({'error': 'Timeout aguardando job'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desabilita buffering no nginx
        },
    )


@router.post("/job/{job_id}/cancel", response_model=JobResponse, tags=["Job"])
def cancel_job(
    job_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Cancela um job, mudando seu status para FAILED.
    Valida que o job pertence ao tenant atual.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Se já está COMPLETED ou FAILED, não faz nada
    if job.status == JobStatus.COMPLETED:
        return job
    if job.status == JobStatus.FAILED:
        return job

    # Marcar como FAILED
    job.status = JobStatus.FAILED
    job.error_message = "Cancelado manualmente pelo usuário"
    if not job.completed_at:
        job.completed_at = utc_now()
    job.updated_at = utc_now()

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


@router.delete("/job/{job_id}", status_code=204, tags=["Job"])
def delete_job(
    job_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Exclui um job que está COMPLETED ou FAILED.
    Valida que o job pertence ao tenant atual.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Só permite excluir jobs que já terminaram (COMPLETED ou FAILED)
    if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir job com status {job.status}. Apenas jobs COMPLETED ou FAILED podem ser excluídos."
        )

    # Excluir job
    session.delete(job)
    session.commit()

    return Response(status_code=204)


@router.post("/job/{job_id}/requeue", response_model=JobRequeueResponse, status_code=202, tags=["Job"])
async def requeue_job(
    job_id: int,
    body: JobRequeueRequest,
    _admin: Member = Depends(require_role("admin")),
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
    hospital_color: Optional[str] = None  # Cor do hospital em formato hexadecimal (#RRGGBB)
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
    schedule_id: Optional[int] = None  # legado; após refatoração worker atualiza Demand(s)


@router.post("/file/upload", response_model=FileUploadResponse, status_code=201, tags=["File"])
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    hospital_id: int = Query(..., description="ID do hospital (obrigatório)"),
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Faz upload de arquivo para MinIO/S3 e cria registro File no banco.
    Requer hospital_id obrigatório.
    Após upload bem-sucedido, enfileira job para gerar thumbnail.

    Retorna file_id, s3_url e presigned_url para acesso ao arquivo.
    """
    # Validar que o hospital existe e pertence ao tenant
    hospital = session.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital não encontrado")
    if hospital.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    storage_service = StorageService()

    try:
        # Upload arquivo e criar registro
        file_model = storage_service.upload_imported_file(
            session=session,
            tenant_id=member.tenant_id,
            hospital_id=hospital_id,
            file=file,
        )

        # Gerar URL presignada
        presigned_url = storage_service.get_file_presigned_url(
            s3_key=file_model.s3_key,
            expiration=3600,  # 1 hora
        )

        # Enfileirar job para gerar thumbnail
        try:
            thumbnail_job = Job(
                tenant_id=member.tenant_id,
                job_type=JobType.GENERATE_THUMBNAIL,
                status=JobStatus.PENDING,
                input_data={"file_id": file_model.id},
            )
            session.add(thumbnail_job)
            session.commit()
            session.refresh(thumbnail_job)

            redis_dsn = WorkerSettings.redis_dsn()
            redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
            await redis.enqueue_job("generate_thumbnail_job", thumbnail_job.id)
        except (RedisTimeoutError, RedisConnectionError) as e:
            # Log erro mas não falha o upload
            logger.warning(f"Erro ao enfileirar job de thumbnail (file_id={file_model.id}): {e}")
        except Exception as e:
            # Log erro mas não falha o upload
            logger.warning(f"Erro ao criar/enfileirar job de thumbnail (file_id={file_model.id}): {e}")

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
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Lista arquivos do tenant atual, com filtros opcionais por período, hospital e paginação.

    Filtra exclusivamente pelo campo created_at (não usa uploaded_at ou updated_at).
    Sempre filtra por tenant_id do JWT (via member).
    Ordena por created_at decrescente.
    Retorna hospital_id e hospital_name para cada arquivo.
    """
    # Validar hospital_id se fornecido
    if hospital_id is not None:
        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != member.tenant_id:
            raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

    # Query base - sempre filtrar por tenant_id
    query = select(File).where(File.tenant_id == member.tenant_id)

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
    count_query = select(func.count(File.id)).where(File.tenant_id == member.tenant_id)
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
        Job.tenant_id == member.tenant_id,
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
        Job.tenant_id == member.tenant_id,
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
            Hospital.tenant_id == member.tenant_id,
            Hospital.id.in_(hospital_ids),
        )
        hospital_list = session.exec(hospital_query).all()
        hospital_dict = {h.id: h for h in hospital_list}

    # Construir resposta com can_delete, job_status, hospital_id, hospital_name e hospital_color
    file_responses = []
    for item in items:
        can_delete = item.id not in file_ids_with_completed_job
        job_status = file_id_to_latest_job_status.get(item.id)
        hospital = hospital_dict.get(item.hospital_id)
        hospital_name = hospital.name if hospital else f"Hospital {item.hospital_id}"
        hospital_color = hospital.color if hospital else None
        # Criar FileResponse manualmente incluindo can_delete, job_status, hospital_id, hospital_name e hospital_color
        file_response = FileResponse(
            id=item.id,
            filename=item.filename,
            content_type=item.content_type,
            file_size=item.file_size,
            created_at=item.created_at,
            hospital_id=item.hospital_id,
            hospital_name=hospital_name,
            hospital_color=hospital_color,
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
    member: Member = Depends(get_current_member),
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
    if file_model.tenant_id != member.tenant_id:
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
    member: Member = Depends(get_current_member),
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
    if file_model.tenant_id != member.tenant_id:
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


@router.get("/file/{file_id}/thumbnail", tags=["File"])
def get_file_thumbnail(
    file_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Retorna thumbnail WebP 500x500 do arquivo.
    Retorna 404 se thumbnail não existir (frontend exibe fallback).
    """
    # Buscar arquivo
    file_model = session.get(File, file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Validar tenant_id
    if file_model.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Calcular thumbnail_key
    thumbnail_key = file_model.s3_key + ".thumbnail.webp"

    # Obter storage service
    storage_service = StorageService()
    s3_client = storage_service.client

    # Tentar obter thumbnail do MinIO
    try:
        exists = s3_client.file_exists(thumbnail_key)
        logger.info(f"[THUMBNAIL] Thumbnail existe? {exists} (key={thumbnail_key})")
        if exists:
            # Thumbnail existe: retornar stream
            response = s3_client._client.get_object(
                Bucket=storage_service.config.bucket_name,
                Key=thumbnail_key,
            )
            return StreamingResponse(
                response['Body'].iter_chunks(chunk_size=8192),
                media_type="image/webp",
                headers={
                    "Cache-Control": "private, max-age=3600",
                },
            )
        else:
            pass  # Thumbnail não existe, será retornado 404 abaixo
    except Exception as e:
        logger.error(f"[THUMBNAIL] Erro ao obter thumbnail (file_id={file_id}, thumbnail_key={thumbnail_key}): {e}", exc_info=True)

    # Thumbnail não existe: retornar 404 (frontend exibe fallback)
    raise HTTPException(
        status_code=404,
        detail=f"Thumbnail não disponível (key={thumbnail_key})",
    )


@router.delete("/file/{file_id}", status_code=204, tags=["File"])
def delete_file(
    file_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Exclui arquivo do banco e do S3/MinIO.
    """
    # Buscar arquivo
    file_model = session.get(File, file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Validar tenant_id
    if file_model.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Excluir arquivo do S3/MinIO
    storage_service = StorageService()
    try:
        storage_service.delete_file(file_model.s3_key)
    except Exception as e:
        # Log erro mas continua com exclusão do banco (arquivo pode já ter sido deletado)
        logger.warning(f"Erro ao excluir arquivo do S3 (continuando com exclusão do banco): {e}")
        # Em desenvolvimento, log mais detalhado
        if os.getenv("APP_ENV", "dev") == "dev":
            logger.warning(f"Traceback ao excluir do S3:\n{traceback.format_exc()}")

    # Excluir thumbnail do S3/MinIO (se existir)
    thumbnail_key = file_model.s3_key + ".thumbnail.webp"
    try:
        s3_client = storage_service.client
        if s3_client.file_exists(thumbnail_key):
            storage_service.delete_file(thumbnail_key)
            logger.info(f"[DELETE] Thumbnail excluído: {thumbnail_key}")
    except Exception as e:
        # Log erro mas continua (thumbnail pode não existir ou já ter sido deletado)
        import logging
        logging.warning(f"Erro ao excluir thumbnail do S3 (continuando): {e}")

    # Excluir registro do banco
    try:
        session.delete(file_model)
        session.commit()
    except Exception as e:
        session.rollback()
        error_detail = f"Erro ao excluir arquivo do banco: {str(e)}"
        if os.getenv("APP_ENV", "dev") == "dev":
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)

    # Retornar 204 No Content
    return Response(status_code=204)


@router.post("/schedule/generate", response_model=ScheduleGenerateResponse, status_code=201, tags=["Schedule"])
async def schedule_generate(
    body: ScheduleGenerateRequest,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """Gera escala a partir de job de extração (modo from_extract). Cria apenas Job; worker não persiste em Demand (sem demand_id)."""
    if body.period_end_at <= body.period_start_at:
        raise HTTPException(status_code=400, detail="period_end_at deve ser maior que period_start_at")
    if body.period_start_at.tzinfo is None or body.period_end_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="period_start_at/period_end_at devem ter timezone explícito")

    extract_job = session.get(Job, body.extract_job_id)
    if not extract_job:
        raise HTTPException(status_code=404, detail="Job de extração não encontrado")
    if extract_job.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if extract_job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job de extração deve estar COMPLETED")
    if not extract_job.result_data:
        raise HTTPException(status_code=400, detail="Job de extração não possui result_data")

    job = Job(
        tenant_id=member.tenant_id,
        job_type=JobType.GENERATE_SCHEDULE,
        status=JobStatus.PENDING,
        input_data={
            "mode": "from_extract",
            "extract_job_id": body.extract_job_id,
            "period_start_at": body.period_start_at.isoformat(),
            "period_end_at": body.period_end_at.isoformat(),
            "name": body.name,
            "version_number": 1,
            "allocation_mode": body.allocation_mode,
            "pros_by_sequence": body.pros_by_sequence,
        },
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    redis_dsn = WorkerSettings.redis_dsn()
    try:
        redis = await create_pool(RedisSettings.from_dsn(redis_dsn))
        await redis.enqueue_job("generate_schedule_job", job.id)
    except (RedisTimeoutError, RedisConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível (REDIS_URL={redis_dsn}): {str(e)}",
        ) from e

    return ScheduleGenerateResponse(job_id=job.id, schedule_id=None)


# ============================================================================
# Hospital Endpoints
# ============================================================================

class HospitalCreate(PydanticBaseModel):
    name: str
    prompt: str | None = None
    color: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode estar vazio")
        return v.strip()

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip() if isinstance(v, str) else v
        return None if not stripped else stripped

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip() if isinstance(v, str) else v
        if not stripped:
            return None
        # Validar formato hexadecimal (#RRGGBB)
        if not stripped.startswith('#'):
            raise ValueError("Cor deve começar com #")
        hex_part = stripped[1:]
        if len(hex_part) != 6:
            raise ValueError("Cor deve ter 6 dígitos hexadecimais após o #")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Cor deve conter apenas caracteres hexadecimais válidos")
        return stripped.upper()


class HospitalUpdate(PydanticBaseModel):
    name: str | None = None
    prompt: str | None = None
    color: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Campo nome não pode estar vazio")
        return v.strip() if v else None

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip() if isinstance(v, str) else v
        return None if not stripped else stripped

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip() if isinstance(v, str) else v
        if not stripped:
            return None
        # Validar formato hexadecimal (#RRGGBB)
        if not stripped.startswith('#'):
            raise ValueError("Cor deve começar com #")
        hex_part = stripped[1:]
        if len(hex_part) != 6:
            raise ValueError("Cor deve ter 6 dígitos hexadecimais após o #")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Cor deve conter apenas caracteres hexadecimais válidos")
        return stripped.upper()


class HospitalResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    name: str
    prompt: str | None
    color: str | None
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
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo hospital (apenas admin).
    Hospital sempre pertence ao tenant atual (do member).
    """
    try:
        logger.info(f"Criando hospital: name={body.name}, prompt={'presente' if body.prompt else 'None/vazio'}, tenant_id={member.tenant_id}")

        # Verificar se já existe hospital com mesmo nome no tenant
        existing = session.exec(
            select(Hospital).where(
                Hospital.tenant_id == member.tenant_id,
                Hospital.name == body.name,
            )
        ).first()
        if existing:
            logger.warning(f"Hospital com nome '{body.name}' já existe no tenant {member.tenant_id} (id={existing.id})")
            raise HTTPException(
                status_code=409,
                detail=f"Hospital com nome '{body.name}' já existe neste tenant",
            )

        hospital = Hospital(
            tenant_id=member.tenant_id,
            name=body.name,
            prompt=body.prompt,
            color=body.color,
        )
        logger.info(f"Objeto Hospital criado: tenant_id={hospital.tenant_id}, name={hospital.name}, prompt={hospital.prompt}")

        session.add(hospital)
        try:
            session.commit()
            session.refresh(hospital)
            return hospital
        except IntegrityError as e:
            session.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Erro de integridade ao criar hospital: {error_msg}", exc_info=True)

            # Verificar se é erro de constraint única
            if "uq_hospital_tenant_name" in error_msg.lower() or "unique constraint" in error_msg.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Hospital com nome '{body.name}' já existe neste tenant",
                ) from e
            else:
                # Outro tipo de erro de integridade
                raise HTTPException(
                    status_code=409,
                    detail=f"Erro de integridade ao criar hospital: {error_msg}",
                ) from e
        except Exception as e:
            session.rollback()
            logger.error(f"Erro inesperado ao criar hospital: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar hospital: {str(e)}",
            ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro crítico ao criar hospital: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao criar hospital: {str(e)}",
        ) from e


@router.get("/hospital/list", response_model=HospitalListResponse, tags=["Hospital"])
def list_hospital(
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """
    Lista todos os hospitais do tenant atual com paginação.
    """
    try:
        query = select(Hospital).where(Hospital.tenant_id == member.tenant_id)

        # Contar total antes de aplicar paginação
        count_query = select(func.count(Hospital.id)).where(Hospital.tenant_id == member.tenant_id)
        total = session.exec(count_query).one()

        # Se não há itens, retornar lista vazia diretamente
        if total == 0:
            return HospitalListResponse(
                items=[],
                total=0,
            )

        # Aplicar ordenação e paginação
        items = session.exec(query.order_by(Hospital.name).limit(limit).offset(offset)).all()

        # Validar e converter itens
        response_items = []
        for h in items:
            try:
                validated = HospitalResponse.model_validate(h)
                response_items.append(validated)
            except Exception as e:
                logger.error(f"Erro ao validar hospital id={h.id}, name={h.name}, prompt={h.prompt}: {e}", exc_info=True)
                raise

        return HospitalListResponse(
            items=response_items,
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar hospitais: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar hospitais: {str(e)}",
        ) from e


@router.get("/hospital/{hospital_id}", response_model=HospitalResponse, tags=["Hospital"])
def get_hospital(
    hospital_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Obtém detalhes de um hospital específico.
    Valida que o hospital pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando hospital id={hospital_id} para tenant_id={member.tenant_id}")
        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            logger.warning(f"Hospital não encontrado: id={hospital_id}")
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: hospital.tenant_id={hospital.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        logger.info(f"Hospital encontrado: id={hospital.id}, name={hospital.name}, prompt={'presente' if hospital.prompt else 'None'}")
        return hospital
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar hospital: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar hospital: {str(e)}",
        ) from e


@router.put("/hospital/{hospital_id}", response_model=HospitalResponse, tags=["Hospital"])
def update_hospital(
    hospital_id: int,
    body: HospitalUpdate,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um hospital (apenas admin).
    Valida que o hospital pertence ao tenant atual.
    """
    try:
        logger.info(f"Atualizando hospital: id={hospital_id}, name={body.name}, prompt={'presente' if body.prompt else 'None/vazio'}, tenant_id={member.tenant_id}")

        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            logger.warning(f"Hospital não encontrado: id={hospital_id}")
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: hospital.tenant_id={hospital.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Verificar se novo nome já existe (se estiver alterando)
        if body.name is not None and body.name != hospital.name:
            existing = session.exec(
                select(Hospital).where(
                    Hospital.tenant_id == member.tenant_id,
                    Hospital.name == body.name,
                    Hospital.id != hospital_id,
                )
            ).first()
            if existing:
                logger.warning(f"Hospital com nome '{body.name}' já existe no tenant")
                raise HTTPException(
                    status_code=409,
                    detail=f"Hospital com nome '{body.name}' já existe neste tenant",
                )

        # Atualizar campos
        if body.name is not None:
            hospital.name = body.name
            logger.info(f"Nome atualizado para: {hospital.name}")
        if body.prompt is not None:
            hospital.prompt = body.prompt
            logger.info(f"Prompt atualizado: {body.prompt}")
        if body.color is not None:
            hospital.color = body.color
            logger.info(f"Cor atualizada: {body.color}")
        hospital.updated_at = utc_now()

        session.add(hospital)
        try:
            session.commit()
            session.refresh(hospital)
            return hospital
        except IntegrityError as e:
            session.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Erro de integridade ao atualizar hospital: {error_msg}", exc_info=True)

            # Verificar se é erro de constraint única
            if "uq_hospital_tenant_name" in error_msg.lower() or "unique constraint" in error_msg.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Hospital com nome '{body.name or hospital.name}' já existe neste tenant",
                ) from e
            else:
                # Outro tipo de erro de integridade
                raise HTTPException(
                    status_code=409,
                    detail=f"Erro de integridade ao atualizar hospital: {error_msg}",
                ) from e
        except Exception as e:
            session.rollback()
            logger.error(f"Erro inesperado ao atualizar hospital: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao atualizar hospital: {str(e)}",
            ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro crítico ao atualizar hospital: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao atualizar hospital: {str(e)}",
        ) from e


@router.delete("/hospital/{hospital_id}", status_code=204, tags=["Hospital"])
def delete_hospital(
    hospital_id: int,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Exclui um hospital (apenas admin).
    Valida que o hospital pertence ao tenant atual.
    """
    try:
        logger.info(f"Excluindo hospital id={hospital_id} para tenant_id={member.tenant_id}")

        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            logger.warning(f"Hospital não encontrado: id={hospital_id}")
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: hospital.tenant_id={hospital.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Verificar se há arquivos associados a este hospital
        from app.model.file import File
        files_count = session.exec(
            select(func.count(File.id)).where(File.hospital_id == hospital_id)
        ).one()

        if files_count > 0:
            logger.warning(f"Não é possível excluir hospital {hospital_id}: há {files_count} arquivo(s) associado(s)")
            raise HTTPException(
                status_code=409,
                detail=f"Não é possível excluir o hospital. Há {files_count} arquivo(s) associado(s) a este hospital.",
            )

        session.delete(hospital)
        try:
            session.commit()
            logger.info(f"Hospital deletado com sucesso: id={hospital_id}")
            return Response(status_code=204)
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao excluir hospital: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao excluir hospital: {str(e)}",
            ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro crítico ao excluir hospital: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao excluir hospital: {str(e)}",
        ) from e


# ============================================================================
# Demand Endpoints
# ============================================================================

class DemandCreate(PydanticBaseModel):
    hospital_id: int | None = None
    job_id: int | None = None
    room: str | None = None
    start_time: datetime
    end_time: datetime
    procedure: str
    anesthesia_type: str | None = None
    complexity: str | None = None
    skills: list[str] | None = None
    priority: str | None = None  # "Urgente" | "Emergência" | None
    is_pediatric: bool = False
    notes: str | None = None
    source: dict | None = None

    @field_validator("procedure")
    @classmethod
    def validate_procedure_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo procedure não pode estar vazio")
        return v.strip()

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time deve ser maior que start_time")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime deve ter timezone explícito (timestamptz)")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_lower = v.strip().lower() if isinstance(v, str) else v
        if v_lower in {"urgente", "emergência", "emergencia"}:
            return "Urgente" if "urg" in v_lower else "Emergência"
        return None


class DemandUpdate(PydanticBaseModel):
    hospital_id: int | None = None
    job_id: int | None = None
    room: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    procedure: str | None = None
    anesthesia_type: str | None = None
    complexity: str | None = None
    skills: list[str] | None = None
    priority: str | None = None
    is_pediatric: bool | None = None
    notes: str | None = None
    source: dict | None = None

    @field_validator("procedure")
    @classmethod
    def validate_procedure(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Campo procedure não pode estar vazio")
        return v.strip() if v else None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("Datetime deve ter timezone explícito (timestamptz)")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_lower = v.strip().lower() if isinstance(v, str) else v
        if v_lower in {"urgente", "emergência", "emergencia"}:
            return "Urgente" if "urg" in v_lower else "Emergência"
        return None


class DemandResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    hospital_id: int | None
    job_id: int | None
    room: str | None
    start_time: datetime
    end_time: datetime
    procedure: str
    anesthesia_type: str | None
    complexity: str | None
    skills: list[str] | None
    priority: str | None
    is_pediatric: bool
    notes: str | None
    source: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DemandListResponse(PydanticBaseModel):
    items: list[DemandResponse]
    total: int


@router.post("/demand", response_model=DemandResponse, status_code=201, tags=["Demand"])
def create_demand(
    body: DemandCreate,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Cria uma nova demanda.
    Valida que hospital_id e job_id (se fornecidos) pertencem ao tenant atual.
    """
    try:
        logger.info(f"Criando demanda: procedure={body.procedure}, tenant_id={member.tenant_id}")

        # Validar hospital_id se fornecido
        if body.hospital_id is not None:
            hospital = session.get(Hospital, body.hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != member.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

        # Validar job_id se fornecido
        if body.job_id is not None:
            job = session.get(Job, body.job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job não encontrado")
            if job.tenant_id != member.tenant_id:
                raise HTTPException(status_code=403, detail="Job não pertence ao tenant atual")

        demand = Demand(
            tenant_id=member.tenant_id,
            hospital_id=body.hospital_id,
            job_id=body.job_id,
            room=body.room,
            start_time=body.start_time,
            end_time=body.end_time,
            procedure=body.procedure,
            anesthesia_type=body.anesthesia_type,
            complexity=body.complexity,
            skills=body.skills,
            priority=body.priority,
            is_pediatric=body.is_pediatric,
            notes=body.notes,
            source=body.source,
        )

        session.add(demand)
        session.commit()
        session.refresh(demand)
        logger.info(f"Demanda criada com sucesso: id={demand.id}")
        return demand
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao criar demanda: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar demanda: {str(e)}",
        ) from e


@router.get("/demand/list", response_model=DemandListResponse, tags=["Demand"])
def list_demands(
    hospital_id: Optional[int] = Query(None, description="Filtrar por hospital_id"),
    job_id: Optional[int] = Query(None, description="Filtrar por job_id"),
    start_at: Optional[datetime] = Query(None, description="Filtrar por start_time >= start_at (timestamptz em ISO 8601)"),
    end_at: Optional[datetime] = Query(None, description="Filtrar por end_time <= end_at (timestamptz em ISO 8601)"),
    is_pediatric: Optional[bool] = Query(None, description="Filtrar por is_pediatric"),
    priority: Optional[str] = Query(None, description="Filtrar por priority (Urgente, Emergência)"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Lista demandas do tenant atual, com filtros opcionais e paginação.
    Sempre filtra por tenant_id do JWT (via member).
    Ordena por start_time crescente.
    """
    try:
        logger.info(f"Listando demandas para tenant_id={member.tenant_id}")

        # Query base - sempre filtrar por tenant_id
        query = select(Demand).where(Demand.tenant_id == member.tenant_id)

        # Aplicar filtros
        if hospital_id is not None:
            hospital = session.get(Hospital, hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != member.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")
            query = query.where(Demand.hospital_id == hospital_id)

        if job_id is not None:
            job = session.get(Job, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job não encontrado")
            if job.tenant_id != member.tenant_id:
                raise HTTPException(status_code=403, detail="Job não pertence ao tenant atual")
            query = query.where(Demand.job_id == job_id)

        if start_at is not None:
            if start_at.tzinfo is None:
                raise HTTPException(status_code=400, detail="start_at deve ter timezone explícito (timestamptz)")
            query = query.where(Demand.start_time >= start_at)

        if end_at is not None:
            if end_at.tzinfo is None:
                raise HTTPException(status_code=400, detail="end_at deve ter timezone explícito (timestamptz)")
            query = query.where(Demand.end_time <= end_at)

        if is_pediatric is not None:
            query = query.where(Demand.is_pediatric == is_pediatric)

        if priority is not None:
            if priority not in {"Urgente", "Emergência"}:
                raise HTTPException(status_code=400, detail="priority inválido (esperado: Urgente, Emergência)")
            query = query.where(Demand.priority == priority)

        # Validar intervalo
        if start_at is not None and end_at is not None:
            if start_at > end_at:
                raise HTTPException(status_code=400, detail="start_at deve ser menor ou igual a end_at")

        # Contar total antes de aplicar paginação
        count_query = select(func.count(Demand.id)).where(Demand.tenant_id == member.tenant_id)
        if hospital_id is not None:
            count_query = count_query.where(Demand.hospital_id == hospital_id)
        if job_id is not None:
            count_query = count_query.where(Demand.job_id == job_id)
        if start_at is not None:
            count_query = count_query.where(Demand.start_time >= start_at)
        if end_at is not None:
            count_query = count_query.where(Demand.end_time <= end_at)
        if is_pediatric is not None:
            count_query = count_query.where(Demand.is_pediatric == is_pediatric)
        if priority is not None:
            count_query = count_query.where(Demand.priority == priority)
        total = session.exec(count_query).one()

        # Aplicar ordenação e paginação (start_time crescente)
        query = query.order_by(Demand.start_time.asc()).limit(limit).offset(offset)

        items = session.exec(query).all()

        return DemandListResponse(
            items=[DemandResponse.model_validate(item) for item in items],
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar demandas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar demandas: {str(e)}",
        ) from e


@router.get("/demand/{demand_id}", response_model=DemandResponse, tags=["Demand"])
def get_demand(
    demand_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Obtém detalhes de uma demanda específica.
    Valida que a demanda pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando demanda id={demand_id} para tenant_id={member.tenant_id}")
        demand = session.get(Demand, demand_id)
        if not demand:
            logger.warning(f"Demanda não encontrada: id={demand_id}")
            raise HTTPException(status_code=404, detail="Demanda não encontrada")
        if demand.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: demand.tenant_id={demand.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        logger.info(f"Demanda encontrada: id={demand.id}, procedure={demand.procedure}")
        return demand
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar demanda: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar demanda: {str(e)}",
        ) from e


@router.put("/demand/{demand_id}", response_model=DemandResponse, tags=["Demand"])
def update_demand(
    demand_id: int,
    body: DemandUpdate,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Atualiza uma demanda.
    Valida que a demanda pertence ao tenant atual.
    Valida que hospital_id e job_id (se fornecidos) pertencem ao tenant atual.
    """
    try:
        logger.info(f"Atualizando demanda id={demand_id} para tenant_id={member.tenant_id}")

        demand = session.get(Demand, demand_id)
        if not demand:
            logger.warning(f"Demanda não encontrada: id={demand_id}")
            raise HTTPException(status_code=404, detail="Demanda não encontrada")
        if demand.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: demand.tenant_id={demand.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar hospital_id se fornecido
        if body.hospital_id is not None:
            hospital = session.get(Hospital, body.hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != member.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

        # Validar job_id se fornecido
        if body.job_id is not None:
            job = session.get(Job, body.job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job não encontrado")
            if job.tenant_id != member.tenant_id:
                raise HTTPException(status_code=403, detail="Job não pertence ao tenant atual")

        # Validar end_time > start_time se ambos forem atualizados
        start_time = body.start_time if body.start_time is not None else demand.start_time
        end_time = body.end_time if body.end_time is not None else demand.end_time
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="end_time deve ser maior que start_time")

        # Atualizar campos
        if body.hospital_id is not None:
            demand.hospital_id = body.hospital_id
        if body.job_id is not None:
            demand.job_id = body.job_id
        if body.room is not None:
            demand.room = body.room
        if body.start_time is not None:
            demand.start_time = body.start_time
        if body.end_time is not None:
            demand.end_time = body.end_time
        if body.procedure is not None:
            demand.procedure = body.procedure
        if body.anesthesia_type is not None:
            demand.anesthesia_type = body.anesthesia_type
        if body.complexity is not None:
            demand.complexity = body.complexity
        if body.skills is not None:
            demand.skills = body.skills
        if body.priority is not None:
            demand.priority = body.priority
        if body.is_pediatric is not None:
            demand.is_pediatric = body.is_pediatric
        if body.notes is not None:
            demand.notes = body.notes
        if body.source is not None:
            demand.source = body.source
        demand.updated_at = utc_now()

        session.add(demand)
        session.commit()
        session.refresh(demand)
        logger.info(f"Demanda atualizada com sucesso: id={demand.id}")
        return demand
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar demanda: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar demanda: {str(e)}",
        ) from e


@router.delete("/demand/{demand_id}", status_code=204, tags=["Demand"])
def delete_demand(
    demand_id: int,
    member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Exclui uma demanda.
    Valida que a demanda pertence ao tenant atual.
    """
    try:
        logger.info(f"Excluindo demanda id={demand_id} para tenant_id={member.tenant_id}")

        demand = session.get(Demand, demand_id)
        if not demand:
            logger.warning(f"Demanda não encontrada: id={demand_id}")
            raise HTTPException(status_code=404, detail="Demanda não encontrada")
        if demand.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: demand.tenant_id={demand.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        session.delete(demand)
        session.commit()
        logger.info(f"Demanda excluída com sucesso: id={demand_id}")
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao excluir demanda: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao excluir demanda: {str(e)}",
        ) from e


# ============================================================================
# MEMBER ENDPOINTS
# ============================================================================

class MemberCreate(PydanticBaseModel):
    """Schema para criar member."""
    email: Optional[str] = None  # Email público (obrigatório se account_id não for fornecido)
    name: Optional[str] = None  # Nome público na clínica
    role: str
    status: str = "ACTIVE"
    account_id: Optional[int] = None  # Opcional (não usado no painel)
    attribute: Optional[dict] = None  # Atributos customizados (JSON)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v:
                return None
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"admin", "account"}:
            raise ValueError("role deve ser 'admin' ou 'account'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in {"PENDING", "ACTIVE", "REJECTED", "REMOVED"}:
            raise ValueError("status deve ser 'PENDING', 'ACTIVE', 'REJECTED' ou 'REMOVED'")
        return v

    @model_validator(mode="after")
    def validate_email_or_account_id(self):
        """Validar que email é fornecido se account_id não for fornecido."""
        if self.account_id is None and (self.email is None or self.email == ""):
            raise ValueError("email é obrigatório quando account_id não é fornecido")
        return self


class MemberUpdate(PydanticBaseModel):
    """Schema para atualizar member."""
    role: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None  # Nome público na clínica (member.name)
    email: Optional[str] = None  # Email público na clínica (member.email)
    attribute: Optional[dict] = None  # Atributos customizados (JSON)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if v not in {"admin", "account"}:
                raise ValueError("role deve ser 'admin' ou 'account'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if v not in {"PENDING", "ACTIVE", "REJECTED", "REMOVED"}:
                raise ValueError("status deve ser 'PENDING', 'ACTIVE', 'REJECTED' ou 'REMOVED'")
        return v


class MemberResponse(PydanticBaseModel):
    """Schema de resposta para member."""
    id: int
    tenant_id: int
    account_id: int | None  # Pode ser NULL para convites pendentes sem Account
    account_email: Optional[str] = None  # Privado, apenas para compatibilidade/auditoria
    member_email: Optional[str] = None  # Email público na clínica (pode ser editado)
    member_name: Optional[str] = None  # Nome público na clínica (pode ser editado)
    role: str
    status: str
    attribute: dict  # Atributos customizados (JSON)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberListResponse(PydanticBaseModel):
    """Schema de resposta para listagem de members."""
    items: list[MemberResponse]
    total: int


@router.post("/member", response_model=MemberResponse, status_code=201, tags=["Member"])
def create_member(
    body: MemberCreate,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo member (apenas admin).
    Permite criar member com email e name públicos, sem necessidade de account_id.
    """
    try:
        email_lower = body.email.lower() if body.email else None
        logger.info(f"Criando member: email={email_lower}, tenant_id={member.tenant_id}, role={body.role}, status={body.status}")

        account = None
        account_id = None

        # Se account_id foi fornecido, validar que existe
        if body.account_id is not None:
            account = session.get(Account, body.account_id)
            if not account:
                logger.warning(f"Account não encontrado: id={body.account_id}")
                raise HTTPException(status_code=404, detail="Account não encontrado")
            account_id = account.id
            # Verificar se já existe member para este account no tenant
            existing_member = session.exec(
                select(Member).where(
                    Member.account_id == account_id,
                    Member.tenant_id == member.tenant_id,
                )
            ).first()
            if existing_member:
                logger.warning(f"Member já existe para account {account_id} no tenant {member.tenant_id}")
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um member para este account neste tenant",
                )
        else:
            # Se account_id não foi fornecido, verificar unicidade por email
            if not email_lower:
                raise HTTPException(status_code=400, detail="email é obrigatório quando account_id não é fornecido")

            existing_member = session.exec(
                select(Member).where(
                    Member.tenant_id == member.tenant_id,
                    Member.email == email_lower,
                    Member.account_id.is_(None),
                )
            ).first()
            if existing_member:
                logger.warning(f"Member já existe para email {email_lower} no tenant {member.tenant_id}")
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um member pendente para este email neste tenant",
                )

        # Criar member
        member_obj = Member(
            tenant_id=member.tenant_id,
            account_id=account_id,
            email=email_lower,
            name=body.name,
            role=MemberRole[body.role.upper()],
            status=MemberStatus[body.status.upper()],
            attribute=body.attribute if body.attribute is not None else {},
        )
        session.add(member_obj)
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="Member duplicado não permitido",
            ) from e
        session.refresh(member_obj)

        # Log de auditoria
        _try_write_audit_log(
            session,
            AuditLog(
                tenant_id=member.tenant_id,
                actor_account_id=member.account_id,
                member_id=member_obj.id,
                event_type="member_invited",
                data={
                    "target_account_id": account_id,
                    "email": email_lower,
                    "from_status": None,
                    "to_status": member_obj.status.value,
                    "from_role": None,
                    "to_role": member_obj.role.value,
                },
            ),
        )

        # Buscar account_email para resposta (pode ser None)
        account_email = account.email if account else None

        return MemberResponse(
            id=member_obj.id,
            tenant_id=member_obj.tenant_id,
            account_id=member_obj.account_id,
            account_email=account_email,
            member_email=member_obj.email,
            member_name=member_obj.name,  # Nome público na clínica (pode ser NULL)
            role=member_obj.role.value,
            status=member_obj.status.value,
            attribute=member_obj.attribute,
            created_at=member_obj.created_at,
            updated_at=member_obj.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao criar member: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar member: {str(e)}",
        ) from e


@router.get("/member/list", response_model=MemberListResponse, tags=["Member"])
def list_members(
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None, description="Filtrar por status (PENDING, ACTIVE, REJECTED, REMOVED)"),
    role: Optional[str] = Query(default=None, description="Filtrar por role (admin, account)"),
):
    """
    Lista members do tenant atual (apenas admin).
    Sempre filtra por tenant_id do JWT (via member).
    """
    try:
        # Query base: members do tenant com LEFT JOIN em Account (para incluir members sem Account)
        query = (
            select(Member, Account)
            .outerjoin(Account, Member.account_id == Account.id)
            .where(Member.tenant_id == member.tenant_id)
        )

        # Aplicar filtros
        if status:
            status_upper = status.strip().upper()
            if status_upper in {"PENDING", "ACTIVE", "REJECTED", "REMOVED"}:
                query = query.where(Member.status == MemberStatus[status_upper])
        if role:
            role_lower = role.strip().lower()
            if role_lower in {"admin", "account"}:
                query = query.where(Member.role == MemberRole[role_lower.upper()])

        # Contar total (sem JOIN, apenas contar members)
        count_query = (
            select(func.count(Member.id))
            .where(Member.tenant_id == member.tenant_id)
        )
        if status:
            status_upper = status.strip().upper()
            if status_upper in {"PENDING", "ACTIVE", "REJECTED", "REMOVED"}:
                count_query = count_query.where(Member.status == MemberStatus[status_upper])
        if role:
            role_lower = role.strip().lower()
            if role_lower in {"admin", "account"}:
                count_query = count_query.where(Member.role == MemberRole[role_lower.upper()])

        total = session.exec(count_query).one()

        # Aplicar paginação e ordenação
        query = query.order_by(Member.created_at.desc()).limit(limit).offset(offset)

        # Executar query
        results = session.exec(query).all()

        # Montar resposta
        items = []
        for member_obj, account in results:
            # account_email é privado, apenas para compatibilidade/auditoria
            account_email = account.email if account else None
            items.append(
                MemberResponse(
                    id=member_obj.id,
                    tenant_id=member_obj.tenant_id,
                    account_id=member_obj.account_id,
                    account_email=account_email,
                    member_email=member_obj.email,  # Email público na clínica
                    member_name=member_obj.name,  # Nome público na clínica (pode ser NULL)
                    role=member_obj.role.value,
                    status=member_obj.status.value,
                    attribute=member_obj.attribute,
                    created_at=member_obj.created_at,
                    updated_at=member_obj.updated_at,
                )
            )

        return MemberListResponse(items=items, total=total)
    except Exception as e:
        logger.error(f"Erro ao listar members: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar members: {str(e)}",
        ) from e


@router.get("/member/{member_id}", response_model=MemberResponse, tags=["Member"])
def get_member(
    member_id: int,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Busca um member específico (apenas admin).
    Valida que o member pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando member id={member_id} para tenant_id={member.tenant_id}")

        member_obj = session.get(Member, member_id)
        if not member_obj:
            logger.warning(f"Member não encontrado: id={member_id}")
            raise HTTPException(status_code=404, detail="Member não encontrado")
        if member_obj.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: member.tenant_id={member_obj.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Buscar account (pode ser None se member ainda não foi vinculado)
        account = None
        account_email = None
        if member_obj.account_id:
            account = session.get(Account, member_obj.account_id)
            if account:
                account_email = account.email

        return MemberResponse(
            id=member_obj.id,
            tenant_id=member_obj.tenant_id,
            account_id=member_obj.account_id,
            account_email=account_email,
            member_email=member_obj.email,  # Email público na clínica
            member_name=member_obj.name,  # Nome público na clínica (pode ser NULL)
            role=member_obj.role.value,
            status=member_obj.status.value,
            attribute=member_obj.attribute,
            created_at=member_obj.created_at,
            updated_at=member_obj.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar member: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar member: {str(e)}",
        ) from e


@router.put("/member/{member_id}", response_model=MemberResponse, tags=["Member"])
def update_member(
    member_id: int,
    body: MemberUpdate,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um member (apenas admin).
    Permite alterar role e status.
    Valida que o member pertence ao tenant atual.
    """
    try:
        logger.info(f"Atualizando member id={member_id} para tenant_id={member.tenant_id}")

        member_obj = session.get(Member, member_id)
        if not member_obj:
            logger.warning(f"Member não encontrado: id={member_id}")
            raise HTTPException(status_code=404, detail="Member não encontrado")
        if member_obj.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: member.tenant_id={member_obj.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar regras de negócio
        if body.status and body.status.upper() == "REMOVED":
            # Não permitir remover o último member ACTIVE de um account
            # Só validar se member tem account_id (members ACTIVE sempre devem ter)
            if member_obj.status == MemberStatus.ACTIVE and member_obj.account_id:
                active_count = session.exec(
                    select(func.count())
                    .select_from(Member)
                    .where(
                        Member.account_id == member_obj.account_id,
                        Member.status == MemberStatus.ACTIVE,
                    )
                ).one()
                if int(active_count or 0) <= 1:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Não é permitido remover o último member ACTIVE da conta. "
                            "Antes, garanta outro acesso (ex.: outro tenant) ou transfira permissões."
                        ),
                    )

        # Atualizar campos
        prev_status = member_obj.status
        prev_role = member_obj.role

        if body.role is not None:
            member_obj.role = MemberRole[body.role.upper()]
        if body.status is not None:
            member_obj.status = MemberStatus[body.status.upper()]
        if body.name is not None:
            # Permitir editar member.name (não account.name)
            member_obj.name = body.name
        if body.email is not None:
            # Permitir editar member.email (campo público, independente de account.email)
            member_obj.email = body.email.lower() if body.email else None
        if body.attribute is not None:
            # Permitir editar member.attribute
            member_obj.attribute = body.attribute

        member_obj.updated_at = utc_now()
        session.add(member_obj)
        session.commit()
        session.refresh(member_obj)

        # Log de auditoria se houver mudanças
        if prev_status != member_obj.status or prev_role != member_obj.role:
            _try_write_audit_log(
                session,
                AuditLog(
                    tenant_id=member.tenant_id,
                    actor_account_id=member.account_id,
                    member_id=member_obj.id,
                    event_type="member_status_changed",
                    data={
                        "target_account_id": member_obj.account_id,
                        "from_status": prev_status.value,
                        "to_status": member_obj.status.value,
                        "from_role": prev_role.value,
                        "to_role": member_obj.role.value,
                    },
                ),
            )

        # Buscar account (pode ser None se member ainda não foi vinculado)
        account = None
        account_email = None
        if member_obj.account_id:
            account = session.get(Account, member_obj.account_id)
            if account:
                account_email = account.email

        return MemberResponse(
            id=member_obj.id,
            tenant_id=member_obj.tenant_id,
            account_id=member_obj.account_id,
            account_email=account_email,
            member_email=member_obj.email,  # Email público na clínica
            member_name=member_obj.name,  # Nome público na clínica (pode ser NULL)
            role=member_obj.role.value,
            status=member_obj.status.value,
            attribute=member_obj.attribute,
            created_at=member_obj.created_at,
            updated_at=member_obj.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar member: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar member: {str(e)}",
        ) from e


@router.delete("/member/{member_id}", status_code=204, tags=["Member"])
def delete_member(
    member_id: int,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove (soft-delete) um member (status -> REMOVED) (apenas admin).
    Valida que o member pertence ao tenant atual.
    Regra de segurança: não permitir remover o último member ACTIVE de um account.
    """
    try:
        logger.info(f"Removendo member id={member_id} para tenant_id={member.tenant_id}")

        member_obj = session.get(Member, member_id)
        if not member_obj:
            logger.warning(f"Member não encontrado: id={member_id}")
            raise HTTPException(status_code=404, detail="Member não encontrado")
        if member_obj.tenant_id != member.tenant_id:
            logger.warning(f"Acesso negado: member.tenant_id={member_obj.tenant_id}, member.tenant_id={member.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar regra de segurança
        # Só validar se member tem account_id (members ACTIVE sempre devem ter)
        if member_obj.status == MemberStatus.ACTIVE and member_obj.account_id:
            active_count = session.exec(
                select(func.count())
                .select_from(Member)
                .where(
                    Member.account_id == member_obj.account_id,
                    Member.status == MemberStatus.ACTIVE,
                )
            ).one()
            if int(active_count or 0) <= 1:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Não é permitido remover o último member ACTIVE da conta. "
                        "Antes, garanta outro acesso (ex.: outro tenant) ou transfira permissões."
                    ),
                )

        prev_status = member_obj.status
        member_obj.status = MemberStatus.REMOVED
        member_obj.updated_at = utc_now()
        session.add(member_obj)
        session.commit()
        session.refresh(member_obj)

        # Log de auditoria
        _try_write_audit_log(
            session,
            AuditLog(
                tenant_id=member.tenant_id,
                actor_account_id=member.account_id,
                member_id=member_obj.id,
                event_type="member_status_changed",
                data={
                    "target_account_id": member_obj.account_id,
                    "from_status": prev_status.value,
                    "to_status": member_obj.status.value,
                },
            ),
        )

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao remover member: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao remover member: {str(e)}",
        ) from e


@router.post("/member/{member_id}/invite", status_code=200, tags=["Member"])
def send_member_invite_email(
    member_id: int,
    member: Member = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Envia email de convite para um member e atualiza status para PENDING.
    Apenas admin pode enviar convites.
    """
    try:
        member_obj = session.get(Member, member_id)
        if not member_obj:
            raise HTTPException(status_code=404, detail="Member não encontrado")

        if member_obj.tenant_id != member.tenant_id:
            raise HTTPException(status_code=403, detail="Acesso negado")

        tenant = session.get(Tenant, member.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        # Usar member.email como email de destino (campo público)
        # Fallback para account.email apenas se member.email estiver vazio e account_id estiver preenchido
        account_email = member_obj.email
        if not account_email and member_obj.account_id:
            account = session.get(Account, member_obj.account_id)
            if account and account.email:
                account_email = account.email

        if not account_email:
            raise HTTPException(status_code=400, detail="Member não possui email para envio de convite")

        logger.info(
            f"[INVITE] Iniciando envio de convite para member ID={member_id} "
            f"(email={account_email}, tenant_id={member.tenant_id})"
        )

        # Atualizar status para PENDING antes de enviar o email
        prev_status = member_obj.status
        if member_obj.status != MemberStatus.PENDING:
            member_obj.status = MemberStatus.PENDING
            member_obj.updated_at = utc_now()
            session.add(member_obj)
            session.commit()
            session.refresh(member_obj)

            # Log de auditoria se status mudou
            if prev_status != member_obj.status:
                _try_write_audit_log(
                    session,
                    AuditLog(
                        tenant_id=member.tenant_id,
                        actor_account_id=member.account_id,
                        member_id=member_obj.id,
                        event_type="member_status_changed",
                        data={
                            "target_account_id": member_obj.account_id,
                            "target_email": account_email,
                            "from_status": prev_status.value,
                            "to_status": member_obj.status.value,
                        },
                    ),
                )

        # Enviar email de convite
        try:
            # Usar member.name se existir, senão usar email
            from app.services.email_service import send_member_invite
            member_name = member_obj.name if member_obj.name else account_email
            result = send_member_invite(
                to_email=account_email,
                member_name=member_name,
                tenant_name=tenant.name,
            )

            # Garantir que o resultado é uma tupla
            if isinstance(result, tuple) and len(result) == 2:
                success, error_message = result
            else:
                # Fallback se a função retornar apenas bool (código antigo em cache)
                logger.warning(
                    f"[INVITE] Função retornou tipo inesperado: {type(result)}. "
                    f"Esperado: tuple[bool, str]. Usando fallback."
                )
                success = bool(result) if isinstance(result, bool) else False
                error_message = "Erro ao processar envio de email. Reinicie o servidor."
        except ValueError as e:
            # Erro de unpacking - função ainda retorna apenas bool
            logger.error(
                f"[INVITE] Erro ao desempacotar resultado: {e}. "
                f"Função pode estar retornando apenas bool. Reinicie o servidor."
            )
            success = False
            error_message = "Erro ao processar envio de email. Reinicie o servidor para aplicar atualizações."

        if not success:
            logger.error(
                f"[INVITE] ❌ FALHA - Envio de convite falhou para member ID={member_id} "
                f"(email={account_email}): {error_message}"
            )
            raise HTTPException(
                status_code=500,
                detail=error_message or "Erro ao enviar email de convite. Tente novamente mais tarde."
            )

        logger.info(
            f"[INVITE] ✅ SUCESSO - Convite enviado com sucesso para member ID={member_id} "
            f"(email={account_email})"
        )
        return {"message": "Convite enviado com sucesso", "email": account_email}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar convite para member {member_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar convite: {str(e)}",
        ) from e
