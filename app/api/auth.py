import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db.session import get_session
from app.model.membership import Membership, MembershipRole, MembershipStatus
from app.model.audit_log import AuditLog
from app.model.account import Account
from app.model.tenant import Tenant
from app.services.hospital_service import create_default_hospital_for_tenant
from app.auth.jwt import create_access_token
from app.auth.oauth import verify_google_token
from app.auth.dependencies import get_current_account, get_current_membership
from app.model.base import utc_now

router = APIRouter(prefix="/auth", tags=["Auth"])

# Configuração de admin (opcional)
ADMIN_EMAILS_RAW = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAILS: set[str] = {e.strip().lower() for e in ADMIN_EMAILS_RAW.split(",") if e.strip()}
ADMIN_HOSTED_DOMAIN = os.getenv("ADMIN_HOSTED_DOMAIN")


def _try_write_audit_log(session: Session, audit: AuditLog) -> None:
    """
    Auditoria best-effort: não deve quebrar a request se falhar.
    """
    try:
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()


class GoogleTokenRequest(BaseModel):
    id_token: str


class TenantOption(BaseModel):
    tenant_id: int
    name: str
    slug: str
    role: str


class InviteOption(BaseModel):
    membership_id: int
    tenant_id: int
    name: str
    slug: str
    role: str
    status: str


class AuthResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    requires_tenant_selection: bool = False
    tenants: list[TenantOption] = []
    invites: list[InviteOption] = []


class TenantListResponse(BaseModel):
    tenants: list[TenantOption] = []
    invites: list[InviteOption] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DevTokenRequest(BaseModel):
    email: str
    name: str = "Dev Account"
    tenant_id: int | None = None


class GoogleSelectTenantRequest(BaseModel):
    id_token: str
    tenant_id: int



def _determine_role(email: str, hd: Optional[str] = None) -> str:
    """Determina a role da conta baseada em email e hosted domain."""
    email_lower = email.lower()

    if ADMIN_EMAILS and email_lower in ADMIN_EMAILS:
        return "admin"

    if ADMIN_HOSTED_DOMAIN and hd == ADMIN_HOSTED_DOMAIN:
        return "admin"

    return "account"


def _get_or_create_default_tenant(session: Session) -> Tenant:
    """Obtém ou cria um tenant padrão para novas contas."""
    # Por enquanto, cria um tenant padrão se não existir
    # Em produção, isso deve ser configurado ou a conta deve escolher durante registro
    default_tenant = session.exec(
        select(Tenant).where(Tenant.slug == "default")
    ).first()

    if not default_tenant:
        default_tenant = Tenant(name="Default Tenant", slug="default")
        session.add(default_tenant)
        session.commit()
        session.refresh(default_tenant)
        # Criar hospital default para o tenant recém-criado
        create_default_hospital_for_tenant(session, default_tenant.id)
    else:
        # Garantir que tenant existente também tenha hospital default
        create_default_hospital_for_tenant(session, default_tenant.id)

    return default_tenant


def _list_active_tenants_for_account(session: Session, *, account_id: int) -> list[TenantOption]:
    rows = session.exec(
        select(Tenant, Membership)
        .join(Membership, Membership.tenant_id == Tenant.id)
        .where(
            Membership.account_id == account_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Tenant.id.asc())
    ).all()

    opts: list[TenantOption] = []
    for tenant, membership in rows:
        opts.append(
            TenantOption(
                tenant_id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                role=membership.role.value,
            )
        )
    return opts


def _list_pending_invites_for_account(session: Session, *, account_id: int, email: str | None = None) -> list[InviteOption]:
    # Buscar invites por account_id OU por email (quando account_id é NULL)
    query = (
        select(Tenant, Membership)
        .join(Membership, Membership.tenant_id == Tenant.id)
        .where(Membership.status == MembershipStatus.PENDING)
    )

    if email:
        # Buscar por account_id OU por email (para memberships pendentes sem Account)
        query = query.where(
            (Membership.account_id == account_id) |
            ((Membership.account_id.is_(None)) & (Membership.email == email.lower()))
        )
    else:
        # Apenas por account_id
        query = query.where(Membership.account_id == account_id)

    rows = session.exec(query.order_by(Tenant.id.asc())).all()

    invites: list[InviteOption] = []
    for tenant, membership in rows:
        invites.append(
            InviteOption(
                membership_id=membership.id,
                tenant_id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                role=membership.role.value,
                status=membership.status.value,
            )
        )
    return invites


