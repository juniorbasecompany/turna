from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlmodel import Session, select

from app.db.session import get_session
from app.model.membership import Membership, MembershipStatus
from app.model.account import Account
from app.model.tenant import Tenant
from app.auth.jwt import verify_token

bearer = HTTPBearer(auto_error=False)


def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


def get_current_account(
    payload: dict[str, Any] = Depends(get_token_payload),
    session: Session = Depends(get_session),
) -> Account:
    """Dependency que retorna a conta autenticada a partir do JWT."""
    account_id_raw = payload.get("sub")
    if not account_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    account_id = int(account_id_raw)

    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found")
    return account


def get_current_membership(
    payload: dict[str, Any] = Depends(get_token_payload),
    session: Session = Depends(get_session),
) -> Membership:
    """
    Dependency que valida o acesso do account ao tenant do JWT via Membership.

    Raises:
        HTTPException: Se não existir membership ACTIVE para (account_id, tenant_id)
    """
    account_id_raw = payload.get("sub")
    tenant_id_raw = payload.get("tenant_id")
    if not account_id_raw or not tenant_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    account_id = int(account_id_raw)
    tenant_id = int(tenant_id_raw)

    membership = session.exec(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado (membership ACTIVE não encontrado)",
        )
    return membership


def get_current_tenant(
    membership: Membership = Depends(get_current_membership),
    session: Session = Depends(get_session),
) -> Tenant:
    tenant = session.get(Tenant, membership.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


def require_role(required_role: str):
    """
    Dependency factory para verificar se a conta tem uma role específica.

    Args:
        required_role: Role necessária (ex: "admin")

    Returns:
        Dependency function
    """
    def role_checker(membership: Membership = Depends(get_current_membership)) -> Membership:
        if membership.role.value != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {required_role}"
            )
        return membership

    return role_checker
