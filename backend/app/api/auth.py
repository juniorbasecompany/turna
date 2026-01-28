import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db.session import get_session
from app.model.member import Member, MemberRole, MemberStatus
from app.model.audit_log import AuditLog
from app.model.account import Account
from app.model.tenant import Tenant
from app.services.hospital_service import create_default_hospital_for_tenant
from app.auth.jwt import create_access_token
from app.auth.oauth import verify_google_token
from app.auth.dependencies import get_current_account, get_current_member
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
    member_id: int
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
        select(Tenant, Member)
        .join(Member, Member.tenant_id == Tenant.id)
        .where(
            Member.account_id == account_id,
            Member.status == MemberStatus.ACTIVE,
        )
        .order_by(Tenant.id.asc())
    ).all()

    opts: list[TenantOption] = []
    for tenant, member in rows:
        opts.append(
            TenantOption(
                tenant_id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                role=member.role.value,
            )
        )
    return opts


def _list_pending_invites_for_account(session: Session, *, account_id: int, email: str | None = None) -> list[InviteOption]:
    # Buscar invites por account_id OU por email (quando account_id é NULL)
    query = (
        select(Tenant, Member)
        .join(Member, Member.tenant_id == Tenant.id)
        .where(Member.status == MemberStatus.PENDING)
    )

    if email:
        # Buscar por account_id OU por email (para members pendentes sem Account)
        query = query.where(
            (Member.account_id == account_id) |
            ((Member.account_id.is_(None)) & (Member.email == email.lower()))
        )
    else:
        # Apenas por account_id
        query = query.where(Member.account_id == account_id)

    rows = session.exec(query.order_by(Tenant.id.asc())).all()

    invites: list[InviteOption] = []
    for tenant, member in rows:
        invites.append(
            InviteOption(
                member_id=member.id,
                tenant_id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                role=member.role.value,
                status=member.status.value,
            )
        )
    return invites


def get_account_members(session: Session, *, account_id: int, email: str | None = None) -> tuple[list[TenantOption], list[InviteOption]]:
    """
    Retorna (ACTIVE tenants, PENDING invites) para a conta.

    Args:
        account_id: ID do Account
        email: Email do Account (opcional, usado para buscar invites pendentes sem Account)
    """
    tenant_list = _list_active_tenants_for_account(session, account_id=account_id)
    invites = _list_pending_invites_for_account(session, account_id=account_id, email=email)
    return tenant_list, invites


def get_active_tenant_for_account(session: Session, *, account_id: int) -> int | None:
    """
    Seleção automática de tenant:
      - 0 ACTIVE: None
      - 1 ACTIVE: tenant_id
      - >1 ACTIVE: None (exige seleção)
    """
    tenant_list = _list_active_tenants_for_account(session, account_id=account_id)
    if len(tenant_list) == 1:
        return tenant_list[0].tenant_id
    return None


def _get_active_member(
    session: Session, *, account_id: int, tenant_id: int
) -> Member | None:
    return session.exec(
        select(Member).where(
            Member.account_id == account_id,
            Member.tenant_id == tenant_id,
            Member.status == MemberStatus.ACTIVE,
        )
    ).first()


