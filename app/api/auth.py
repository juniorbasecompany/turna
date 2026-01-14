import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db.session import get_session
from app.model.user import Account
from app.model.tenant import Tenant
from app.auth.jwt import create_access_token
from app.auth.oauth import verify_google_token

router = APIRouter(prefix="/auth", tags=["Auth"])

# Configuração de admin (opcional)
ADMIN_EMAILS_RAW = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAILS: set[str] = {e.strip().lower() for e in ADMIN_EMAILS_RAW.split(",") if e.strip()}
ADMIN_HOSTED_DOMAIN = os.getenv("ADMIN_HOSTED_DOMAIN")


class GoogleTokenRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DevTokenRequest(BaseModel):
    email: str
    name: str = "Dev User"



def _determine_role(email: str, hd: Optional[str] = None) -> str:
    """Determina a role do usuário baseado em email e hosted domain."""
    email_lower = email.lower()

    if ADMIN_EMAILS and email_lower in ADMIN_EMAILS:
        return "admin"

    if ADMIN_HOSTED_DOMAIN and hd == ADMIN_HOSTED_DOMAIN:
        return "admin"

    return "user"


def _get_or_create_default_tenant(session: Session) -> Tenant:
    """Obtém ou cria um tenant padrão para novos usuários."""
    # Por enquanto, cria um tenant padrão se não existir
    # Em produção, isso deve ser configurado ou o usuário deve escolher durante registro
    default_tenant = session.exec(
        select(Tenant).where(Tenant.slug == "default")
    ).first()

    if not default_tenant:
        default_tenant = Tenant(name="Default Tenant", slug="default")
        session.add(default_tenant)
        session.commit()
        session.refresh(default_tenant)

    return default_tenant


@router.post("/google", response_model=TokenResponse)
def auth_google(
    body: GoogleTokenRequest,
    session: Session = Depends(get_session),
):
    """
    Login com Google - apenas autentica se o usuário já existe.

    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do sistema>", "token_type": "bearer"}
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]
    name = idinfo["name"]

    # Busca conta no banco
    account = session.exec(
        select(Account).where(Account.email == email)
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado. Use a opção 'Cadastrar-se' para criar uma conta."
        )

    # Cria token JWT
    token = create_access_token(
        account_id=account.id,
        tenant_id=account.tenant_id,
        role=account.role,
        email=account.email,
        name=account.name,
    )

    return TokenResponse(access_token=token)


@router.post("/google/register", response_model=TokenResponse)
def auth_google_register(
    body: GoogleTokenRequest,
    session: Session = Depends(get_session),
):
    """
    Cadastro com Google - cria o usuário se não existir, ou autentica se já existe.

    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do sistema>", "token_type": "bearer"}
    """
    idinfo = verify_google_token(body.id_token)
    email = idinfo["email"]
    name = idinfo["name"]
    hd = idinfo.get("hd")

    # Verifica se o usuário já existe
    account = session.exec(
        select(Account).where(Account.email == email)
    ).first()

    if account:
        # Usuário já existe, apenas autentica
        role = account.role
    else:
        # Cria novo usuário
        role = _determine_role(email, hd)

        # Obtém ou cria tenant padrão
        tenant = _get_or_create_default_tenant(session)

        # Cria conta no banco
        account = Account(
            email=email,
            name=name,
            role=role,
            tenant_id=tenant.id,
            auth_provider="google",
        )
        session.add(account)
        session.commit()
        session.refresh(account)

    # Cria token JWT
    token = create_access_token(
        account_id=account.id,
        tenant_id=account.tenant_id,
        role=account.role,
        email=account.email,
        name=account.name,
    )

    return TokenResponse(access_token=token)


@router.post("/dev/token", response_model=TokenResponse, tags=["Auth"])
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
            tenant_id=tenant.id,
            auth_provider="dev",
        )
        session.add(account)
        session.commit()
        session.refresh(account)

    token = create_access_token(
        account_id=account.id,
        tenant_id=account.tenant_id,
        role=account.role,
        email=account.email,
        name=account.name,
    )
    return TokenResponse(access_token=token)
