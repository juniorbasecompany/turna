import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Set, Dict, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import jwt, JWTError

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# -----------------------------
# Env loading (robusto)
# -----------------------------
try:
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parent
    # 1) Preferir sempre o .env na raiz do projeto (robusto mesmo se CWD mudar)
    load_dotenv(project_root / ".env")
    # 2) Também tenta .env no diretório atual (útil em execuções ad-hoc)
    load_dotenv(".env")
except Exception:
    pass

APP_JWT_ALG = "HS256"

def _env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing env var: {name}")
    return val

GOOGLE_CLIENT_ID = _env("GOOGLE_CLIENT_ID")  # pegue do Console
APP_JWT_SECRET = _env("APP_JWT_SECRET")      # segredo do seu sistema (forte!)
ADMIN_EMAILS_RAW = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAILS: Set[str] = {e.strip().lower() for e in ADMIN_EMAILS_RAW.split(",") if e.strip()}

# Opcional: restringir a domínio Workspace via hd claim:
ADMIN_HOSTED_DOMAIN = os.getenv("ADMIN_HOSTED_DOMAIN")  # ex: "suaempresa.com"

# Caminho do arquivo de usuários
USERS_FILE = project_root / "data" / "users.json"
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Sistema de Autenticação (Login e Cadastro)")

# Serve a página simples de login
app.mount("/static", StaticFiles(directory="static"), name="static")

bearer = HTTPBearer(auto_error=False)

# -----------------------------
# Gerenciamento de usuários
# -----------------------------

def load_users() -> List[Dict]:
    """Carrega usuários do arquivo JSON"""
    if not USERS_FILE.exists():
        return []
    try:
        with USERS_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_users(users: List[Dict]) -> None:
    """Salva usuários no arquivo JSON"""
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def find_user_by_email(email: str) -> Optional[Dict]:
    """Busca um usuário pelo email"""
    users = load_users()
    email_lower = email.lower()
    for user in users:
        if user.get("email", "").lower() == email_lower:
            return user
    return None

# -----------------------------
# JWT
# -----------------------------

def issue_app_jwt(email: str, name: str, role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "name": name,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
        "iss": "your-app",
        "aud": "your-app-web",
    }
    return jwt.encode(payload, APP_JWT_SECRET, algorithm=APP_JWT_ALG)

def verify_app_jwt(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")
    token = creds.credentials
    try:
        payload = jwt.decode(
            token,
            APP_JWT_SECRET,
            algorithms=[APP_JWT_ALG],
            audience="your-app-web",
            issuer="your-app",
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = Path(__file__).resolve().parent / "static" / "login.html"
    html_content = html_path.read_text(encoding="utf-8")
    # Substitui o placeholder pelo Client ID real (garante que frontend e backend usam o mesmo)
    html_content = html_content.replace("COLE_AQUI_SEU_GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    return HTMLResponse(content=html_content)


def _verify_google_token(token: str) -> dict:
    """Verifica o token do Google e retorna as informações do usuário"""
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        error_msg = str(e)
        if "Token's audience" in error_msg or "Wrong audience" in error_msg:
            raise HTTPException(
                status_code=401,
                detail=f"Token audience mismatch. Verifique se o GOOGLE_CLIENT_ID no .env corresponde ao Client ID usado no HTML."
            )
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {type(e).__name__}: {str(e)}")

    email = str(idinfo.get("email", "")).lower()
    name = str(idinfo.get("name", ""))

    if not email:
        raise HTTPException(status_code=401, detail="Google token missing email")

    return {"email": email, "name": name, "hd": idinfo.get("hd")}

@app.post("/auth/google")
def auth_google(body: dict):
    """
    Login com Google - apenas autentica se o usuário já existe
    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do seu sistema>"}
    """
    token = body.get("id_token")
    if not token:
        raise HTTPException(status_code=400, detail="id_token is required")

    idinfo = _verify_google_token(token)
    email = idinfo["email"]
    name = idinfo["name"]

    # Verifica se o usuário existe
    user = find_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado. Use a opção 'Cadastrar-se' para criar uma conta.")

    # Determina role
    role = user.get("role", "user")
    
    # Verifica permissões de admin (se necessário)
    if ADMIN_EMAILS and email not in ADMIN_EMAILS:
        if ADMIN_HOSTED_DOMAIN:
            hd = idinfo.get("hd")
            if hd != ADMIN_HOSTED_DOMAIN:
                raise HTTPException(status_code=403, detail="Not an admin")
        elif role != "admin":
            raise HTTPException(status_code=403, detail="Not an admin")

    app_token = issue_app_jwt(email=email, name=name, role=role)
    return {"access_token": app_token, "token_type": "bearer"}

@app.post("/auth/google/register")
def auth_google_register(body: dict):
    """
    Cadastro com Google - cria o usuário se não existir, ou autentica se já existe
    Recebe: {"id_token": "<JWT do Google>"}
    Retorna: {"access_token": "<JWT do seu sistema>"}
    """
    token = body.get("id_token")
    if not token:
        raise HTTPException(status_code=400, detail="id_token is required")

    idinfo = _verify_google_token(token)
    email = idinfo["email"]
    name = idinfo["name"]
    hd = idinfo.get("hd")

    # Verifica se o usuário já existe
    user = find_user_by_email(email)
    
    if user:
        # Usuário já existe, apenas autentica
        role = user.get("role", "user")
    else:
        # Cria novo usuário
        # Determina role: admin se estiver na lista de admins, senão user
        is_admin = False
        if ADMIN_EMAILS and email in ADMIN_EMAILS:
            is_admin = True
        elif ADMIN_HOSTED_DOMAIN and hd == ADMIN_HOSTED_DOMAIN:
            is_admin = True

        role = "admin" if is_admin else "user"

        new_user = {
            "name": name,
            "email": email,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "auth_provider": "google"
        }

        users = load_users()
        users.append(new_user)
        save_users(users)

    # Verifica permissões de admin (se necessário)
    if ADMIN_EMAILS and email not in ADMIN_EMAILS:
        if ADMIN_HOSTED_DOMAIN:
            if hd != ADMIN_HOSTED_DOMAIN:
                raise HTTPException(status_code=403, detail="Not an admin")
        elif role != "admin":
            raise HTTPException(status_code=403, detail="Not an admin")

    app_token = issue_app_jwt(email=email, name=name, role=role)
    return {"access_token": app_token, "token_type": "bearer"}

@app.get("/me")
def me(user=Depends(verify_app_jwt)):
    return {"user": user}

@app.get("/admin/ping")
def admin_ping(user=Depends(verify_app_jwt)):
    return {"ok": True, "email": user["sub"], "role": user.get("role")}
