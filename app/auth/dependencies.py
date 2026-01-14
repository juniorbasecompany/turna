from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.user import User
from app.models.tenant import Tenant
from app.auth.jwt import verify_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    """
    Dependency que retorna o usuário autenticado a partir do JWT.
    
    Raises:
        HTTPException: Se não houver token ou se o usuário não existir
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extrai user_id do payload
    user_id = int(payload.get("sub"))
    
    # Busca usuário no banco
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def get_current_tenant(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Tenant:
    """
    Dependency que retorna o tenant do usuário autenticado.
    
    Raises:
        HTTPException: Se o tenant não existir
    """
    tenant = session.get(Tenant, user.tenant_id)
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
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {required_role}"
            )
        return user
    
    return role_checker
