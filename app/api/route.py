import os
import logging
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
from app.model.demand import Demand
from app.model.profile import Profile
from app.model.professional import Professional
from app.services.hospital_service import create_default_hospital_for_tenant
from app.services.email_service import send_professional_invite
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
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo account (apenas admin).
    """
    try:
        logger.info(f"Criando account: email={body.email}, tenant_id={membership.tenant_id}")

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

        logger.info(f"Account criado com sucesso: id={account.id}")
        return AccountResponse(
            id=account.id,
            email=account.email,
            name=account.name,
            role=account.role,
            tenant_id=membership.tenant_id,
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


@router.get("/account/list", response_model=list[AccountResponse], tags=["Account"])
def list_accounts(
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista accounts do tenant atual (via Membership ACTIVE).
    """
    try:
        logger.info(f"Listando accounts para tenant_id={membership.tenant_id}")
        # Buscar accounts via Membership
        memberships = session.exec(
            select(Membership, Account)
            .join(Account, Membership.account_id == Account.id)
            .where(
                Membership.tenant_id == membership.tenant_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
            .order_by(Account.name)
        ).all()

        accounts = []
        for membership_obj, account in memberships:
            accounts.append(AccountResponse(
                id=account.id,
                email=account.email,
                name=account.name,
                role=account.role,
                tenant_id=membership.tenant_id,
                auth_provider=account.auth_provider,
                created_at=_isoformat_utc(account.created_at),
                updated_at=_isoformat_utc(account.updated_at),
            ))

        logger.info(f"Encontrados {len(accounts)} accounts")
        return accounts
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar accounts: {str(e)}",
        ) from e


