import os
from pathlib import Path
from typing import Dict
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Carrega variáveis de ambiente do .env (backend/ ou raiz do repo)
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(project_root.parent / ".env")
    load_dotenv(project_root / ".env")
    load_dotenv(".env")
except Exception:
    pass

# Configuração Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_OAUTH_CLIENT_ID")


def verify_google_token(token: str) -> Dict[str, str]:
    """
    Verifica o token do Google e retorna as informações do usuário.

    Args:
        token: Token ID do Google OAuth

    Returns:
        Dict com email, name e hd (hosted domain)

    Raises:
        HTTPException: Se o token for inválido
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID not configured"
        )

    try:
        # clock_skew_in_seconds permite tolerar diferenças de relógio entre servidor e Google
        # Padrão: 60 segundos (suficiente para pequenas dessincronias)
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60
        )
    except ValueError as e:
        error_msg = str(e)
        if "Token's audience" in error_msg or "Wrong audience" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Token audience mismatch. Verifique se o GOOGLE_CLIENT_ID no .env corresponde ao Client ID usado no frontend."
            )
        # Não expõe detalhes do erro do provider para evitar leakage e inconsistências.
        raise HTTPException(status_code=401, detail="Invalid Google ID token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Google ID token")

    email = str(idinfo.get("email", "")).lower()
    name = str(idinfo.get("name", ""))

    if not email:
        raise HTTPException(status_code=401, detail="Google token missing email")

    return {
        "email": email,
        "name": name,
        "hd": idinfo.get("hd"),  # Hosted domain (para Google Workspace)
    }
