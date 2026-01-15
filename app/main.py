import os
from pathlib import Path
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.route import router

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(".env")
except Exception:
    pass

app = FastAPI(
    title="Turna API",
    description="API para gerenciamento de escalas médicas",
    version="1.0.0"
)
app.include_router(router)


def _error_payload(*, code: str, message: str, details: object | None = None) -> dict:
    payload: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Normaliza erros HTTP do FastAPI/Starlette para um payload consistente.
    # Não expõe exceções internas nem detalhes sensíveis por padrão.
    code = f"HTTP_{exc.status_code}"
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content=_error_payload(code=code, message=message))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Normaliza erros de validação (422) para payload consistente.
    return JSONResponse(
        status_code=422,
        content=_error_payload(code="VALIDATION_ERROR", message="Invalid request", details=exc.errors()),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Fallback: evita vazar stacktrace/detalhes no response.
    return JSONResponse(
        status_code=500,
        content=_error_payload(code="INTERNAL_ERROR", message="Internal server error"),
    )


# Serve arquivos estáticos (para login.html)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Endpoint /login deve vir depois do mount para ter prioridade
# Tag "Interface" para diferenciar visualmente no Swagger
@app.get("/login", response_class=HTMLResponse, tags=["Interface"])
def login_page():
    """Página de login para testar autenticação Google (retorna HTML, não JSON)."""
    html_path = static_dir / "login.html"
    if html_path.exists():
        html_content = html_path.read_text(encoding="utf-8")
        # Substitui o placeholder pelo Client ID real (garante que frontend e backend usam o mesmo)
        google_client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        if not google_client_id:
            return HTMLResponse(
                content="<h1>Erro: GOOGLE_CLIENT_ID não configurado no .env</h1>",
                status_code=500
            )
        html_content = html_content.replace("COLE_AQUI_SEU_GOOGLE_CLIENT_ID", google_client_id)
        return HTMLResponse(content=html_content)
    return HTMLResponse(content="<h1>Login page not found</h1>", status_code=404)
