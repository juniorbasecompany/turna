from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.tenant import Tenant
from pydantic import BaseModel as PydanticBaseModel


router = APIRouter()


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


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/tenants", response_model=TenantResponse, status_code=201)
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
