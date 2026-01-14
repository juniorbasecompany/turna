import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router

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

# Serve arquivos estáticos (para login.html)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Endpoint /login deve vir depois do mount para ter prioridade
# Tag "Interface" para diferenciar visualmente no Swagger
@app.get("/login", response_class=HTMLResponse, tags=["Interface"])
def login_page():
    """Página de login para testar autenticação Google (retorna HTML, não JSON)."""
    return HTMLResponse(content="<h1>Login page not found</h1>", status_code=404)
