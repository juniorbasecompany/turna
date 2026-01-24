from __future__ import annotations

from sqlmodel import Session, select

from app.model.tenant import Tenant


def get_tenant_by_id(session: Session, tenant_id: int) -> Tenant | None:
    return session.exec(select(Tenant).where(Tenant.id == int(tenant_id))).first()


def create_tenant(
    session: Session,
    *,
    name: str,
    slug: str,
    timezone: str = "America/Sao_Paulo",
    locale: str = "pt-BR",
    currency: str = "BRL",
) -> Tenant:
    tenant = Tenant(name=name, slug=slug, timezone=timezone, locale=locale, currency=currency)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant

