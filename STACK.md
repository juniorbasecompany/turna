# Fase 1 — Stack (decidida)

## Estrutura do repositório

- **Monorepo**: um único repositório `turna`.
- **Backend**: pasta `backend/` (API FastAPI, worker Arq, modelos, Alembic, demand, output, strategy). Docker usa `context: ./backend` e volume `./backend:/app`. Variáveis de ambiente em `backend/.env`; Docker Compose usa `env_file: backend/.env`.
- **Frontend**: pasta `frontend/` (Next.js). Variáveis em `frontend/.env.local`.
- **Orquestração**: `docker-compose.yml` na raiz; comandos Docker e Alembic executados a partir da raiz.

## Objetivo
MVP SaaS multi-tenant para clínicas gerarem escalas e relatórios (PDF), com acesso:
- **Web (admin)**: cadastros, importação, geração/publicação de escalas, relatórios.
- **Mobile (profissionais)**: consulta de escalas publicadas + interações simples.

## Tecnologias (sem alternativas)
### Backend
- **Python**
- **FastAPI** (API REST)
- **Pydantic v2** (validação/serialização)
- **Uvicorn** (ASGI server)

### Persistência
- **PostgreSQL** (banco principal)
- **SQLModel** (ORM)
- **Alembic** (migrações)

### Jobs assíncronos
- **Redis** (broker/cache)
- **Arq** (worker async de jobs)

### Otimização
- **Google OR-Tools (CP-SAT)** (solver para escala)

### IA (abstraída)
- **AI Provider Adapter** (interface interna para extração a partir de PDF/JPEG/PNG/XLSX/XLS/CSV)

### Arquivos
- **S3-compatible Object Storage** (arquivos importados + relatórios PDF)
- **MinIO** (dev/local)

### Frontend
- **Next.js (React)** (web admin)

### Mobile
- **React Native** (app profissionais)

### Autenticação
- **OAuth 2.0 (Google)** (login)
- **JWT** (sessão/claims: account_id, tenant_id)
  - **Campos mínimos**: `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`
  - **Dados do banco**: email, name, role são obtidos via endpoints (`/me`, `get_current_member()`)
  - **Privacidade**: Account é privado

### Email
- **Resend** (envio de emails transacionais)

### Infra (Fase 1)
- **Docker** + **Docker Compose**
- **VPS simples** para produção inicial (1 servidor)

## Formatos
- **Entrada**: PDF, JPEG, PNG, XLSX, XLS, CSV
- **Saída**: **PDF** (somente)

## Princípios de arquitetura (Fase 1)
1. **Requests HTTP nunca rodam solver/IA**: sempre criam **Job** e retornam `job_id`.
2. **ScheduleVersion**: cada geração cria uma versão imutável; publicação é um passo separado.
3. **Multi-tenant por `tenant_id`** em todas as tabelas (enforcement na camada de repositório/serviço no MVP).
4. **Storage fora do banco**: arquivos sempre em object storage; banco guarda apenas metadados/URLs.