def get_account_memberships(session: Session, *, account_id: int, email: str | None = None) -> tuple[list[TenantOption], list[InviteOption]]:
    """
    Retorna (ACTIVE tenants, PENDING invites) para a conta.

    Args:
        account_id: ID do Account
        email: Email do Account (opcional, usado para buscar invites pendentes sem Account)
    """
    tenants = _list_active_tenants_for_account(session, account_id=account_id)
    invites = _list_pending_invites_for_account(session, account_id=account_id, email=email)
    return tenants, invites


def get_active_tenant_for_account(session: Session, *, account_id: int) -> int | None:
    """
    Seleção automática de tenant:
      - 0 ACTIVE: None
      - 1 ACTIVE: tenant_id
      - >1 ACTIVE: None (exige seleção)
    """
    tenants = _list_active_tenants_for_account(session, account_id=account_id)
    if len(tenants) == 1:
        return tenants[0].tenant_id
    return None


def _get_active_membership(
    session: Session, *, account_id: int, tenant_id: int
) -> Membership | None:
    return session.exec(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    ).first()


def _issue_token_for_membership(*, account: Account, membership: Membership) -> str:
    return create_access_token(
        account_id=account.id,
        tenant_id=membership.tenant_id,
    )


@router.post("/google", response_model=AuthResponse)
def auth_google(
    body: GoogleTokenRequest,
    session: Session = Depends(get_session),
):
    """
    Login com Google - apenas autentica se a conta já existe.

    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do sistema>", "token_type": "bearer"}
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]
    name = idinfo["name"]

    # Busca conta no banco (email é globalmente único)
    account = session.exec(
        select(Account).where(Account.email == email)
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada. Use a opção 'Cadastrar-se' para criar uma conta."
        )

    # Atualizar account.name apenas se estiver NULL/vazio (nunca sobrescrever edições manuais)
    if not account.name or account.name == "":
        if name and name != "":
            account.name = name
            session.add(account)
            session.commit()
            session.refresh(account)

    # Buscar e vincular Memberships PENDING com account_id NULL pelo email
    pending_memberships = session.exec(
        select(Membership).where(
            Membership.email == email.lower(),
            Membership.account_id.is_(None),
            Membership.status == MembershipStatus.PENDING,
        )
    ).all()

    for pending_membership in pending_memberships:
        # Vincular Account ao Membership
        pending_membership.account_id = account.id
        # Preencher membership.name se NULL
        if (pending_membership.name is None or pending_membership.name == "") and account.name and account.name != "":
            pending_membership.name = account.name
        session.add(pending_membership)

    if pending_memberships:
        session.commit()

    tenants, invites = get_account_memberships(session, account_id=account.id)

    # Se não há tenants ACTIVE nem invites PENDING, exige seleção (permite criar clínica)
    if len(tenants) == 0 and len(invites) == 0:
        return AuthResponse(requires_tenant_selection=True, tenants=[], invites=[])

    # Se não há tenants ACTIVE mas há invites, exige seleção
    if len(tenants) == 0:
        return AuthResponse(requires_tenant_selection=True, tenants=[], invites=invites)

    # Se há múltiplos tenants ACTIVE ou convites PENDING, exige seleção
    if len(tenants) > 1 or len(invites) > 0:
        return AuthResponse(requires_tenant_selection=True, tenants=tenants, invites=invites)

    # Único tenant ativo e sem convites -> emite token direto.
    only = tenants[0]
    membership = _get_active_membership(session, account_id=account.id, tenant_id=only.tenant_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Membership ACTIVE não encontrado para o tenant selecionado")

    # Preencher membership.name se NULL (usar account.name atualizado)
    if (membership.name is None or membership.name == "") and account.name and account.name != "":
        membership.name = account.name
        session.add(membership)
        session.commit()
        session.refresh(membership)

    token = _issue_token_for_membership(account=account, membership=membership)
    return AuthResponse(access_token=token)


@router.post("/google/register", response_model=AuthResponse)
def auth_google_register(
    body: GoogleTokenRequest,
    session: Session = Depends(get_session),
):
    """
    Cadastro com Google - cria a conta se não existir, ou autentica se já existe.

    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do sistema>", "token_type": "bearer"}
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]
    name = idinfo["name"]
    hd = idinfo.get("hd")

    # Verifica se a conta já existe
    account = session.exec(
        select(Account).where(Account.email == email)
    ).first()

    if not account:
        # Cria novo account (Account não possui tenant_id; o vínculo é via Membership)
        role = _determine_role(email, hd)
        tenant = _get_or_create_default_tenant(session)

        account = Account(
            email=email,
            name=name,
            role=role,
            auth_provider="google",
        )
        session.add(account)
        session.commit()
        session.refresh(account)

        membership = Membership(
            tenant_id=tenant.id,
            account_id=account.id,
            role=MembershipRole.ADMIN if role == "admin" else MembershipRole.ACCOUNT,
            status=MembershipStatus.ACTIVE,
            name=name,  # Preencher membership.name com nome do Google na criação
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

        token = _issue_token_for_membership(account=account, membership=membership)
        return AuthResponse(access_token=token)

    # Account já existe -> comportamento igual ao login (pode exigir seleção).
    # Também buscar e vincular Memberships PENDING
    pending_memberships = session.exec(
        select(Membership).where(
            Membership.email == email.lower(),
            Membership.account_id.is_(None),
            Membership.status == MembershipStatus.PENDING,
        )
    ).all()

    for pending_membership in pending_memberships:
        pending_membership.account_id = account.id
        if (pending_membership.name is None or pending_membership.name == "") and account.name and account.name != "":
            pending_membership.name = account.name
        session.add(pending_membership)

    if pending_memberships:
        session.commit()

    return auth_google(body=body, session=session)


@router.post("/google/select-tenant", response_model=TokenResponse)
def auth_google_select_tenant(
    body: GoogleSelectTenantRequest,
    session: Session = Depends(get_session),
):
    """
    Quando a conta tem múltiplos tenants ACTIVE, este endpoint emite o JWT do sistema
    para o tenant escolhido, validando via Google ID token + Membership.

    Permite também gerar token para aceitar convites (membership PENDING) quando
    o usuário não tem nenhum tenant ativo.
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]

    account = session.exec(select(Account).where(Account.email == email)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Primeiro, tentar buscar membership ACTIVE
    membership = _get_active_membership(session, account_id=account.id, tenant_id=body.tenant_id)

    # Se não encontrar ACTIVE, verificar se há membership PENDING (para aceitar convites)
    # Buscar por account_id OU por email (quando account_id é NULL)
    if not membership:
        membership_pending = session.exec(
            select(Membership).where(
                (Membership.account_id == account.id) |
                ((Membership.account_id.is_(None)) & (Membership.email == email.lower())),
                Membership.tenant_id == body.tenant_id,
                Membership.status == MembershipStatus.PENDING,
            )
        ).first()

        if membership_pending:
            # Se membership tem account_id NULL, vincular ao Account
            if membership_pending.account_id is None:
                membership_pending.account_id = account.id
                if (membership_pending.name is None or membership_pending.name == "") and account.name and account.name != "":
                    membership_pending.name = account.name
                # Preencher membership.email se NULL (sincronizar uma vez com account.email)
                if membership_pending.email is None or membership_pending.email == "":
                    if account.email:
                        membership_pending.email = account.email.lower()
                session.add(membership_pending)
                session.commit()
                session.refresh(membership_pending)

            # Permitir gerar token temporário para aceitar convite
            # O token será usado apenas para aceitar o convite, não para acessar o tenant
            token = create_access_token(
                account_id=account.id,
                tenant_id=body.tenant_id,
            )
            return TokenResponse(access_token=token)
        else:
            raise HTTPException(status_code=403, detail="Acesso negado (membership ACTIVE ou PENDING não encontrado)")

    token = _issue_token_for_membership(account=account, membership=membership)
    return TokenResponse(access_token=token)


@router.post("/dev/token", response_model=AuthResponse, tags=["Auth"])
def auth_dev_token(
    body: DevTokenRequest,
    session: Session = Depends(get_session),
):
    """
    Gera um JWT de desenvolvimento sem Google OAuth.

    Proteção: só funciona quando APP_ENV=dev.
    """
    if os.getenv("APP_ENV", "dev") != "dev":
        raise HTTPException(status_code=404, detail="Not found")

    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    account = session.exec(select(Account).where(Account.email == email)).first()
    if not account:
        tenant = _get_or_create_default_tenant(session)
        role = _determine_role(email)
        account = Account(
            email=email,
            name=body.name,
            role=role,
            auth_provider="dev",
        )
        session.add(account)
        session.commit()
        session.refresh(account)

        membership = Membership(
            tenant_id=tenant.id,
            account_id=account.id,
            role=MembershipRole.ADMIN if role == "admin" else MembershipRole.ACCOUNT,
            status=MembershipStatus.ACTIVE,
        )
        session.add(membership)
        session.commit()

    # Se tenant_id foi informado, emite token para ele (valida membership).
    if body.tenant_id is not None:
        membership = _get_active_membership(session, account_id=account.id, tenant_id=body.tenant_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Acesso negado (membership ACTIVE não encontrado)")
        token = _issue_token_for_membership(account=account, membership=membership)
        return AuthResponse(access_token=token)

    tenants, invites = get_account_memberships(session, account_id=account.id, email=account.email)
    if not tenants:
        raise HTTPException(status_code=403, detail="Conta sem acesso a nenhum tenant (membership ACTIVE ausente)")
    if len(tenants) > 1:
        return AuthResponse(requires_tenant_selection=True, tenants=tenants)

    only = tenants[0]
    membership = _get_active_membership(session, account_id=account.id, tenant_id=only.tenant_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Membership ACTIVE não encontrado para o tenant selecionado")
    token = _issue_token_for_membership(account=account, membership=membership)
    return AuthResponse(access_token=token)


@router.get("/tenant/list", response_model=TenantListResponse, tags=["Auth"])
def list_my_tenants(
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """Lista tenants ACTIVE disponíveis e convites PENDING para a conta autenticada."""
    tenants, invites = get_account_memberships(session, account_id=account.id, email=account.email)
    return TenantListResponse(tenants=tenants, invites=invites)


@router.get("/invites", response_model=list[InviteOption], tags=["Auth"])
def list_my_invites(
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """Lista convites PENDING da conta autenticada."""
    return _list_pending_invites_for_account(session, account_id=account.id)


class InviteActionResponse(BaseModel):
    membership_id: int
    tenant_id: int
    status: str


@router.post("/invites/{membership_id}/accept", response_model=InviteActionResponse, tags=["Auth"])
def accept_invite(
    membership_id: int,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """
    Aceita um convite (membership PENDING) e o torna ACTIVE.

    Requer autenticação do account (via token JWT), mas não requer membership ACTIVE.
    Isso permite aceitar o primeiro convite mesmo sem ter nenhum tenant ativo.

    Se membership.account_id for NULL, vincula o Account ao Membership pelo email.
    """
    membership = session.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Verificar se o convite pertence ao account autenticado
    # Se account_id é NULL, verificar pelo email
    if membership.account_id is not None:
        if membership.account_id != account.id:
            raise HTTPException(status_code=403, detail="Acesso negado")
    else:
        # Membership pendente sem Account - verificar pelo email
        if membership.email != account.email.lower():
            raise HTTPException(status_code=403, detail="Acesso negado (email não corresponde)")
        # Vincular Account ao Membership
        membership.account_id = account.id

    if membership.status != MembershipStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invite is not PENDING")

    prev_status = membership.status
    membership.status = MembershipStatus.ACTIVE
    membership.updated_at = utc_now()

    # Preencher membership.name se NULL (usar account.name do Google)
    if membership.name is None or membership.name == "":
        if account.name and account.name != "":
            membership.name = account.name

    # Preencher membership.email se NULL (sincronizar uma vez com account.email)
    if membership.email is None or membership.email == "":
        if account.email:
            membership.email = account.email.lower()

    session.add(membership)
    session.commit()
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=membership.tenant_id,
            actor_account_id=account.id,
            membership_id=membership.id,
            event_type="membership_status_changed",
            data={
                "from_status": prev_status.value,
                "to_status": membership.status.value,
            },
        ),
    )
    return InviteActionResponse(
        membership_id=membership.id,
        tenant_id=membership.tenant_id,
        status=membership.status.value,
    )


@router.post("/invites/{membership_id}/reject", response_model=InviteActionResponse, tags=["Auth"])
def reject_invite(
    membership_id: int,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    membership = session.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Invite not found")
    if membership.account_id != account.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if membership.status != MembershipStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invite is not PENDING")

    prev_status = membership.status
    membership.status = MembershipStatus.REJECTED
    membership.updated_at = utc_now()
    session.add(membership)
    session.commit()
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=membership.tenant_id,
            actor_account_id=account.id,
            membership_id=membership.id,
            event_type="membership_status_changed",
            data={
                "from_status": prev_status.value,
                "to_status": membership.status.value,
            },
        ),
    )
    return InviteActionResponse(
        membership_id=membership.id,
        tenant_id=membership.tenant_id,
        status=membership.status.value,
    )


class SwitchTenantRequest(BaseModel):
    tenant_id: int


@router.post("/switch-tenant", response_model=TokenResponse, tags=["Auth"])
def switch_tenant(
    body: SwitchTenantRequest,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """
    Emite um novo JWT do sistema para outro tenant (sem passar pelo Google novamente).

    Permite também gerar token para aceitar convites (membership PENDING) quando
    o usuário não tem nenhum tenant ativo.
    """
    # Tentar obter membership ACTIVE primeiro
    membership = _get_active_membership(session, account_id=account.id, tenant_id=body.tenant_id)

    # Se não encontrar ACTIVE, verificar se há membership PENDING (para aceitar convites)
    # Buscar por account_id OU por email (quando account_id é NULL)
    if not membership:
        membership_pending = session.exec(
            select(Membership).where(
                (Membership.account_id == account.id) |
                ((Membership.account_id.is_(None)) & (Membership.email == account.email.lower())),
                Membership.tenant_id == body.tenant_id,
                Membership.status == MembershipStatus.PENDING,
            )
        ).first()

        if membership_pending:
            # Se membership tem account_id NULL, vincular ao Account
            if membership_pending.account_id is None:
                membership_pending.account_id = account.id
                if (membership_pending.name is None or membership_pending.name == "") and account.name and account.name != "":
                    membership_pending.name = account.name
                # Preencher membership.email se NULL (sincronizar uma vez com account.email)
                if membership_pending.email is None or membership_pending.email == "":
                    if account.email:
                        membership_pending.email = account.email.lower()
                session.add(membership_pending)
                session.commit()
                session.refresh(membership_pending)

            # Permitir gerar token temporário para aceitar convite
            # O token será usado apenas para aceitar o convite, não para acessar o tenant
            token = create_access_token(
                account_id=account.id,
                tenant_id=body.tenant_id,
            )
            return TokenResponse(access_token=token)
        else:
            raise HTTPException(status_code=403, detail="Acesso negado (membership ACTIVE ou PENDING não encontrado)")

    # Se encontrou membership ACTIVE, tentar obter current_membership para log de auditoria
    # Mas não falhar se não houver (permite aceitar primeiro convite)
    try:
        from app.auth.dependencies import get_token_payload
        from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
        bearer = HTTPBearer(auto_error=False)
        # Tentar obter token do header
        # Como já temos account autenticado, podemos tentar buscar membership atual do token
        # Mas isso é opcional - se não houver, apenas não fazemos log de auditoria
        pass  # Simplificar: não fazer log de auditoria se não houver current_membership
    except:
        pass  # Ignorar erro de auditoria se não houver current_membership

    token = _issue_token_for_membership(account=account, membership=membership)
    return TokenResponse(access_token=token)


@router.post("/google/create-tenant", response_model=TokenResponse, tags=["Auth"])
def auth_google_create_tenant(
    body: GoogleTokenRequest,
    session: Session = Depends(get_session),
):
    """
    Cria um novo tenant automaticamente usando id_token do Google.
    Usado quando o account não tem nenhum tenant ACTIVE.

    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do sistema>", "token_type": "bearer"}
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]
    name = idinfo["name"]

    # Busca conta no banco (email é globalmente único)
    account = session.exec(
        select(Account).where(Account.email == email)
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada. Use a opção 'Cadastrar-se' para criar uma conta."
        )

    # Verificar se já tem tenants ACTIVE (não deve usar este endpoint se tiver)
    # Também buscar e vincular Memberships PENDING
    pending_memberships = session.exec(
        select(Membership).where(
            Membership.email == email.lower(),
            Membership.account_id.is_(None),
            Membership.status == MembershipStatus.PENDING,
        )
    ).all()

    for pending_membership in pending_memberships:
        pending_membership.account_id = account.id
        if (pending_membership.name is None or pending_membership.name == "") and account.name and account.name != "":
            pending_membership.name = account.name
        session.add(pending_membership)

    if pending_memberships:
        session.commit()

    tenants, invites = get_account_memberships(session, account_id=account.id, email=email)
    if len(tenants) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account já possui tenants ACTIVE. Use o endpoint de seleção de tenant."
        )

    # Criar tenant com dados default
    timestamp = int(utc_now().timestamp() * 1000)
    slug = f"clinica-{timestamp}"

    # Verificar se slug já existe (muito improvável, mas por segurança)
    existing = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
    if existing:
        # Tentar com sufixo aleatório
        import random
        slug = f"clinica-{timestamp}-{random.randint(1000, 9999)}"
        existing = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar slug único para o tenant"
            )

    tenant = Tenant(
        name="Clínica",
        slug=slug,
        timezone="America/Sao_Paulo",
        locale="pt-BR",
        currency="BRL",
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    # Criar hospital default para o tenant
    create_default_hospital_for_tenant(session, tenant.id)

    # Criar membership ADMIN/ACTIVE para o criador
    membership = Membership(
        tenant_id=tenant.id,
        account_id=account.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
        name=account.name if account.name else None,  # Preencher membership.name com account.name
    )
    session.add(membership)
    session.commit()
    session.refresh(membership)

    # Criar professional automaticamente para o membership criador do tenant
    try:
        from app.model.professional import Professional
        from app.model.base import utc_now
        professional = Professional(
            tenant_id=tenant.id,
            membership_id=membership.id,
            name=membership.name if membership.name else account.name,
            email=membership.email if membership.email else account.email,
            active=True,
        )
        session.add(professional)
        session.commit()
    except Exception as e:
        # Se falhar ao criar professional, logar mas não quebrar a criação do tenant
        session.rollback()
        pass  # Professional é opcional

    # Emitir token para o novo tenant
    token = _issue_token_for_membership(account=account, membership=membership)
    return TokenResponse(access_token=token)


@router.post("/switch-tenant-old", response_model=TokenResponse, tags=["Auth"])
def switch_tenant_old(
    body: SwitchTenantRequest,
    account: Account = Depends(get_current_account),
    current_membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
):
    """
    Emite um novo JWT do sistema para outro tenant (sem passar pelo Google novamente).
    """
    membership = _get_active_membership(session, account_id=account.id, tenant_id=body.tenant_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Acesso negado (membership ACTIVE não encontrado)")
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=current_membership.tenant_id,
            actor_account_id=account.id,
            membership_id=current_membership.id,
            event_type="tenant_switched",
            data={
                "from_tenant_id": current_membership.tenant_id,
                "to_tenant_id": body.tenant_id,
                "to_membership_id": membership.id,
            },
        ),
    )
    token = _issue_token_for_membership(account=account, membership=membership)
    return TokenResponse(access_token=token)
