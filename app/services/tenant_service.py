from __future__ import annotations

from sqlmodel import Session, select

from app.model.tenant import Tenant


def get_tenant_by_id(session: Session, tenant_id: int) -> Tenant | None:
    return session.exec(select(Tenant).where(Tenant.id == int(tenant_id))).first()


def create_tenant(session: Session, *, name: str, slug: str, timezone: str = "UTC") -> Tenant:
    tenant = Tenant(name=name, slug=slug, timezone=timezone)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant

