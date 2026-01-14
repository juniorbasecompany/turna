from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.tenant import Tenant
from pydantic import BaseModel as PydanticBaseModel
from app.api.auth import router as auth_router
from app.auth.dependencies import get_current_account
from app.models.user import Account


router = APIRouter()  # Sem tag padrão - cada endpoint define sua própria tag
router.include_router(auth_router)


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
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "updated_at": account.updated_at.isoformat() if account.updated_at else None,
    }


class TenantCreate(PydanticBaseModel):
    name: str
    slug: str


class TenantResponse(PydanticBaseModel):
    id: int
    name: str
    slug: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/health", tags=["System"])
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/tenants", response_model=TenantResponse, status_code=201, tags=["Tenants"])
def create_tenant(tenant_data: TenantCreate, session: Session = Depends(get_session)):
    """Cria um novo tenant."""
    # Verifica se já existe um tenant com o mesmo slug
    existing = session.exec(select(Tenant).where(Tenant.slug == tenant_data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant com este slug já existe")

    tenant = Tenant(name=tenant_data.name, slug=tenant_data.slug)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    return tenant