def _issue_token_for_member(*, account: Account, member: Member) -> str:
    return create_access_token(
        account_id=account.id,
        tenant_id=member.tenant_id,
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

    # Buscar e vincular Members PENDING com account_id NULL pelo email
    pending_members = session.exec(
        select(Member).where(
            Member.email == email.lower(),
            Member.account_id.is_(None),
            Member.status == MemberStatus.PENDING,
        )
    ).all()

    for pending_member in pending_members:
        # Vincular Account ao Member
        pending_member.account_id = account.id
        # Preencher member.name se NULL
        if (pending_member.name is None or pending_member.name == "") and account.name and account.name != "":
            pending_member.name = account.name
        session.add(pending_member)

    if pending_members:
        session.commit()

    tenant_list, invites = get_account_members(session, account_id=account.id)

    # Se não há tenants ACTIVE nem invites PENDING, exige seleção (permite criar clínica)
    if len(tenant_list) == 0 and len(invites) == 0:
        return AuthResponse(requires_tenant_selection=True, tenants=[], invites=[])

    # Se não há tenants ACTIVE mas há invites, exige seleção
    if len(tenant_list) == 0:
        return AuthResponse(requires_tenant_selection=True, tenants=[], invites=invites)

    # Se há múltiplos tenants ACTIVE ou convites PENDING, exige seleção
    if len(tenant_list) > 1 or len(invites) > 0:
        return AuthResponse(requires_tenant_selection=True, tenants=tenant_list, invites=invites)

    # Único tenant ativo e sem convites -> emite token direto.
    only = tenant_list[0]
    member = _get_active_member(session, account_id=account.id, tenant_id=only.tenant_id)
    if not member:
        raise HTTPException(status_code=403, detail="Member ACTIVE não encontrado para o tenant selecionado")

    # Preencher member.name se NULL (usar account.name atualizado)
    if (member.name is None or member.name == "") and account.name and account.name != "":
        member.name = account.name
        session.add(member)
        session.commit()
        session.refresh(member)

    token = _issue_token_for_member(account=account, member=member)
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
        # Cria novo account (Account não possui tenant_id; o vínculo é via Member)
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

        member = Member(
            tenant_id=tenant.id,
            account_id=account.id,
            role=MemberRole.ADMIN if role == "admin" else MemberRole.ACCOUNT,
            status=MemberStatus.ACTIVE,
            name=name,  # Preencher member.name com nome do Google na criação
        )
        session.add(member)
        session.commit()
        session.refresh(member)

        token = _issue_token_for_member(account=account, member=member)
        return AuthResponse(access_token=token)

    # Account já existe -> comportamento igual ao login (pode exigir seleção).
    # Também buscar e vincular Members PENDING
    pending_members = session.exec(
        select(Member).where(
            Member.email == email.lower(),
            Member.account_id.is_(None),
            Member.status == MemberStatus.PENDING,
        )
    ).all()

    for pending_member in pending_members:
        pending_member.account_id = account.id
        if (pending_member.name is None or pending_member.name == "") and account.name and account.name != "":
            pending_member.name = account.name
        session.add(pending_member)

    if pending_members:
        session.commit()

    return auth_google(body=body, session=session)


@router.post("/google/select-tenant", response_model=TokenResponse)
def auth_google_select_tenant(
    body: GoogleSelectTenantRequest,
    session: Session = Depends(get_session),
):
    """
    Quando a conta tem múltiplos tenants ACTIVE, este endpoint emite o JWT do sistema
    para o tenant escolhido, validando via Google ID token + Member.

    Permite também gerar token para aceitar convites (member PENDING) quando
    o usuário não tem nenhum tenant ativo.
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]

    account = session.exec(select(Account).where(Account.email == email)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Primeiro, tentar buscar member ACTIVE
    member = _get_active_member(session, account_id=account.id, tenant_id=body.tenant_id)

    # Se não encontrar ACTIVE, verificar se há member PENDING (para aceitar convites)
    # Buscar por account_id OU por email (quando account_id é NULL)
    if not member:
        member_pending = session.exec(
            select(Member).where(
                (Member.account_id == account.id) |
                ((Member.account_id.is_(None)) & (Member.email == email.lower())),
                Member.tenant_id == body.tenant_id,
                Member.status == MemberStatus.PENDING,
            )
        ).first()

        if member_pending:
            # Se member tem account_id NULL, vincular ao Account
            if member_pending.account_id is None:
                member_pending.account_id = account.id
                if (member_pending.name is None or member_pending.name == "") and account.name and account.name != "":
                    member_pending.name = account.name
                # Preencher member.email se NULL (sincronizar uma vez com account.email)
                if member_pending.email is None or member_pending.email == "":
                    if account.email:
                        member_pending.email = account.email.lower()
                session.add(member_pending)
                session.commit()
                session.refresh(member_pending)

            # Permitir gerar token temporário para aceitar convite
            # O token será usado apenas para aceitar o convite, não para acessar o tenant
            token = create_access_token(
                account_id=account.id,
                tenant_id=body.tenant_id,
            )
            return TokenResponse(access_token=token)
        else:
            raise HTTPException(status_code=403, detail="Acesso negado (member ACTIVE ou PENDING não encontrado)")

    token = _issue_token_for_member(account=account, member=member)
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

        member = Member(
            tenant_id=tenant.id,
            account_id=account.id,
            role=MemberRole.ADMIN if role == "admin" else MemberRole.ACCOUNT,
            status=MemberStatus.ACTIVE,
        )
        session.add(member)
        session.commit()

    # Se tenant_id foi informado, emite token para ele (valida member).
    if body.tenant_id is not None:
        member = _get_active_member(session, account_id=account.id, tenant_id=body.tenant_id)
        if not member:
            raise HTTPException(status_code=403, detail="Acesso negado (member ACTIVE não encontrado)")
        token = _issue_token_for_member(account=account, member=member)
        return AuthResponse(access_token=token)

    tenant_list, invites = get_account_members(session, account_id=account.id, email=account.email)
    if not tenant_list:
        raise HTTPException(status_code=403, detail="Conta sem acesso a nenhum tenant (member ACTIVE ausente)")
    if len(tenant_list) > 1:
        return AuthResponse(requires_tenant_selection=True, tenants=tenant_list)

    only = tenant_list[0]
    member = _get_active_member(session, account_id=account.id, tenant_id=only.tenant_id)
    if not member:
        raise HTTPException(status_code=403, detail="Member ACTIVE não encontrado para o tenant selecionado")
    token = _issue_token_for_member(account=account, member=member)
    return AuthResponse(access_token=token)


@router.get("/tenant/list", response_model=TenantListResponse, tags=["Auth"])
def list_my_tenants(
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """Lista tenants ACTIVE disponíveis e convites PENDING para a conta autenticada."""
    tenant_list, invites = get_account_members(session, account_id=account.id, email=account.email)
    return TenantListResponse(tenants=tenant_list, invites=invites)


@router.get("/invites", response_model=list[InviteOption], tags=["Auth"])
def list_my_invites(
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """Lista convites PENDING da conta autenticada."""
    return _list_pending_invites_for_account(session, account_id=account.id)


class InviteActionResponse(BaseModel):
    member_id: int
    tenant_id: int
    status: str


@router.post("/invites/{member_id}/accept", response_model=InviteActionResponse, tags=["Auth"])
def accept_invite(
    member_id: int,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    """
    Aceita um convite (member PENDING) e o torna ACTIVE.

    Requer autenticação do account (via token JWT), mas não requer member ACTIVE.
    Isso permite aceitar o primeiro convite mesmo sem ter nenhum tenant ativo.

    Se member.account_id for NULL, vincula o Account ao Member pelo email.
    """
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Verificar se o convite pertence ao account autenticado
    # Se account_id é NULL, verificar pelo email
    if member.account_id is not None:
        if member.account_id != account.id:
            raise HTTPException(status_code=403, detail="Acesso negado")
    else:
        # Member pendente sem Account - verificar pelo email
        if member.email != account.email.lower():
            raise HTTPException(status_code=403, detail="Acesso negado (email não corresponde)")
        # Vincular Account ao Member
        member.account_id = account.id

    if member.status != MemberStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invite is not PENDING")

    prev_status = member.status
    member.status = MemberStatus.ACTIVE
    member.updated_at = utc_now()

    # Preencher member.name se NULL (usar account.name do Google)
    if member.name is None or member.name == "":
        if account.name and account.name != "":
            member.name = account.name

    # Preencher member.email se NULL (sincronizar uma vez com account.email)
    if member.email is None or member.email == "":
        if account.email:
            member.email = account.email.lower()

    session.add(member)
    session.commit()
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=member.tenant_id,
            actor_account_id=account.id,
            member_id=member.id,
            event_type="member_status_changed",
            data={
                "from_status": prev_status.value,
                "to_status": member.status.value,
            },
        ),
    )
    return InviteActionResponse(
        member_id=member.id,
        tenant_id=member.tenant_id,
        status=member.status.value,
    )


@router.post("/invites/{member_id}/reject", response_model=InviteActionResponse, tags=["Auth"])
def reject_invite(
    member_id: int,
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Invite not found")
    if member.account_id != account.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if member.status != MemberStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invite is not PENDING")

    prev_status = member.status
    member.status = MemberStatus.REJECTED
    member.updated_at = utc_now()
    session.add(member)
    session.commit()
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=member.tenant_id,
            actor_account_id=account.id,
            member_id=member.id,
            event_type="member_status_changed",
            data={
                "from_status": prev_status.value,
                "to_status": member.status.value,
            },
        ),
    )
    return InviteActionResponse(
        member_id=member.id,
        tenant_id=member.tenant_id,
        status=member.status.value,
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

    Permite também gerar token para aceitar convites (member PENDING) quando
    o usuário não tem nenhum tenant ativo.
    """
    # Tentar obter member ACTIVE primeiro
    member = _get_active_member(session, account_id=account.id, tenant_id=body.tenant_id)

    # Se não encontrar ACTIVE, verificar se há member PENDING (para aceitar convites)
    # Buscar por account_id OU por email (quando account_id é NULL)
    if not member:
        member_pending = session.exec(
            select(Member).where(
                (Member.account_id == account.id) |
                ((Member.account_id.is_(None)) & (Member.email == account.email.lower())),
                Member.tenant_id == body.tenant_id,
                Member.status == MemberStatus.PENDING,
            )
        ).first()

        if member_pending:
            # Se member tem account_id NULL, vincular ao Account
            if member_pending.account_id is None:
                member_pending.account_id = account.id
                if (member_pending.name is None or member_pending.name == "") and account.name and account.name != "":
                    member_pending.name = account.name
                # Preencher member.email se NULL (sincronizar uma vez com account.email)
                if member_pending.email is None or member_pending.email == "":
                    if account.email:
                        member_pending.email = account.email.lower()
                session.add(member_pending)
                session.commit()
                session.refresh(member_pending)

            # Permitir gerar token temporário para aceitar convite
            # O token será usado apenas para aceitar o convite, não para acessar o tenant
            token = create_access_token(
                account_id=account.id,
                tenant_id=body.tenant_id,
            )
            return TokenResponse(access_token=token)
        else:
            raise HTTPException(status_code=403, detail="Acesso negado (member ACTIVE ou PENDING não encontrado)")

    # Se encontrou member ACTIVE, tentar obter current_member para log de auditoria
    # Mas não falhar se não houver (permite aceitar primeiro convite)
    try:
        from app.auth.dependencies import get_token_payload
        from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
        bearer = HTTPBearer(auto_error=False)
        # Tentar obter token do header
        # Como já temos account autenticado, podemos tentar buscar member atual do token
        # Mas isso é opcional - se não houver, apenas não fazemos log de auditoria
        pass  # Simplificar: não fazer log de auditoria se não houver current_member
    except:
        pass  # Ignorar erro de auditoria se não houver current_member

    token = _issue_token_for_member(account=account, member=member)
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
    # Também buscar e vincular Members PENDING
    pending_members = session.exec(
        select(Member).where(
            Member.email == email.lower(),
            Member.account_id.is_(None),
            Member.status == MemberStatus.PENDING,
        )
    ).all()

    for pending_member in pending_members:
        pending_member.account_id = account.id
        if (pending_member.name is None or pending_member.name == "") and account.name and account.name != "":
            pending_member.name = account.name
        session.add(pending_member)

    if pending_members:
        session.commit()

    tenant_list, invites = get_account_members(session, account_id=account.id, email=email)
    if len(tenant_list) > 0:
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

    # Criar member ADMIN/ACTIVE para o criador
    member = Member(
        tenant_id=tenant.id,
        account_id=account.id,
        role=MemberRole.ADMIN,
        status=MemberStatus.ACTIVE,
        name=account.name if account.name else None,  # Preencher member.name com account.name
    )
    session.add(member)
    session.commit()
    session.refresh(member)


    # Emitir token para o novo tenant
    token = _issue_token_for_member(account=account, member=member)
    return TokenResponse(access_token=token)


@router.post("/switch-tenant-old", response_model=TokenResponse, tags=["Auth"])
def switch_tenant_old(
    body: SwitchTenantRequest,
    account: Account = Depends(get_current_account),
    current_member: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    """
    Emite um novo JWT do sistema para outro tenant (sem passar pelo Google novamente).
    """
    member = _get_active_member(session, account_id=account.id, tenant_id=body.tenant_id)
    if not member:
        raise HTTPException(status_code=403, detail="Acesso negado (member ACTIVE não encontrado)")
    _try_write_audit_log(
        session,
        AuditLog(
            tenant_id=current_member.tenant_id,
            actor_account_id=account.id,
            member_id=current_member.id,
            event_type="tenant_switched",
            data={
                "from_tenant_id": current_member.tenant_id,
                "to_tenant_id": body.tenant_id,
                "to_member_id": member.id,
            },
        ),
    )
    token = _issue_token_for_member(account=account, member=member)
    return TokenResponse(access_token=token)
