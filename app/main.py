import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.route import router
from app.middleware.tenant import tenant_context_middleware

logger = logging.getLogger(__name__)

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

# Configuração CORS
# Permite requisições do frontend (localhost:3000 e localhost:3001)
# Pode ser configurado via variável de ambiente CORS_ORIGINS (separado por vírgula)
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _tenant_context(request: Request, call_next):
    return await tenant_context_middleware(request, call_next)


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
    # Loga o erro completo para debug
    logger.error(f"Erro não tratado: {exc}", exc_info=True)

    # Extrai mensagem do erro de forma segura
    error_message = str(exc) if exc else "Internal server error"

    # Limita o tamanho da mensagem para evitar expor informações sensíveis
    # e manter a resposta em tamanho razoável
    max_message_length = 500
    if len(error_message) > max_message_length:
        error_message = error_message[:max_message_length] + "..."

    # Retorna a mensagem do erro para ajudar no debug, mas sem stacktrace
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            code="INTERNAL_ERROR",
            message=error_message
        ),
    )


# Serve arquivos estáticos (para login.html)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Endpoint /loginbackend deve vir depois do mount para ter prioridade
# Tag "Interface" para diferenciar visualmente no Swagger
@app.get("/loginbackend", response_class=HTMLResponse, tags=["Interface"])
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
