from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.tenant import Tenant
from pydantic import BaseModel as PydanticBaseModel
from app.api.auth import router as auth_router
from app.auth.dependencies import get_current_user
from app.models.user import User


router = APIRouter()  # Sem tag padrão - cada endpoint define sua própria tag
router.include_router(auth_router)


@router.get("/me", tags=["Auth"])
def get_me(user: User = Depends(get_current_user)):
    """
    Retorna os dados do usuário autenticado.
    Endpoint na raiz conforme checklist.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "auth_provider": user.auth_provider,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
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
