import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from jose import jwt, JWTError
from fastapi import HTTPException

# Carrega variáveis de ambiente do .env (garante que está carregado antes de usar)
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(".env")
except Exception:
    pass

# Configuração JWT
# Aceita JWT_SECRET ou APP_JWT_SECRET (compatibilidade com login.py)
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("APP_JWT_SECRET") or "CHANGE_ME"
JWT_ISSUER = os.getenv("JWT_ISSUER") or os.getenv("APP_JWT_ISSUER", "turna")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8


def create_access_token(user_id: int, tenant_id: int, role: str, email: str, name: str) -> str:
    """
    Cria um token JWT com as informações do usuário.

    Args:
        user_id: ID do usuário no banco
        tenant_id: ID do tenant do usuário
        role: Role do usuário (user, admin)
        email: Email do usuário
        name: Nome do usuário

    Returns:
        Token JWT codificado
    """
    now = datetime.now(timezone.utc)
    payload: Dict[str, any] = {
        "sub": str(user_id),  # Subject (user_id)
        "email": email,
        "name": name,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRATION_HOURS)).timestamp()),
        "iss": JWT_ISSUER,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Dict[str, any]:
    """
    Verifica e decodifica um token JWT.

    Args:
        token: Token JWT a ser verificado

    Returns:
        Payload do token decodificado

    Raises:
        HTTPException: Se o token for inválido ou expirado
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