@router.put("/account/{account_id}", response_model=AccountResponse, tags=["Account"])
def update_account(
    account_id: int,
    body: AccountUpdate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um account (apenas admin).
    Valida que o account pertence ao tenant atual (via Membership ACTIVE).
    """
    try:
        logger.info(f"Atualizando account: id={account_id}, tenant_id={membership.tenant_id}")

        account = session.get(Account, account_id)
        if not account:
            logger.warning(f"Account não encontrado: id={account_id}")
            raise HTTPException(status_code=404, detail="Account não encontrado")

        # Validar que o account pertence ao tenant atual via Membership
        account_membership = session.exec(
            select(Membership).where(
                Membership.account_id == account_id,
                Membership.tenant_id == membership.tenant_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        ).first()
        if not account_membership:
            logger.warning(f"Account {account_id} não possui membership ACTIVE no tenant {membership.tenant_id}")
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
            tenant_id=membership.tenant_id,
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
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove um account do tenant atual removendo o Membership (apenas admin).
    Valida que o account pertence ao tenant atual (via Membership ACTIVE).
    """
    try:
        logger.info(f"Removendo account: id={account_id}, tenant_id={membership.tenant_id}")

        account = session.get(Account, account_id)
        if not account:
            logger.warning(f"Account não encontrado: id={account_id}")
            raise HTTPException(status_code=404, detail="Account não encontrado")

        # Validar que o account pertence ao tenant atual via Membership
        account_membership = session.exec(
            select(Membership).where(
                Membership.account_id == account_id,
                Membership.tenant_id == membership.tenant_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        ).first()
        if not account_membership:
            logger.warning(f"Account {account_id} não possui membership ACTIVE no tenant {membership.tenant_id}")
            raise HTTPException(
                status_code=403,
                detail=f"Account {account_id} não pertence ao tenant atual",
            )

        # Validar regra de segurança: não permitir remover o último membership ACTIVE de um account
        active_count = session.exec(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.account_id == account_id,
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

        # Remover membership (soft-delete: status -> REMOVED)
        prev_status = account_membership.status
        account_membership.status = MembershipStatus.REMOVED
        account_membership.updated_at = utc_now()
        session.add(account_membership)
        session.commit()
        session.refresh(account_membership)

        # Log de auditoria
        _try_write_audit_log(
            session,
            AuditLog(
                tenant_id=membership.tenant_id,
                actor_account_id=membership.account_id,
                membership_id=account_membership.id,
                event_type="membership_status_changed",
                data={
                    "target_account_id": account_id,
                    "from_status": prev_status.value,
                    "to_status": account_membership.status.value,
                },
            ),
        )

        logger.info(f"Account removido com sucesso: id={account_id}")
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

    # Criar professional automaticamente para o account criador do tenant
    # Usa dados do account (nome e email) para criar o professional
    try:
        professional = Professional(
            tenant_id=tenant.id,
            account_id=account.id,
            name=account.name,
            email=account.email,
            active=True,
        )
        session.add(professional)
        session.commit()
        logger.info(f"Professional criado automaticamente para account {account.id} no tenant {tenant.id}")
    except Exception as e:
        # Se falhar ao criar professional, logar mas não quebrar a criação do tenant
        logger.warning(f"Erro ao criar professional automaticamente para account {account.id}: {e}")
        session.rollback()
        # Continuar mesmo se falhar (professional é opcional)

    return tenant


@router.get("/tenant/list", response_model=TenantListResponse, tags=["Tenant"])
def list_tenants(
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Lista todos os tenants (apenas admin).
    """
    try:
        logger.info(f"Listando tenants")
        query = select(Tenant)
        items = session.exec(query.order_by(Tenant.name)).all()
        total = len(items)

        logger.info(f"Encontrados {total} tenants")

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


@router.put("/tenant/{tenant_id}", response_model=TenantResponse, tags=["Tenant"])
def update_tenant(
    tenant_id: int,
    body: TenantUpdate,
    membership: Membership = Depends(require_role("admin")),
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

        logger.info(f"Tenant atualizado com sucesso: id={tenant_id}")
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
    membership: Membership = Depends(require_role("admin")),
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

        # Verificar se há memberships ativos para este tenant
        active_memberships = session.exec(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.tenant_id == tenant_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        ).one()

        if int(active_memberships or 0) > 0:
            raise HTTPException(
                status_code=409,
                detail="Não é permitido remover um tenant que possui memberships ativos. Remova ou desative os memberships primeiro.",
            )

        session.delete(tenant)
        session.commit()

        logger.info(f"Tenant removido com sucesso: id={tenant_id}")
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
    Exclui arquivo do banco e do S3/MinIO.
    """
    # Buscar arquivo
    file_model = session.get(File, file_id)
    if not file_model:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Validar tenant_id
    if file_model.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Excluir arquivo do S3/MinIO
    storage_service = StorageService()
    try:
        storage_service.delete_file(file_model.s3_key)
    except Exception as e:
        # Log erro mas continua com exclusão do banco (arquivo pode já ter sido deletado)
        import logging
        logging.warning(f"Erro ao excluir arquivo do S3 (continuando com exclusão do banco): {e}")
        # Em desenvolvimento, log mais detalhado
        if os.getenv("APP_ENV", "dev") == "dev":
            import traceback
            logging.warning(f"Traceback ao excluir do S3:\n{traceback.format_exc()}")

    # Excluir registro do banco
    try:
        session.delete(file_model)
        session.commit()
    except Exception as e:
        session.rollback()
        import logging
        import traceback
        error_detail = f"Erro ao excluir arquivo do banco: {str(e)}"
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
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo hospital (apenas admin).
    Hospital sempre pertence ao tenant atual (do membership).
    """
    try:
        logger.info(f"Criando hospital: name={body.name}, prompt={'presente' if body.prompt else 'None/vazio'}, tenant_id={membership.tenant_id}")

        # Verificar se já existe hospital com mesmo nome no tenant
        existing = session.exec(
            select(Hospital).where(
                Hospital.tenant_id == membership.tenant_id,
                Hospital.name == body.name,
            )
        ).first()
        if existing:
            logger.warning(f"Hospital com nome '{body.name}' já existe no tenant {membership.tenant_id} (id={existing.id})")
            raise HTTPException(
                status_code=409,
                detail=f"Hospital com nome '{body.name}' já existe neste tenant",
            )

        logger.info(f"Valor do prompt após validação Pydantic: {body.prompt}")

        hospital = Hospital(
            tenant_id=membership.tenant_id,
            name=body.name,
            prompt=body.prompt,
            color=body.color,
        )
        logger.info(f"Objeto Hospital criado: tenant_id={hospital.tenant_id}, name={hospital.name}, prompt={hospital.prompt}")

        session.add(hospital)
        try:
            session.commit()
            logger.info(f"Hospital criado com sucesso: id={hospital.id}")
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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista todos os hospitais do tenant atual.
    """
    try:
        logger.info(f"Listando hospitais para tenant_id={membership.tenant_id}")
        query = select(Hospital).where(Hospital.tenant_id == membership.tenant_id)
        items = session.exec(query.order_by(Hospital.name)).all()
        total = len(items)

        logger.info(f"Encontrados {total} hospitais")

        # Se não há itens, retornar lista vazia diretamente
        if total == 0:
            logger.info("Nenhum hospital encontrado, retornando lista vazia")
            return HospitalListResponse(
                items=[],
                total=0,
            )

        # Validar e converter itens
        response_items = []
        for h in items:
            try:
                validated = HospitalResponse.model_validate(h)
                response_items.append(validated)
            except Exception as e:
                logger.error(f"Erro ao validar hospital id={h.id}, name={h.name}, prompt={h.prompt}: {e}", exc_info=True)
                raise

        logger.info(f"Retornando {len(response_items)} hospitais validados")
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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Obtém detalhes de um hospital específico.
    Valida que o hospital pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando hospital id={hospital_id} para tenant_id={membership.tenant_id}")
        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            logger.warning(f"Hospital não encontrado: id={hospital_id}")
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: hospital.tenant_id={hospital.tenant_id}, membership.tenant_id={membership.tenant_id}")
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
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um hospital (apenas admin).
    Valida que o hospital pertence ao tenant atual.
    """
    try:
        logger.info(f"Atualizando hospital: id={hospital_id}, name={body.name}, prompt={'presente' if body.prompt else 'None/vazio'}, tenant_id={membership.tenant_id}")

        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            logger.warning(f"Hospital não encontrado: id={hospital_id}")
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: hospital.tenant_id={hospital.tenant_id}, membership.tenant_id={membership.tenant_id}")
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

        logger.info(f"Objeto Hospital antes do commit: tenant_id={hospital.tenant_id}, name={hospital.name}, prompt={hospital.prompt}")

        session.add(hospital)
        try:
            session.commit()
            logger.info(f"Hospital atualizado com sucesso: id={hospital.id}")
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
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Exclui um hospital (apenas admin).
    Valida que o hospital pertence ao tenant atual.
    """
    try:
        logger.info(f"Excluindo hospital id={hospital_id} para tenant_id={membership.tenant_id}")

        hospital = session.get(Hospital, hospital_id)
        if not hospital:
            logger.warning(f"Hospital não encontrado: id={hospital_id}")
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        if hospital.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: hospital.tenant_id={hospital.tenant_id}, membership.tenant_id={membership.tenant_id}")
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


class ProfileCreate(PydanticBaseModel):
    account_id: int
    hospital_id: int | None = None
    attribute: dict = {}

    @field_validator("attribute")
    @classmethod
    def validate_attribute(cls, v: dict) -> dict:
        if not isinstance(v, dict):
            raise ValueError("attribute deve ser um objeto JSON")
        return v


class ProfileUpdate(PydanticBaseModel):
    hospital_id: int | None = None
    attribute: dict | None = None

    @field_validator("attribute")
    @classmethod
    def validate_attribute(cls, v: dict | None) -> dict | None:
        if v is not None and not isinstance(v, dict):
            raise ValueError("attribute deve ser um objeto JSON")
        return v


class ProfileResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    account_id: int
    hospital_id: int | None
    attribute: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileListResponse(PydanticBaseModel):
    items: list[ProfileResponse]
    total: int


class ProfessionalCreate(PydanticBaseModel):
    name: str
    email: str
    phone: str | None = None
    notes: str | None = None
    active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo nome é obrigatório")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo email é obrigatório")
        # Normalizar email para lowercase
        return v.strip().lower()


class ProfessionalUpdate(PydanticBaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    active: bool | None = None

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


class ProfessionalResponse(PydanticBaseModel):
    id: int
    tenant_id: int
    account_id: int | None
    name: str
    email: str | None
    phone: str | None
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfessionalListResponse(PydanticBaseModel):
    items: list[ProfessionalResponse]
    total: int


@router.post("/demand", response_model=DemandResponse, status_code=201, tags=["Demand"])
def create_demand(
    body: DemandCreate,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Cria uma nova demanda.
    Valida que hospital_id e job_id (se fornecidos) pertencem ao tenant atual.
    """
    try:
        logger.info(f"Criando demanda: procedure={body.procedure}, tenant_id={membership.tenant_id}")

        # Validar hospital_id se fornecido
        if body.hospital_id is not None:
            hospital = session.get(Hospital, body.hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != membership.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

        # Validar job_id se fornecido
        if body.job_id is not None:
            job = session.get(Job, body.job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job não encontrado")
            if job.tenant_id != membership.tenant_id:
                raise HTTPException(status_code=403, detail="Job não pertence ao tenant atual")

        demand = Demand(
            tenant_id=membership.tenant_id,
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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista demandas do tenant atual, com filtros opcionais e paginação.
    Sempre filtra por tenant_id do JWT (via membership).
    Ordena por start_time crescente.
    """
    try:
        logger.info(f"Listando demandas para tenant_id={membership.tenant_id}")

        # Query base - sempre filtrar por tenant_id
        query = select(Demand).where(Demand.tenant_id == membership.tenant_id)

        # Aplicar filtros
        if hospital_id is not None:
            hospital = session.get(Hospital, hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != membership.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")
            query = query.where(Demand.hospital_id == hospital_id)

        if job_id is not None:
            job = session.get(Job, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job não encontrado")
            if job.tenant_id != membership.tenant_id:
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
        count_query = select(func.count(Demand.id)).where(Demand.tenant_id == membership.tenant_id)
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
        logger.info(f"Encontradas {total} demandas, retornando {len(items)}")

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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Obtém detalhes de uma demanda específica.
    Valida que a demanda pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando demanda id={demand_id} para tenant_id={membership.tenant_id}")
        demand = session.get(Demand, demand_id)
        if not demand:
            logger.warning(f"Demanda não encontrada: id={demand_id}")
            raise HTTPException(status_code=404, detail="Demanda não encontrada")
        if demand.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: demand.tenant_id={demand.tenant_id}, membership.tenant_id={membership.tenant_id}")
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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Atualiza uma demanda.
    Valida que a demanda pertence ao tenant atual.
    Valida que hospital_id e job_id (se fornecidos) pertencem ao tenant atual.
    """
    try:
        logger.info(f"Atualizando demanda id={demand_id} para tenant_id={membership.tenant_id}")

        demand = session.get(Demand, demand_id)
        if not demand:
            logger.warning(f"Demanda não encontrada: id={demand_id}")
            raise HTTPException(status_code=404, detail="Demanda não encontrada")
        if demand.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: demand.tenant_id={demand.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar hospital_id se fornecido
        if body.hospital_id is not None:
            hospital = session.get(Hospital, body.hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != membership.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

        # Validar job_id se fornecido
        if body.job_id is not None:
            job = session.get(Job, body.job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job não encontrado")
            if job.tenant_id != membership.tenant_id:
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
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Exclui uma demanda.
    Valida que a demanda pertence ao tenant atual.
    """
    try:
        logger.info(f"Excluindo demanda id={demand_id} para tenant_id={membership.tenant_id}")

        demand = session.get(Demand, demand_id)
        if not demand:
            logger.warning(f"Demanda não encontrada: id={demand_id}")
            raise HTTPException(status_code=404, detail="Demanda não encontrada")
        if demand.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: demand.tenant_id={demand.tenant_id}, membership.tenant_id={membership.tenant_id}")
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


@router.post("/profile", response_model=ProfileResponse, status_code=201, tags=["Profile"])
def create_profile(
    body: ProfileCreate,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Cria um novo profile.
    Valida que account_id pertence ao tenant atual (via Membership) e que hospital_id (se fornecido) pertence ao tenant.
    """
    try:
        logger.info(f"Criando profile: account_id={body.account_id}, hospital_id={body.hospital_id}, tenant_id={membership.tenant_id}")

        # Validar que account_id pertence ao tenant via Membership
        account_membership = session.exec(
            select(Membership).where(
                Membership.account_id == body.account_id,
                Membership.tenant_id == membership.tenant_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        ).first()
        if not account_membership:
            logger.warning(f"Account {body.account_id} não possui membership ACTIVE no tenant {membership.tenant_id}")
            raise HTTPException(
                status_code=403,
                detail=f"Account {body.account_id} não pertence ao tenant atual",
            )

        # Validar hospital_id se fornecido
        if body.hospital_id is not None:
            hospital = session.get(Hospital, body.hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != membership.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

        profile = Profile(
            tenant_id=membership.tenant_id,
            account_id=body.account_id,
            hospital_id=body.hospital_id,
            attribute=body.attribute,
        )

        session.add(profile)
        session.commit()
        session.refresh(profile)
        logger.info(f"Profile criado com sucesso: id={profile.id}")
        return profile
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Erro de integridade ao criar profile: {error_msg}", exc_info=True)

        # Verificar se é erro de constraint única de profile
        error_lower = error_msg.lower()
        if "uq_profile_tenant_account" in error_lower or "uq_profile_tenant_account_no_hospital" in error_lower:
            # Determinar mensagem baseada no hospital_id
            if body.hospital_id is None:
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um perfil para esta conta sem hospital associado. Cada conta pode ter apenas um perfil geral (sem hospital).",
                ) from e
            else:
                # Buscar nome do hospital para mensagem mais amigável
                hospital = session.get(Hospital, body.hospital_id)
                hospital_name = hospital.name if hospital else "este hospital"
                raise HTTPException(
                    status_code=409,
                    detail=f"Já existe um perfil para esta conta no hospital '{hospital_name}'. Cada conta pode ter apenas um perfil por hospital.",
                ) from e
        else:
            # Outro tipo de erro de integridade
            raise HTTPException(
                status_code=409,
                detail="Erro de integridade: os dados fornecidos violam uma regra de negócio. Verifique se já existe um perfil com essas informações.",
            ) from e
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao criar profile: {e}", exc_info=True)
        sanitized_message = _sanitize_error_message(e, "Erro ao criar perfil. Tente novamente.")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar perfil: {sanitized_message}",
        ) from e


@router.get("/profile/list", response_model=ProfileListResponse, tags=["Profile"])
def list_profile(
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Lista profiles do tenant atual com paginação.
    """
    try:
        logger.info(f"Listando profiles para tenant_id={membership.tenant_id}, limit={limit}, offset={offset}")
        query = select(Profile).where(Profile.tenant_id == membership.tenant_id)

        # Contar total
        total_query = select(func.count(Profile.id)).where(Profile.tenant_id == membership.tenant_id)
        total = session.exec(total_query).one()

        # Buscar itens com paginação
        items = session.exec(query.order_by(Profile.created_at.desc()).offset(offset).limit(limit)).all()

        logger.info(f"Encontrados {total} profiles, retornando {len(items)}")

        return ProfileListResponse(
            items=items,
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar profiles: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar profiles: {str(e)}",
        ) from e


@router.get("/profile/{profile_id}", response_model=ProfileResponse, tags=["Profile"])
def get_profile(
    profile_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Obtém detalhes de um profile específico.
    Valida que o profile pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando profile id={profile_id} para tenant_id={membership.tenant_id}")
        profile = session.get(Profile, profile_id)
        if not profile:
            logger.warning(f"Profile não encontrado: id={profile_id}")
            raise HTTPException(status_code=404, detail="Profile não encontrado")
        if profile.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: profile.tenant_id={profile.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        logger.info(f"Profile encontrado: id={profile.id}")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar profile: {str(e)}",
        ) from e


@router.put("/profile/{profile_id}", response_model=ProfileResponse, tags=["Profile"])
def update_profile(
    profile_id: int,
    body: ProfileUpdate,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Atualiza um profile.
    Valida que o profile pertence ao tenant atual.
    Não permite alterar tenant_id ou account_id.
    """
    try:
        logger.info(f"Atualizando profile: id={profile_id}, tenant_id={membership.tenant_id}")

        profile = session.get(Profile, profile_id)
        if not profile:
            logger.warning(f"Profile não encontrado: id={profile_id}")
            raise HTTPException(status_code=404, detail="Profile não encontrado")
        if profile.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: profile.tenant_id={profile.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar hospital_id se fornecido
        if body.hospital_id is not None:
            hospital = session.get(Hospital, body.hospital_id)
            if not hospital:
                raise HTTPException(status_code=404, detail="Hospital não encontrado")
            if hospital.tenant_id != membership.tenant_id:
                raise HTTPException(status_code=403, detail="Hospital não pertence ao tenant atual")

        # Atualizar campos permitidos (nunca permitir alterar tenant_id ou account_id)
        if body.hospital_id is not None:
            profile.hospital_id = body.hospital_id
        if body.attribute is not None:
            profile.attribute = body.attribute
        profile.updated_at = utc_now()

        session.add(profile)
        session.commit()
        session.refresh(profile)
        logger.info(f"Profile atualizado com sucesso: id={profile.id}")
        return profile
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Erro de integridade ao atualizar profile: {error_msg}", exc_info=True)

        # Verificar se é erro de constraint única de profile
        error_lower = error_msg.lower()
        if "uq_profile_tenant_account" in error_lower or "uq_profile_tenant_account_no_hospital" in error_lower:
            # Determinar mensagem baseada no hospital_id
            new_hospital_id = body.hospital_id if body.hospital_id is not None else profile.hospital_id
            if new_hospital_id is None:
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um perfil para esta conta sem hospital associado. Cada conta pode ter apenas um perfil geral (sem hospital).",
                ) from e
            else:
                # Buscar nome do hospital para mensagem mais amigável
                hospital = session.get(Hospital, new_hospital_id)
                hospital_name = hospital.name if hospital else "este hospital"
                raise HTTPException(
                    status_code=409,
                    detail=f"Já existe um perfil para esta conta no hospital '{hospital_name}'. Cada conta pode ter apenas um perfil por hospital.",
                ) from e
        else:
            # Outro tipo de erro de integridade
            raise HTTPException(
                status_code=409,
                detail="Erro de integridade: os dados fornecidos violam uma regra de negócio. Verifique se já existe um perfil com essas informações.",
            ) from e
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar profile: {e}", exc_info=True)
        sanitized_message = _sanitize_error_message(e, "Erro ao atualizar perfil. Tente novamente.")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar perfil: {sanitized_message}",
        ) from e


@router.delete("/profile/{profile_id}", status_code=204, tags=["Profile"])
def delete_profile(
    profile_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Exclui um profile.
    Valida que o profile pertence ao tenant atual.
    """
    try:
        logger.info(f"Deletando profile id={profile_id} para tenant_id={membership.tenant_id}")

        profile = session.get(Profile, profile_id)
        if not profile:
            logger.warning(f"Profile não encontrado: id={profile_id}")
            raise HTTPException(status_code=404, detail="Profile não encontrado")
        if profile.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: profile.tenant_id={profile.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        session.delete(profile)
        session.commit()
        logger.info(f"Profile excluído com sucesso: id={profile_id}")
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao excluir profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao excluir profile: {str(e)}",
        ) from e


@router.post("/professional", response_model=ProfessionalResponse, status_code=201, tags=["Professional"])
def create_professional(
    body: ProfessionalCreate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo profissional (apenas admin).
    Profissional sempre pertence ao tenant atual (do membership).
    """
    try:
        logger.info(f"Criando profissional: name={body.name}, tenant_id={membership.tenant_id}")

        # Verificar se já existe profissional com mesmo nome no tenant
        existing = session.exec(
            select(Professional).where(
                Professional.tenant_id == membership.tenant_id,
                Professional.name == body.name,
            )
        ).first()
        if existing:
            logger.warning(f"Profissional com nome '{body.name}' já existe no tenant {membership.tenant_id} (id={existing.id})")
            raise HTTPException(
                status_code=409,
                detail=f"Profissional com nome '{body.name}' já existe neste tenant",
            )

        professional = Professional(
            tenant_id=membership.tenant_id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            notes=body.notes,
            active=body.active,
        )

        session.add(professional)
        try:
            session.commit()
            logger.info(f"Profissional criado com sucesso: id={professional.id}")
            session.refresh(professional)
            return professional
        except IntegrityError as e:
            session.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Erro de integridade ao criar profissional: {error_msg}", exc_info=True)

            # Verificar se é erro de constraint única
            if "uq_professional_tenant_name" in error_msg.lower() or "unique constraint" in error_msg.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Profissional com nome '{body.name}' já existe neste tenant",
                ) from e
            else:
                # Outro tipo de erro de integridade
                raise HTTPException(
                    status_code=409,
                    detail=f"Erro de integridade ao criar profissional: {error_msg}",
                ) from e
        except Exception as e:
            session.rollback()
            logger.error(f"Erro inesperado ao criar profissional: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar profissional: {str(e)}",
            ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro crítico ao criar profissional: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao criar profissional: {str(e)}",
        ) from e


@router.get("/professional/list", response_model=ProfessionalListResponse, tags=["Professional"])
def list_professional(
    q: Optional[str] = Query(None, description="Busca por nome (case-insensitive)"),
    active: Optional[bool] = Query(None, description="Filtrar por active"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de itens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Lista profissionais do tenant atual, com filtros opcionais e paginação.
    Sempre filtra por tenant_id do JWT (via membership).
    Ordena por name crescente.
    """
    try:
        logger.info(f"Listando profissionais para tenant_id={membership.tenant_id}")

        # Query base - sempre filtrar por tenant_id
        query = select(Professional).where(Professional.tenant_id == membership.tenant_id)

        # Aplicar filtros
        if q is not None and q.strip():
            # Busca por nome (case-insensitive)
            query = query.where(func.lower(Professional.name).contains(func.lower(q.strip())))

        if active is not None:
            query = query.where(Professional.active == active)

        # Contar total (antes de aplicar limit/offset)
        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()

        # Aplicar ordenação, limit e offset
        query = query.order_by(Professional.name).offset(offset).limit(limit)
        items = session.exec(query).all()

        logger.info(f"Encontrados {total} profissionais (retornando {len(items)})")

        return ProfessionalListResponse(items=list(items), total=total)
    except Exception as e:
        logger.error(f"Erro ao listar profissionais: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar profissionais: {str(e)}",
        ) from e


@router.get("/professional/{professional_id}", response_model=ProfessionalResponse, tags=["Professional"])
def get_professional(
    professional_id: int,
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Busca um profissional específico.
    Valida que o profissional pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando profissional id={professional_id} para tenant_id={membership.tenant_id}")
        professional = session.get(Professional, professional_id)
        if not professional:
            logger.warning(f"Profissional não encontrado: id={professional_id}")
            raise HTTPException(status_code=404, detail="Profissional não encontrado")
        if professional.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: professional.tenant_id={professional.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        logger.info(f"Profissional encontrado: id={professional.id}")
        return professional
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar profissional: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar profissional: {str(e)}",
        ) from e


@router.put("/professional/{professional_id}", response_model=ProfessionalResponse, tags=["Professional"])
def update_professional(
    professional_id: int,
    body: ProfessionalUpdate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um profissional (apenas admin).
    Valida que o profissional pertence ao tenant atual.
    Não permite alterar tenant_id.
    """
    try:
        logger.info(f"Atualizando profissional: id={professional_id}, tenant_id={membership.tenant_id}")

        professional = session.get(Professional, professional_id)
        if not professional:
            logger.warning(f"Profissional não encontrado: id={professional_id}")
            raise HTTPException(status_code=404, detail="Profissional não encontrado")
        if professional.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: professional.tenant_id={professional.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Verificar se nome está sendo alterado e se já existe outro com o mesmo nome
        if body.name is not None and body.name != professional.name:
            existing = session.exec(
                select(Professional).where(
                    Professional.tenant_id == membership.tenant_id,
                    Professional.name == body.name,
                    Professional.id != professional_id,
                )
            ).first()
            if existing:
                logger.warning(f"Profissional com nome '{body.name}' já existe no tenant {membership.tenant_id} (id={existing.id})")
                raise HTTPException(
                    status_code=409,
                    detail=f"Profissional com nome '{body.name}' já existe neste tenant",
                )

        # Atualizar campos (NUNCA permitir alterar tenant_id)
        if body.name is not None:
            professional.name = body.name
        if body.email is not None:
            professional.email = body.email
        if body.phone is not None:
            professional.phone = body.phone
        if body.notes is not None:
            professional.notes = body.notes
        if body.active is not None:
            professional.active = body.active

        # Atualizar updated_at
        professional.updated_at = utc_now()

        try:
            session.add(professional)
            session.commit()
            session.refresh(professional)
            logger.info(f"Profissional atualizado com sucesso: id={professional.id}")
            return professional
        except IntegrityError as e:
            session.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Erro de integridade ao atualizar profissional: {error_msg}", exc_info=True)

            # Verificar se é erro de constraint única
            if "uq_professional_tenant_name" in error_msg.lower() or "unique constraint" in error_msg.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Profissional com nome '{body.name or professional.name}' já existe neste tenant",
                ) from e
            else:
                raise HTTPException(
                    status_code=409,
                    detail=f"Erro de integridade ao atualizar profissional: {error_msg}",
                ) from e
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar profissional: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar profissional: {str(e)}",
        ) from e


@router.delete("/professional/{professional_id}", status_code=204, tags=["Professional"])
def delete_professional(
    professional_id: int,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Exclui um profissional (apenas admin).
    Valida que o profissional pertence ao tenant atual.
    Hard delete no MVP (igual arquivos).
    """
    try:
        logger.info(f"Deletando profissional id={professional_id} para tenant_id={membership.tenant_id}")

        professional = session.get(Professional, professional_id)
        if not professional:
            logger.warning(f"Profissional não encontrado: id={professional_id}")
            raise HTTPException(status_code=404, detail="Profissional não encontrado")
        if professional.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: professional.tenant_id={professional.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        session.delete(professional)
        session.commit()
        logger.info(f"Profissional excluído com sucesso: id={professional_id}")
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao excluir profissional: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao excluir profissional: {str(e)}",
        ) from e


class ProfessionalInviteRequest(PydanticBaseModel):
    """Request para enviar convite a um profissional."""
    pass


@router.post("/professional/{professional_id}/invite", status_code=200, tags=["Professional"])
def send_professional_invite_email(
    professional_id: int,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Envia email de convite para um profissional se juntar à clínica.
    Apenas admin pode enviar convites.
    """
    try:
        professional = session.get(Professional, professional_id)
        if not professional:
            raise HTTPException(status_code=404, detail="Profissional não encontrado")

        if professional.tenant_id != membership.tenant_id:
            raise HTTPException(status_code=403, detail="Acesso negado")

        tenant = session.get(Tenant, membership.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        logger.info(
            f"[INVITE] Iniciando envio de convite para profissional ID={professional_id} "
            f"(email={professional.email}, tenant_id={membership.tenant_id})"
        )

        # Enviar email de convite
        try:
            result = send_professional_invite(
                to_email=professional.email,
                professional_name=professional.name,
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
                f"[INVITE] ❌ FALHA - Envio de convite falhou para profissional ID={professional_id} "
                f"(email={professional.email}): {error_message}"
            )
            raise HTTPException(
                status_code=500,
                detail=error_message or "Erro ao enviar email de convite. Tente novamente mais tarde."
            )

        logger.info(
            f"[INVITE] ✅ SUCESSO - Convite enviado com sucesso para profissional ID={professional_id} "
            f"(email={professional.email})"
        )
        return {"message": "Convite enviado com sucesso", "email": professional.email}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar convite para profissional {professional_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar convite: {str(e)}",
        ) from e


# ============================================================================
# MEMBERSHIP ENDPOINTS
# ============================================================================

class MembershipCreate(PydanticBaseModel):
    """Schema para criar membership."""
    account_id: int
    role: str
    status: str = "ACTIVE"

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


class MembershipUpdate(PydanticBaseModel):
    """Schema para atualizar membership."""
    role: Optional[str] = None
    status: Optional[str] = None

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


class MembershipResponse(PydanticBaseModel):
    """Schema de resposta para membership."""
    id: int
    tenant_id: int
    account_id: int
    account_email: Optional[str] = None
    account_name: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MembershipListResponse(PydanticBaseModel):
    """Schema de resposta para listagem de memberships."""
    items: list[MembershipResponse]
    total: int


@router.post("/membership", response_model=MembershipResponse, status_code=201, tags=["Membership"])
def create_membership(
    body: MembershipCreate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Cria um novo membership (apenas admin).
    Valida que o account existe e que não há membership duplicado.
    """
    try:
        logger.info(f"Criando membership: account_id={body.account_id}, tenant_id={membership.tenant_id}, role={body.role}, status={body.status}")

        # Verificar se account existe
        account = session.get(Account, body.account_id)
        if not account:
            logger.warning(f"Account não encontrado: id={body.account_id}")
            raise HTTPException(status_code=404, detail="Account não encontrado")

        # Verificar se já existe membership para este account no tenant
        existing_membership = session.exec(
            select(Membership).where(
                Membership.account_id == body.account_id,
                Membership.tenant_id == membership.tenant_id,
            )
        ).first()
        if existing_membership:
            logger.warning(f"Membership já existe para account {body.account_id} no tenant {membership.tenant_id}")
            raise HTTPException(
                status_code=409,
                detail="Já existe um membership para este account neste tenant",
            )

        # Criar membership
        membership_obj = Membership(
            tenant_id=membership.tenant_id,
            account_id=body.account_id,
            role=MembershipRole[body.role.upper()],
            status=MembershipStatus[body.status.upper()],
        )
        session.add(membership_obj)
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="Membership duplicado (tenant_id, account_id) não permitido",
            ) from e
        session.refresh(membership_obj)

        # Log de auditoria
        _try_write_audit_log(
            session,
            AuditLog(
                tenant_id=membership.tenant_id,
                actor_account_id=membership.account_id,
                membership_id=membership_obj.id,
                event_type="membership_invited",
                data={
                    "target_account_id": body.account_id,
                    "email": account.email,
                    "from_status": None,
                    "to_status": membership_obj.status.value,
                    "from_role": None,
                    "to_role": membership_obj.role.value,
                },
            ),
        )

        logger.info(f"Membership criado com sucesso: id={membership_obj.id}")
        return MembershipResponse(
            id=membership_obj.id,
            tenant_id=membership_obj.tenant_id,
            account_id=membership_obj.account_id,
            account_email=account.email,
            account_name=account.name,
            role=membership_obj.role.value,
            status=membership_obj.status.value,
            created_at=membership_obj.created_at,
            updated_at=membership_obj.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao criar membership: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar membership: {str(e)}",
        ) from e


@router.get("/membership/list", response_model=MembershipListResponse, tags=["Membership"])
def list_memberships(
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None, description="Filtrar por status (PENDING, ACTIVE, REJECTED, REMOVED)"),
    role: Optional[str] = Query(default=None, description="Filtrar por role (admin, account)"),
):
    """
    Lista memberships do tenant atual (apenas admin).
    Sempre filtra por tenant_id do JWT (via membership).
    """
    try:
        logger.info(f"Listando memberships para tenant_id={membership.tenant_id}, limit={limit}, offset={offset}")

        # Query base: memberships do tenant com join em Account
        query = (
            select(Membership, Account)
            .join(Account, Membership.account_id == Account.id)
            .where(Membership.tenant_id == membership.tenant_id)
        )

        # Aplicar filtros
        if status:
            status_upper = status.strip().upper()
            if status_upper in {"PENDING", "ACTIVE", "REJECTED", "REMOVED"}:
                query = query.where(Membership.status == MembershipStatus[status_upper])
        if role:
            role_lower = role.strip().lower()
            if role_lower in {"admin", "account"}:
                query = query.where(Membership.role == MembershipRole[role_lower.upper()])

        # Contar total
        count_query = (
            select(func.count(Membership.id))
            .join(Account, Membership.account_id == Account.id)
            .where(Membership.tenant_id == membership.tenant_id)
        )
        if status:
            status_upper = status.strip().upper()
            if status_upper in {"PENDING", "ACTIVE", "REJECTED", "REMOVED"}:
                count_query = count_query.where(Membership.status == MembershipStatus[status_upper])
        if role:
            role_lower = role.strip().lower()
            if role_lower in {"admin", "account"}:
                count_query = count_query.where(Membership.role == MembershipRole[role_lower.upper()])

        total = session.exec(count_query).one()

        # Aplicar paginação e ordenação
        query = query.order_by(Membership.created_at.desc()).limit(limit).offset(offset)

        # Executar query
        results = session.exec(query).all()

        # Montar resposta
        items = []
        for membership_obj, account in results:
            items.append(
                MembershipResponse(
                    id=membership_obj.id,
                    tenant_id=membership_obj.tenant_id,
                    account_id=membership_obj.account_id,
                    account_email=account.email,
                    account_name=account.name,
                    role=membership_obj.role.value,
                    status=membership_obj.status.value,
                    created_at=membership_obj.created_at,
                    updated_at=membership_obj.updated_at,
                )
            )

        logger.info(f"Retornando {len(items)} memberships de {total} total")
        return MembershipListResponse(items=items, total=total)
    except Exception as e:
        logger.error(f"Erro ao listar memberships: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar memberships: {str(e)}",
        ) from e


@router.get("/membership/{membership_id}", response_model=MembershipResponse, tags=["Membership"])
def get_membership(
    membership_id: int,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Busca um membership específico (apenas admin).
    Valida que o membership pertence ao tenant atual.
    """
    try:
        logger.info(f"Buscando membership id={membership_id} para tenant_id={membership.tenant_id}")

        membership_obj = session.get(Membership, membership_id)
        if not membership_obj:
            logger.warning(f"Membership não encontrado: id={membership_id}")
            raise HTTPException(status_code=404, detail="Membership não encontrado")
        if membership_obj.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: membership.tenant_id={membership_obj.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Buscar account
        account = session.get(Account, membership_obj.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account não encontrado")

        return MembershipResponse(
            id=membership_obj.id,
            tenant_id=membership_obj.tenant_id,
            account_id=membership_obj.account_id,
            account_email=account.email,
            account_name=account.name,
            role=membership_obj.role.value,
            status=membership_obj.status.value,
            created_at=membership_obj.created_at,
            updated_at=membership_obj.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar membership: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar membership: {str(e)}",
        ) from e


@router.put("/membership/{membership_id}", response_model=MembershipResponse, tags=["Membership"])
def update_membership(
    membership_id: int,
    body: MembershipUpdate,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Atualiza um membership (apenas admin).
    Permite alterar role e status.
    Valida que o membership pertence ao tenant atual.
    """
    try:
        logger.info(f"Atualizando membership id={membership_id} para tenant_id={membership.tenant_id}")

        membership_obj = session.get(Membership, membership_id)
        if not membership_obj:
            logger.warning(f"Membership não encontrado: id={membership_id}")
            raise HTTPException(status_code=404, detail="Membership não encontrado")
        if membership_obj.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: membership.tenant_id={membership_obj.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar regras de negócio
        if body.status and body.status.upper() == "REMOVED":
            # Não permitir remover o último membership ACTIVE de um account
            if membership_obj.status == MembershipStatus.ACTIVE:
                active_count = session.exec(
                    select(func.count())
                    .select_from(Membership)
                    .where(
                        Membership.account_id == membership_obj.account_id,
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

        # Atualizar campos
        prev_status = membership_obj.status
        prev_role = membership_obj.role

        if body.role is not None:
            membership_obj.role = MembershipRole[body.role.upper()]
        if body.status is not None:
            membership_obj.status = MembershipStatus[body.status.upper()]

        membership_obj.updated_at = utc_now()
        session.add(membership_obj)
        session.commit()
        session.refresh(membership_obj)

        # Log de auditoria se houver mudanças
        if prev_status != membership_obj.status or prev_role != membership_obj.role:
            _try_write_audit_log(
                session,
                AuditLog(
                    tenant_id=membership.tenant_id,
                    actor_account_id=membership.account_id,
                    membership_id=membership_obj.id,
                    event_type="membership_status_changed",
                    data={
                        "target_account_id": membership_obj.account_id,
                        "from_status": prev_status.value,
                        "to_status": membership_obj.status.value,
                        "from_role": prev_role.value,
                        "to_role": membership_obj.role.value,
                    },
                ),
            )

        # Buscar account
        account = session.get(Account, membership_obj.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account não encontrado")

        logger.info(f"Membership atualizado com sucesso: id={membership_id}")
        return MembershipResponse(
            id=membership_obj.id,
            tenant_id=membership_obj.tenant_id,
            account_id=membership_obj.account_id,
            account_email=account.email,
            account_name=account.name,
            role=membership_obj.role.value,
            status=membership_obj.status.value,
            created_at=membership_obj.created_at,
            updated_at=membership_obj.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar membership: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar membership: {str(e)}",
        ) from e


@router.delete("/membership/{membership_id}", status_code=204, tags=["Membership"])
def delete_membership(
    membership_id: int,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Remove (soft-delete) um membership (status -> REMOVED) (apenas admin).
    Valida que o membership pertence ao tenant atual.
    Regra de segurança: não permitir remover o último membership ACTIVE de um account.
    """
    try:
        logger.info(f"Removendo membership id={membership_id} para tenant_id={membership.tenant_id}")

        membership_obj = session.get(Membership, membership_id)
        if not membership_obj:
            logger.warning(f"Membership não encontrado: id={membership_id}")
            raise HTTPException(status_code=404, detail="Membership não encontrado")
        if membership_obj.tenant_id != membership.tenant_id:
            logger.warning(f"Acesso negado: membership.tenant_id={membership_obj.tenant_id}, membership.tenant_id={membership.tenant_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Validar regra de segurança
        if membership_obj.status == MembershipStatus.ACTIVE:
            active_count = session.exec(
                select(func.count())
                .select_from(Membership)
                .where(
                    Membership.account_id == membership_obj.account_id,
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

        prev_status = membership_obj.status
        membership_obj.status = MembershipStatus.REMOVED
        membership_obj.updated_at = utc_now()
        session.add(membership_obj)
        session.commit()
        session.refresh(membership_obj)

        # Log de auditoria
        _try_write_audit_log(
            session,
            AuditLog(
                tenant_id=membership.tenant_id,
                actor_account_id=membership.account_id,
                membership_id=membership_obj.id,
                event_type="membership_status_changed",
                data={
                    "target_account_id": membership_obj.account_id,
                    "from_status": prev_status.value,
                    "to_status": membership_obj.status.value,
                },
            ),
        )

        logger.info(f"Membership removido com sucesso: id={membership_id}")
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao remover membership: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao remover membership: {str(e)}",
        ) from e


@router.post("/membership/{membership_id}/invite", status_code=200, tags=["Membership"])
def send_membership_invite_email(
    membership_id: int,
    membership: Membership = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    """
    Envia email de convite para um membership e atualiza status para PENDING.
    Apenas admin pode enviar convites.
    """
    try:
        membership_obj = session.get(Membership, membership_id)
        if not membership_obj:
            raise HTTPException(status_code=404, detail="Membership não encontrado")

        if membership_obj.tenant_id != membership.tenant_id:
            raise HTTPException(status_code=403, detail="Acesso negado")

        tenant = session.get(Tenant, membership.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        account = session.get(Account, membership_obj.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account não encontrado")

        logger.info(
            f"[INVITE] Iniciando envio de convite para membership ID={membership_id} "
            f"(email={account.email}, tenant_id={membership.tenant_id})"
        )

        # Atualizar status para PENDING antes de enviar o email
        prev_status = membership_obj.status
        if membership_obj.status != MembershipStatus.PENDING:
            membership_obj.status = MembershipStatus.PENDING
            membership_obj.updated_at = utc_now()
            session.add(membership_obj)
            session.commit()
            session.refresh(membership_obj)

            # Log de auditoria se status mudou
            if prev_status != membership_obj.status:
                _try_write_audit_log(
                    session,
                    AuditLog(
                        tenant_id=membership.tenant_id,
                        actor_account_id=membership.account_id,
                        membership_id=membership_obj.id,
                        event_type="membership_status_changed",
                        data={
                            "target_account_id": account.id,
                            "from_status": prev_status.value,
                            "to_status": membership_obj.status.value,
                        },
                    ),
                )

        # Enviar email de convite
        try:
            result = send_professional_invite(
                to_email=account.email,
                professional_name=account.name or account.email,
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
                f"[INVITE] ❌ FALHA - Envio de convite falhou para membership ID={membership_id} "
                f"(email={account.email}): {error_message}"
            )
            raise HTTPException(
                status_code=500,
                detail=error_message or "Erro ao enviar email de convite. Tente novamente mais tarde."
            )

        logger.info(
            f"[INVITE] ✅ SUCESSO - Convite enviado com sucesso para membership ID={membership_id} "
            f"(email={account.email})"
        )
        return {"message": "Convite enviado com sucesso", "email": account.email}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar convite para membership {membership_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar convite: {str(e)}",
        ) from e
