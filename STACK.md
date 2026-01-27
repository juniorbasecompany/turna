# Fase 1 — Stack (decidida)

## Estrutura do repositório

- **Monorepo**: um único repositório `turna`.
- **Backend**: pasta `backend/` (API FastAPI, worker Arq, modelos, Alembic, demand, output, strategy). Docker usa `context: ./backend` e volume `./backend:/app`. Variáveis de ambiente em `backend/.env`; Docker Compose usa `env_file: backend/.env`.
- **Frontend**: pasta `frontend/` (Next.js). Variáveis em `frontend/.env.local`.
- **Orquestração**: `docker-compose.yml` na raiz; comandos Docker e Alembic executados a partir da raiz.

## Objetivo
MVP SaaS multi-tenant para clínicas gerarem escalas e relatórios (PDF), com acesso:
- **Web (admin)**: cadastros, importação, geração/publicação de escalas, relatórios.
- **Mobile (profissionais)**: consulta de escalas publicadas + interações simples (futuro).

## Tecnologias (sem alternativas)

### Backend
- **Python 3.11+**
- **FastAPI** (API REST)
- **Pydantic v2** (validação/serialização)
- **Uvicorn** (ASGI server)

### Persistência
- **PostgreSQL 16** (banco principal)
- **SQLModel** (ORM)
- **Alembic** (migrações)

### Jobs assíncronos
- **Redis 7** (broker/cache)
- **Arq** (worker async de jobs)
  - Tipos de job: `PING`, `EXTRACT_DEMAND`, `GENERATE_SCHEDULE`, `GENERATE_THUMBNAIL`

### Otimização
- **Google OR-Tools (CP-SAT)** (solver para escala - futuro)
- **Solver Greedy** (implementado - alocação rápida)

### IA (abstraída)
- **OpenAI** (extração de demandas a partir de PDF/JPEG/PNG)
- **AI Provider Adapter** (interface interna para abstração futura)

### Arquivos
- **S3-compatible Object Storage** (arquivos importados + relatórios PDF)
- **MinIO** (dev/local)
- **Pillow** (geração de thumbnails)

### Geração de PDF
- **ReportLab** (renderização de escalas em PDF)
- **pypdfium2**, **pdfplumber**, **PyMuPDF** (leitura de PDFs)

### Frontend
- **Next.js 14 (App Router)** (web admin)
- **React 18** + **TypeScript**
- **Tailwind CSS** (estilização)

### Mobile (futuro)
- **React Native** (app profissionais)

### Autenticação
- **OAuth 2.0 (Google)** (login)
- **JWT** (sessão/claims: account_id, tenant_id)
  - **Campos mínimos**: `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`
  - **Dados do banco**: email, name, role são obtidos via endpoints (`/me`, `get_current_member()`)
  - **Privacidade**: Account é privado

### Email
- **Resend** (envio de emails transacionais - convites)

### Infra (Fase 1)
- **Docker** + **Docker Compose**
- **VPS simples** para produção inicial (1 servidor)

## Modelos de Dados

### Entidades principais
- **Tenant**: clínica (entidade organizacional)
- **Account**: pessoa física (login Google, email único global, sem tenant_id)
- **Member**: vínculo Account↔Tenant com role e status
- **Hospital**: hospital por tenant (com prompt customizável para extração IA)
- **File**: metadados de arquivos no S3/MinIO
- **Demand**: demandas cirúrgicas extraídas ou criadas manualmente
- **Schedule**: escalas geradas (DRAFT, PUBLISHED, ARCHIVED)
- **Job**: jobs assíncronos (Arq)
- **AuditLog**: log de auditoria de eventos

## Formatos
- **Entrada**: PDF, JPEG, PNG, XLSX, XLS, CSV
- **Saída**: **PDF** (somente)

## Princípios de arquitetura (Fase 1)
1. **Requests HTTP nunca rodam solver/IA**: sempre criam **Job** e retornam `job_id`.
2. **Schedule**: cada geração cria uma versão imutável; publicação é um passo separado.
3. **Multi-tenant por `tenant_id`** em todas as tabelas (enforcement na camada de repositório/serviço no MVP).
4. **Storage fora do banco**: arquivos sempre em object storage; banco guarda apenas metadados/URLs.
5. **Separação Account (privado) vs Member (público)**: dados de autenticação separados de dados da clínica.
