from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import Request

from app.auth.jwt import verify_token


async def tenant_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Any]],
):
    """
    Middleware de contexto (não-enforcement):

    - Se houver Authorization: Bearer <token>, decodifica via verify_token()
    - Coloca {account_id, tenant_id, role, membership_id} em request.state
    - NÃO consulta DB e NÃO bloqueia request em caso de token inválido
      (o enforcement real fica nas dependencies: get_current_membership()).
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return await call_next(request)

    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return await call_next(request)

    try:
        payload = verify_token(token)
    except Exception:
        # Não muda o comportamento de endpoints públicos (ex.: /health).
        return await call_next(request)

    account_id_raw = payload.get("sub")
    tenant_id_raw = payload.get("tenant_id")
    role = payload.get("role")
    membership_id_raw = payload.get("membership_id")

    try:
        if account_id_raw is not None:
            request.state.account_id = int(account_id_raw)
        if tenant_id_raw is not None:
            request.state.tenant_id = int(tenant_id_raw)
        if role is not None:
            request.state.role = str(role)
        if membership_id_raw is not None:
            request.state.membership_id = int(membership_id_raw)
    except Exception:
        # Se o token tiver formato inesperado, não setamos contexto.
        pass

    return await call_next(request)


def get_tenant_id(request: Request) -> int | None:
    """
    Helper leve para extrair tenant_id do contexto.
    Preferir enforcement via get_current_membership().
    """
    v = getattr(request.state, "tenant_id", None)
    return int(v) if v is not None else None

