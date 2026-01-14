import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db.session import get_session
from app.models.user import User
from app.models.tenant import Tenant
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

    # Busca usuário no banco
    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado. Use a opção 'Cadastrar-se' para criar uma conta."
        )

    # Cria token JWT
    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
        name=user.name,
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
    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if user:
        # Usuário já existe, apenas autentica
        role = user.role
    else:
        # Cria novo usuário
        role = _determine_role(email, hd)

        # Obtém ou cria tenant padrão
        tenant = _get_or_create_default_tenant(session)

        # Cria usuário no banco
        user = User(
            email=email,
            name=name,
            role=role,
            tenant_id=tenant.id,
            auth_provider="google",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # Cria token JWT
    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
        name=user.name,
    )

    return TokenResponse(access_token=token)
