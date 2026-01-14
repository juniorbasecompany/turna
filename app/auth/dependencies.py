from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select
from app.db.session import get_session
from app.model.user import Account
from app.model.tenant import Tenant
from app.auth.jwt import verify_token

bearer = HTTPBearer(auto_error=False)


def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(get_session),
) -> Account:
    """
    Dependency que retorna a conta autenticada a partir do JWT.

    Raises:
        HTTPException: Se não houver token ou se a conta não existir
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    # Extrai account_id do payload
    account_id = int(payload.get("sub"))

    # Busca conta no banco
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found"
        )

    return account


def get_current_tenant(
    account: Account = Depends(get_current_account),
    session: Session = Depends(get_session),
) -> Tenant:
    """
    Dependency que retorna o tenant da conta autenticada.

    Raises:
        HTTPException: Se o tenant não existir
    """
    tenant = session.get(Tenant, account.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    return tenant


def require_role(required_role: str):
    """
    Dependency factory para verificar se o usuário tem uma role específica.

    Args:
        required_role: Role necessária (ex: "admin")

    Returns:
        Dependency function
    """
    def role_checker(account: Account = Depends(get_current_account)) -> Account:
        if account.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {required_role}"
            )
        return account

    return role_checker
