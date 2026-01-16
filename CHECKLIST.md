# Checklist de Implementação - Stack Fase 1

Este checklist organiza as tarefas necessárias para aderir completamente à stack definida em `stack.md`, seguindo uma abordagem **incremental e testável** em cada etapa.

---

## Status Geral

- **Infraestrutura**: Docker Compose configurado (PostgreSQL na porta 5433, Redis, MinIO)
- **Dependências**: Bibliotecas instaladas (FastAPI, SQLModel, Arq, psycopg2-binary, etc.)
- **Endpoint básico**: `/health` funcionando
- **Modelos**: ✅ Tenant, Account, Membership, Job, File, ScheduleVersion, AuditLog criados e migrados
- **Autenticação**: ✅ OAuth Google, JWT, Membership, convites, multi-tenant isolation
- **Storage**: ✅ S3/MinIO configurado, upload/download funcionando
- **Jobs**: ✅ Arq worker, PING, EXTRACT_DEMAND, GENERATE_SCHEDULE implementados
- **Implementação**: ~70% - Fundações completas, falta completar endpoints e testes

---

## Caminho Mínimo Incremental

Cada etapa abaixo entrega algo **visível e testável** via Swagger (`/docs`) ou curl, sem quebrar o que já funciona.

### Etapa 0: Base (Já feito)
- [x] Docker Compose sobe sem erros
- [x] `/health` retorna `{"status": "ok"}`
- [x] Dependências instaladas

### Etapa 1: DB + 3 tabelas básicas
- [x] Modelos: Tenant, Account, Job
- [x] Alembic configurado e migração aplicada
- [x] Endpoint `POST /tenant` (criar tenant simples)
- [x] Testar: criar tenant via `/docs`, verificar no banco

### Etapa 2: OAuth + JWT + `/me`
- [x] OAuth Google integrado
- [x] JWT com `tenant_id` no token
- [x] Endpoint `GET /me` retorna Account do banco
- [x] Testar: login via Google, verificar JWT, chamar `/me`

### Etapa 3: Upload + File + MinIO
- [x] Modelo File
- [x] StorageService básico (upload/download)
- [x] Endpoint `POST /file/upload` retorna URL/presigned
- [x] Testar: upload arquivo, verificar MinIO e banco

### Etapa 4: Arq - Job fake primeiro
- [x] WorkerSettings configurado
- [x] Job `PING_JOB` (fake, só valida fila)
- [x] Endpoint `POST /job/ping` cria Job e enfileira
- [x] Endpoint `GET /job/{job_id}` retorna status/resultado (validando tenant)
- [x] Testar: criar job, ver worker processar, ver status

### Etapa 5: Arq - EXTRACT_DEMAND
- [x] Job `EXTRACT_DEMAND` com OpenAI (adaptar `demand/read.py`)
- [x] Salvar resultado como JSON no `Job.result_data`
- [x] Endpoint `POST /job/extract` (recebe file_id)
- [x] Testar: upload → extract → ver resultado no Job

### Etapa 6: ScheduleVersion + GenerateSchedule
- [x] Modelo ScheduleVersion
- [x] Job `GENERATE_SCHEDULE` (usar código de `strategy/`)
- [x] Salvar resultado no ScheduleVersion
- [x] Endpoint `POST /schedule/generate`
- [x] Testar: gerar escala, ver ScheduleVersion criado (script `script_test_schedule_generate.py`)

### Etapa 7: PDF + Publicação
- [x] Gerar PDF (adaptar `output/day.py`)
- [x] Upload PDF para S3
- [x] Endpoint `POST /schedule/{id}/publish`
- [x] Endpoint `GET /schedule/{id}/pdf` (download)
- [x] Testar: publicar → download PDF (ok no container, gerou `output_test_schedule.pdf`)

---

## FASE 1: Fundações - Modelos e Banco de Dados

### 1.1 Modelos SQLModel (Mínimo Inicial: 5 tabelas)

**Começar simples, evoluir depois:**

- [x] Criar `app/model/__init__.py`
- [x] Criar `app/model/base.py`:
  - [x] Classe base `BaseModel` (SQLModel) com:
    - [x] `id: int` (primary key)
    - [x] `created_at: datetime`
    - [x] `updated_at: datetime`
- [x] Criar `app/model/tenant.py`:
  - [x] Modelo `Tenant` (id, name, slug, timezone, created_at, updated_at)
  - [x] Sem `tenant_id` (é a raiz do multi-tenant)
- [x] Criar `app/model/account.py`:
  - [x] Modelo `Account` (id, email, name, role, auth_provider, created_at, updated_at)
  - [x] Email único global (um Account pode participar de múltiplos tenants via Membership)
- [x] Criar `app/model/membership.py`:
  - [x] Modelo `Membership` (id, tenant_id, account_id, role, status, created_at, updated_at)
  - [x] UniqueConstraint em `(tenant_id, account_id)`
  - [x] Role e status como Enums (MembershipRole, MembershipStatus)
- [x] Criar `app/model/job.py`:
  - [x] Modelo `Job` (id, tenant_id, job_type, status, input_data JSON, result_data JSON, error_message, created_at, updated_at, completed_at)
  - [x] Enum para `job_type`: `PING`, `EXTRACT_DEMAND`, `GENERATE_SCHEDULE`
  - [x] Enum para `status`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`
  - [x] **Nota**: `result_data` guarda Demandas como JSON inicialmente
- [x] Criar `app/model/file.py`:
  - [x] Modelo `File` (id, tenant_id, filename, content_type, s3_key, s3_url, file_size, uploaded_at, created_at)
- [x] Criar `app/model/schedule_version.py`:
  - [x] Modelo `ScheduleVersion` (id, tenant_id, name, period_start_at, period_end_at, status, version_number, job_id FK nullable, pdf_file_id FK nullable, result_data JSON, generated_at, published_at, created_at)
  - [x] Enum para `status`: `DRAFT`, `PUBLISHED`, `ARCHIVED`
  - [x] **Nota**: `result_data` guarda resultado da geração (alocação) como JSON

**Evolução futura (quando necessário):**
- [ ] Criar `app/model/schedule.py` (quando precisar de múltiplas versões por schedule)
- [ ] Criar `app/model/demand.py` (quando precisar queryar demandas diretamente)
- [ ] Criar `app/model/professional.py` (quando precisar CRUD de profissionais)

### 1.2 Configuração do Alembic
- [x] Atualizar `alembic/env.py`:
  - [x] Importar `Base` do SQLModel (ou metadata do SQLAlchemy)
  - [x] Definir `target_metadata` apontando para os modelos
  - [x] Garantir que `compare_type=True` está ativo
- [x] Criar migração inicial: `alembic revision --autogenerate -m "Initial schema - Tenant, Account, Job"`
- [x] Revisar migração gerada (verificar se 3 tabelas foram incluídas)
- [x] Testar migração: `alembic upgrade head`
- [x] Verificar se tabelas foram criadas no PostgreSQL

### 1.3 Utilitários de Banco
- [x] Criar `app/db/__init__.py`
- [x] Criar `app/db/session.py`:
  - [x] Função `get_session()` (dependency do FastAPI)
  - [x] Configurar engine do SQLModel com `DATABASE_URL`
  - [x] Criar engine singleton
- [x] Criar `app/db/base.py`:
  - [x] Função para criar todas as tabelas (útil para testes)

---

## FASE 2: Autenticação e Multi-Tenant

### 2.1 Integração de Autenticação
- [x] Criar `app/auth/__init__.py`
- [x] Criar `app/auth/jwt.py`:
  - [x] Função `create_access_token(account_id, tenant_id, role)` retornando JWT
  - [x] Função `verify_token(token)` retornando payload (account_id, tenant_id, role)
  - [x] Usar `JWT_SECRET` e `JWT_ISSUER` do ambiente
  - [x] Claims obrigatórios: `account_id`, `tenant_id`, `role`, `exp`, `iat`, `iss`
  - [x] Role vem do Membership (implementado)
- [x] Criar `app/auth/dependencies.py`:
  - [x] Dependency `get_current_account(session, token)` retornando Account
  - [x] Dependency `get_current_membership(session, token)` validando acesso via Membership ACTIVE
  - [x] Dependency `require_role(role: str)` para verificar permissões (usa Membership)
  - [x] Dependency `get_current_tenant(session, token)` retornando Tenant (usa Membership)
- [x] Migrar lógica do `login.py` para `app/auth/oauth.py`:
  - [x] Função `verify_google_token(token)` com clock_skew_in_seconds
- [x] Criar `app/api/auth.py`:
  - [x] Endpoint `POST /auth/google` (login - busca Account por email, valida memberships)
  - [x] Endpoint `POST /auth/google/register` (cria Account sem tenant_id, cria Membership se necessário)
  - [x] Endpoint `POST /auth/switch-tenant` (trocar tenant quando já autenticado)
  - [x] Endpoint `GET /auth/tenant/list` (lista tenants disponíveis e convites pendentes)
  - [x] Endpoint `GET /auth/invites` (lista convites pendentes do usuário)
  - [x] Endpoint `POST /auth/invites/{membership_id}/accept` (aceitar convite)
  - [x] Endpoint `POST /auth/invites/{membership_id}/reject` (rejeitar convite)
- [x] Atualizar `app/api/routes.py`:
  - [x] Importar router de autenticação
  - [x] Incluir rotas de auth
  - [x] Endpoint `GET /me` na raiz
- [x] Testar autenticação:
  - [x] Login com Google retorna JWT válido
  - [x] JWT contém `tenant_id` e `role` (do Membership)
  - [x] `GET /me` retorna dados do usuário do banco (com role do Membership)
  - [x] Multi-tenant isolation funcionando (usuário só vê dados do seu tenant)

### 2.2 Multi-Tenant Enforcement
- [x] Criar `app/services/tenant_service.py`:
  - [x] Função `get_tenant_by_id(tenant_id)`
  - [x] Função `create_tenant(name, slug)`
- [x] Criar `app/middleware/tenant.py`:
  - [x] Middleware que extrai `tenant_id` do JWT e adiciona ao `request.state` (contexto, sem DB)
  - [x] **Nota**: validação/enforcement real continua no `get_current_membership()` (não consultar DB no middleware)
- [x] Aplicar middleware em `app/main.py`
- [x] Criar helper `get_tenant_id(request)` para endpoints
- [x] Documentar padrão: `tenant_id` nunca vem do body/querystring; sempre do contexto (membership/JWT/request.state)

### 2.3 Sistema de Membership e Convites

**Modelo implementado**:
- **Tenant** = clínica (entidade organizacional)
- **Account** = pessoa física (login Google, único global por email, sem tenant_id)
- **Membership** = vínculo Account↔Tenant com role e status (um usuário pode estar em múltiplos tenants)

- [x] Modelo `Membership` implementado com:
  - [x] UniqueConstraint em `(tenant_id, account_id)`
  - [x] Role e status como Enums (MembershipRole, MembershipStatus)
  - [x] Índices em `tenant_id`, `account_id`, `status`
- [x] Endpoints de autenticação:
  - [x] `POST /auth/google` (login - busca Account por email, valida memberships)
  - [x] `POST /auth/google/register` (cria Account sem tenant_id, cria Membership se necessário)
  - [x] `POST /auth/switch-tenant` (trocar tenant quando já autenticado)
  - [x] `GET /auth/tenant/list` (lista tenants disponíveis e convites pendentes)
- [x] Endpoints de convites:
  - [x] `POST /tenant/{tenant_id}/invite` (admin convida email, cria Membership PENDING)
  - [x] `GET /auth/invites` (lista convites pendentes do usuário)
  - [x] `POST /auth/invites/{membership_id}/accept` (aceitar convite)
  - [x] `POST /auth/invites/{membership_id}/reject` (rejeitar convite)
- [x] Endpoint `POST /tenant` (criar clínica):
  - [x] Cria Tenant e Membership ADMIN ACTIVE para o usuário
- [x] Validações de segurança:
  - [x] Não permitir criar membership duplicado (constraint no banco + tratamento HTTP 409 na API)
  - [x] Não permitir remover último membership ACTIVE de um account (soft-delete bloqueia)
  - [x] CHECK constraints no banco para validar role e status válidos
- [x] Logs/auditoria:
  - [x] Tabela `audit_log` para rastrear eventos (membership_invited, membership_status_changed, tenant_switched)
  - [x] Logs em endpoints relevantes (`app/api/auth.py`, `app/api/route.py`)

### 2.4 JWT e Dependencies
- [x] `app/auth/jwt.py`:
  - [x] `create_access_token(account_id, tenant_id, role, email, name)` - role vem do Membership
  - [x] `verify_token(token)` retorna payload com account_id, tenant_id, role
- [x] `app/auth/dependencies.py`:
  - [x] `get_current_account()` - busca Account por account_id do JWT (sem filtro de tenant)
  - [x] `get_current_membership()` - valida acesso via Membership ACTIVE
  - [x] `get_current_tenant()` - usa Membership para validar e retornar Tenant
  - [x] `require_role(required_role)` - verifica role do Membership

---

## FASE 3: Storage (S3/MinIO)

### 3.1 Configuração S3/MinIO
- [x] Criar `app/storage/__init__.py`
- [x] Criar `app/storage/config.py`:
  - [x] Classe `S3Config` lendo variáveis: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_REGION`, `S3_USE_SSL`
  - [x] Validar placeholder de `S3_ENDPOINT_URL` (evita `https://SEU_S3`)
- [x] Criar `app/storage/client.py`:
  - [x] Classe `S3Client` usando boto3
  - [x] Método `upload_file(file_path, s3_key, content_type) -> s3_url`
  - [x] Método `upload_fileobj(file_obj, s3_key, content_type) -> s3_url`
  - [x] Método `download_file(s3_key, local_path)`
  - [x] Método `get_presigned_url(s3_key, expiration)`
  - [x] Método `ensure_bucket_exists()` (criar bucket se não existir)
- [x] Criar `app/storage/service.py`:
  - [x] Classe `StorageService` que usa `S3Client`
  - [x] Método `upload_imported_file(session, tenant_id, file, filename) -> File`
  - [x] Método `upload_schedule_pdf(session, tenant_id, schedule_version_id, pdf_bytes) -> File`
  - [x] Método `get_file_presigned_url(s3_key, expiration) -> str`
  - [x] Padrão de S3 keys: `{tenant_id}/{file_type}/{filename}` (com sufixo UUID pra evitar colisão)

### 3.2 Integração com Modelos
- [x] Criar endpoint `POST /file/upload`:
  - [x] Receber arquivo via multipart
  - [x] Upload para S3 (StorageService)
  - [x] Criar File no banco
  - [x] Retornar `{file_id, s3_url, presigned_url}`
- [x] Testar upload/download:
  - [x] Upload de arquivo cria registro no banco e arquivo no MinIO
  - [ ] Download retorna arquivo correto
  - [x] URLs presignadas funcionam

---

## FASE 4: Job Assíncrono (Arq) - Incremental

### 4.1 Configuração Básica de Worker
- [x] Atualizar `app/worker/worker_settings.py`:
  - [x] Configurar `redis_settings` usando `REDIS_URL`
  - [x] Registrar `functions` do Arq (inclui `ping_job`)
- [x] Atualizar `app/worker/run.py`:
  - [x] Iniciar worker com `run_worker(WorkerSettings)`

### 4.2 Job Fake (PING) - Validar Fila
- [x] Criar `app/worker/job.py`:
  - [x] Função `ping_job(ctx, job_id)` (job fake) atualiza status no banco e grava `result_data={"pong": true}`
- [x] Criar endpoint `POST /job/ping`:
  - [x] Criar Job no banco (tipo PING, status PENDING)
  - [x] Enfileirar job no Arq
  - [x] Retornar `{job_id}`
- [x] Criar endpoint `GET /job/{job_id}`:
  - [x] Retornar status e resultado do Job (validando tenant)
- [x] Testar: criar job ping, ver worker processar, verificar status COMPLETED

### 4.3 Job EXTRACT_DEMAND (OpenAI)
- [x] Implementar `extract_demand_job(ctx, job_id)` no worker (Arq):
  - [x] Buscar File do banco (validar tenant_id)
  - [x] Download do S3/MinIO para arquivo temporário
  - [x] Chamar `demand/read.py` (OpenAI text-only/vision conforme disponível)
  - [x] Salvar resultado como JSON no `Job.result_data`
  - [x] Atualizar Job status (RUNNING/COMPLETED/FAILED)
- [x] Criar endpoint `POST /job/extract`:
  - [x] Receber `file_id`
  - [x] Criar Job (tipo EXTRACT_DEMAND, status PENDING)
  - [x] Enfileirar job no Arq
  - [x] Retornar `{job_id}`
- [x] Testar: upload arquivo → extract → ver demandas no `Job.result_data`
- [x] Job robustness (órfãos):
  - [x] Campo `Job.started_at` (migration Alembic)
  - [x] Worker marca `started_at` ao entrar em RUNNING
  - [x] Reconciler (cron) auto-fail apenas de `PENDING` stale com `started_at IS NULL`
  - [x] Endpoint admin `POST /job/{id}/requeue` com `force` e `wipe_result` (regras anti-duplicação)

### 4.4 Job GENERATE_SCHEDULE
- [x] Implementar no worker (`app/worker/job.py`):
  - [x] Função `generate_schedule_job(ctx, job_id)`
  - [x] Lógica (MVP):
    1. Buscar `Job` e marcar `RUNNING` + `started_at`
    2. Buscar `ScheduleVersion` do banco (validar tenant)
    3. Buscar job de extração (`extract_job_id`) e ler demandas do `result_data`
    4. Buscar profissionais (`pros_by_sequence` no input; mock no script)
    5. Chamar solver greedy (código de `strategy/`)
    6. Salvar resultado no `ScheduleVersion.result_data` e `generated_at`
    7. Atualizar Job status (`COMPLETED`/`FAILED`) e `result_data`
  - [x] PDF + S3 + `pdf_file_id` (Etapa 7) (via endpoint `POST /schedule/{id}/publish`)
- [x] Criar endpoint `POST /schedule/generate`:
  - [x] Receber `extract_job_id`, `period_start_at`, `period_end_at`, `allocation_mode`, `pros_by_sequence` (opcional)
  - [x] Criar `ScheduleVersion` (DRAFT) e vincular `job_id`
  - [x] Criar Job (tipo GENERATE_SCHEDULE, status PENDING)
  - [x] Enfileirar `generate_schedule_job` no Arq
  - [x] Retornar `{job_id, schedule_version_id}`
- [x] Testar: gerar escala, ver `schedule_version.result_data` preenchido (script `script_test_schedule_generate.py --db-check`)

**Nota**: Abstração completa de AI Provider (interface formal) fica para depois, quando precisar plugar outro provedor.

---

## FASE 5: API Endpoints Completos

### 5.1 Endpoints de Tenants
- [x] `POST /tenant` (criar tenant - já implementado em `app/api/route.py`)
  - [x] Cria Tenant e Membership ADMIN ACTIVE para o criador
- [x] `GET /tenant/me` (tenant atual do usuário - implementado em `app/api/route.py`)

### 5.2 Endpoints de Schedule
- [x] Criar `app/api/schedule.py`:
  - [ ] `GET /schedule/list` (listar ScheduleVersions - filtrado por tenant)
  - [ ] `POST /schedule` (criar ScheduleVersion - filtrado por tenant)
  - [ ] `GET /schedule/{id}` (detalhes - validar tenant)
  - [x] `POST /schedule/{id}/publish` (publicar versão - validar tenant)
  - [x] `GET /schedule/{id}/pdf` (download PDF - validar tenant)
  - [x] Retornar URL presignada do S3

### 5.3 Endpoint de Job
- [x] Endpoints implementados em `app/api/route.py`:
  - [x] `GET /job/list` (listar jobs do tenant, com paginação e filtros por tipo/status)
  - [x] `GET /job/{job_id}` (detalhes - validar tenant)

### 5.4 Validações e Segurança
- [x] Garantir que TODOS os endpoints validam tenant_id:
  - [x] Extrair de JWT via `get_current_membership()` (implementado em todos os endpoints)
  - [x] Validar que tenant existe (validação implícita em `get_current_membership()`)
  - [x] Filtrar queries por tenant_id (implementado em todos os endpoints de listagem)
- [x] Garantir que endpoints de criação/atualização não permitem alterar tenant_id:
  - [x] Endpoints de criação usam `membership.tenant_id` (não aceitam do body)
  - [x] Endpoints de atualização validam `tenant_id` e não permitem alteração
- [x] Documentar padrões de segurança:
  - [x] Criado `SECURITY.md` com padrões de validação multi-tenant
  - [x] Documentação de exemplos corretos e incorretos
  - [x] Checklist de validação para novos endpoints
- [x] Documentar API com OpenAPI/Swagger (FastAPI já faz isso automaticamente)

---

## FASE 6: Integração de Código Existente

### 6.1 Adaptação de Solvers
- [ ] Revisar `strategy/greedy/solve.py`:
  - [ ] Adaptar para receber demandas como List[dict] (do JSON)
  - [ ] Adaptar para receber profissionais como List[dict]
  - [ ] Retornar resultado como dict (compatível com ScheduleVersion.result_data)
- [ ] Revisar `strategy/cd_sat/solve.py`:
  - [ ] Mesma adaptação acima
- [ ] Criar `app/services/schedule_service.py`:
  - [ ] Função `generate_schedule(demands, professionals, allocation_mode) -> dict`
  - [ ] Chama solver apropriado (greedy ou CP-SAT)

### 6.2 Adaptação de Geração de PDF
- [x] Revisar `output/day.py`:
  - [x] Retornar bytes do PDF (helpers `render_pdf_bytes()` e `render_multi_day_pdf_bytes()`)
- [ ] Integrar no job `generate_schedule_job`:
  - [ ] Gerar PDF em memória
  - [ ] Upload para S3 via StorageService

### 6.3 Manutenção de Compatibilidade
- [ ] Manter `app.py` funcionando (não quebrar código legado)

---

## FASE 7: Testes e Validação

### 7.1 Testes Básicos
- [x] Script de teste end-to-end criado (`script_test_e2e.py`):
  - [x] Testa fluxo completo automatizado
  - [x] Cria tenant e autentica
  - [x] Faz upload de arquivo
  - [x] Aguarda job de extração processar
  - [x] Cria ScheduleVersion via `/schedule/generate` (pula se não houver demandas)
  - [x] Aguarda job de geração processar
  - [x] Publica escala (`POST /schedule/{id}/publish`) (pula se schedule não gerado)
  - [x] Faz download do PDF (`GET /schedule/{id}/pdf`) (pula se schedule não gerado)
  - [x] Testa endpoints independentes (`/job/list`, `/schedule/list`, `/tenant/me`)
  - [x] Testa isolamento multi-tenant (cria segundo tenant, valida isolamento de jobs/schedules/files)
  - [x] Valida princípios arquiteturais (passo 9)
- [ ] Testar fluxo completo via `/docs` manualmente (validação adicional)
- [x] Testar multi-tenant isolation (usuário de tenant A não vê dados de tenant B) - implementado no script
- [x] Testar que jobs respeitam tenant_id - implementado no script

### 7.2 Validação de Princípios
- [x] Princípio 1: Requests HTTP nunca rodam solver/IA (sempre criam Job)
- [x] Princípio 2: ScheduleVersion imutável, publicação separada (estrutura validada; requer schedule gerado para teste completo)
- [x] Princípio 3: Multi-tenant por tenant_id em todas as tabelas
- [x] Princípio 4: Storage fora do banco (S3, banco só metadados)

## FASE 8: Frontend e Mobile

### 8.1 Organização do Repositório (Monorepo)
- [ ] Manter **um único repositório `turna`** (monorepo)
- [ ] Criar pasta `frontend/` para o projeto Next.js
- [ ] **Não mover o backend neste momento**
  - [ ] Manter código FastAPI na estrutura atual
  - [ ] Evitar impacto em imports, Alembic, Docker e scripts existentes
- [ ] Manter `docker-compose.yml` na raiz do projeto
- [ ] Garantir independência entre backend e frontend:
  - [ ] Backend com seu próprio `requirements.txt`
  - [ ] Frontend com seu próprio `package.json`
  - [ ] Comunicação exclusivamente via API HTTP
  - [ ] Nenhuma dependência direta de código entre as camadas

### 8.2 Frontend Web (Next.js) – Setup Básico
- [ ] Criar projeto Next.js:
  - [ ] Executar `npx create-next-app@latest frontend` com **App Router**
  - [ ] Configurar TypeScript
  - [ ] Configurar ESLint (Prettier opcional)
  - [ ] Criar estrutura inicial:
    - `app/`
    - `components/`
    - `lib/`
    - `hooks/`
    - `types/`
- [ ] Configurar Tailwind CSS (opcional, recomendado):
  - [ ] Instalar e configurar Tailwind
  - [ ] Definir tema mínimo (cores e tipografia)
- [ ] Configurar variáveis de ambiente:
  - [ ] `NEXT_PUBLIC_API_URL` (ex.: `http://localhost:8000`)
  - [ ] `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
  - [ ] Criar `.env.local` para desenvolvimento

### 8.3 Cliente HTTP e Infraestrutura
- [ ] Criar wrapper de chamadas HTTP (`lib/api.ts`):
  - [ ] Baseado em `fetch`
  - [ ] Usar `credentials: "include"` (cookies httpOnly)
  - [ ] Função única para chamadas à API
  - [ ] Tratamento centralizado de erros:
    - 401 → redirecionar para `/login`
    - 403 → mensagem clara de acesso negado
- [ ] Criar types TypeScript:
  - [ ] `AuthResponse`
  - [ ] `TenantOption`
  - [ ] `TokenResponse`
  - [ ] Types para demais endpoints consumidos
- [ ] Gerenciamento de estado (mínimo):
  - [ ] Zustand ou Context API
  - [ ] Estado para informações de sessão (usuário, tenant atual)
  - [ ] Evitar armazenar JWT em estado ou storage

### 8.4 Autenticação – Login e OAuth Google
- [ ] Implementar página de login (`app/(auth)/login/page.tsx`):
  - [ ] Botão “Entrar com Google” (Google Identity Services)
  - [ ] Obter `id_token` do Google
  - [ ] Enviar `id_token` para handler do Next.js
  - [ ] Loading state durante autenticação
- [ ] Criar handlers de autenticação no Next.js:
  - [ ] `app/api/auth/google/login`
    - Recebe `id_token`
    - Chama `POST /auth/google` no backend
    - Grava JWT em **cookie httpOnly**
    - Retorna estado para o frontend
  - [ ] `app/api/auth/google/select-tenant`
    - Recebe `id_token` + `tenant_id`
    - Chama backend
    - Atualiza cookie com novo JWT
  - [ ] `app/api/auth/logout`
    - Remove cookie de autenticação
- [ ] Tratamento de resposta no login:
  - [ ] Token direto → redirect dashboard
  - [ ] `requires_tenant_selection = true` → redirect seleção de tenant
  - [ ] 403 → mensagem clara (“usuário sem acesso a nenhum tenant”)

### 8.5 Seleção de Tenant
- [ ] Implementar página de seleção (`app/(auth)/select-tenant/page.tsx`):
  - [ ] Listar tenants via `GET /auth/tenant/list`
  - [ ] Usar response do login apenas como atalho inicial
  - [ ] Permitir refresh da página sem quebrar o fluxo
  - [ ] Loading state durante seleção
- [ ] Seleção de tenant:
  - [ ] Chamar handler `api/auth/google/select-tenant`
  - [ ] Atualizar cookie httpOnly
  - [ ] Redirect para dashboard

### 8.6 Layout Autenticado e Header
- [ ] Criar layout autenticado (`app/(protected)/layout.tsx`):
  - [ ] Considerar `(protected)` ou `(app)` como grupo de rotas
  - [ ] Proteção via middleware (verificação de cookie)
  - [ ] Carregar tenant atual (`GET /tenant/me`)
- [ ] Criar componente Header:
  - [ ] Nome do tenant atual
  - [ ] Seletor para troca de tenant
  - [ ] Menu do usuário (email, logout)
- [ ] Troca de tenant:
  - [ ] Chamar `GET /auth/tenant/list`
  - [ ] Chamar `POST /auth/switch-tenant`
  - [ ] Atualizar cookie
  - [ ] Recarregar dados dependentes do tenant

### 8.7 Middleware de Proteção de Rotas
- [ ] Criar `middleware.ts` no Next.js:
  - [ ] Verificar **apenas** a presença do cookie
  - [ ] Não validar JWT no frontend
  - [ ] Redirecionar para `/login` se não autenticado
  - [ ] Permitir acesso a rotas públicas (`/login`, `/select-tenant`, `/api/auth/*`)

### 8.8 Dashboard
- [ ] Implementar página Dashboard (`app/(protected)/page.tsx`):
  - [ ] Layout simples e direto
  - [ ] Links rápidos:
    - Nova Importação
    - Ver Escalas
  - [ ] Cards informativos (opcional)

### 8.9 Página de Importação
- [ ] Implementar página de importação (`app/(protected)/import/page.tsx`):
  - [ ] Upload de arquivo (PDF, JPEG, PNG, XLSX, XLS, CSV)
  - [ ] Validação de tipo
  - [ ] Chamar `POST /file/upload`
  - [ ] Receber `file_id`
  - [ ] Criar job (`POST /job/extract`)
  - [ ] Polling de status (`GET /job/{id}`)
  - [ ] Estados: PENDING, RUNNING, COMPLETED, FAILED
  - [ ] Feedback visual claro
  - [ ] Tratamento de erro de job

### 8.10 Página de Escalas
- [ ] Listagem de escalas (`app/(protected)/schedules/page.tsx`):
  - [ ] `GET /schedule/list`
  - [ ] Paginação
  - [ ] Filtros por status
  - [ ] Ordenação por data
- [ ] Detalhe de escala (`app/(protected)/schedules/[id]/page.tsx`):
  - [ ] `GET /schedule/{id}`
  - [ ] Exibir dados principais
  - [ ] Ações:
    - Publicar (DRAFT)
    - Download PDF (PUBLISHED)
  - [ ] Loading e tratamento de erros

### 8.11 UX Essencial e Tratamento de Erros
- [ ] Loading states:
  - [ ] Login OAuth
  - [ ] Seleção de tenant
  - [ ] Upload e processamento
- [ ] Mensagens claras:
  - [ ] 401 → “Sessão expirada”
  - [ ] 403 → “Sem acesso a este tenant”
  - [ ] Erros de upload e job
- [ ] Feedback visual:
  - [ ] Toasts de sucesso/erro
  - [ ] Indicadores de status

### 8.12 Integração com Docker Compose (pós-MVP)
- [ ] Rodar frontend local sem Docker durante desenvolvimento inicial
- [ ] Criar Dockerfile para frontend
- [ ] Adicionar serviço frontend no `docker-compose.yml`:
  - [ ] Porta 3000
  - [ ] Variáveis de ambiente
  - [ ] Hot-reload em desenvolvimento
- [ ] Configurar CORS no backend:
  - [ ] Permitir `http://localhost:3000`
  - [ ] Habilitar credentials
  - [ ] Origin configurável via variável de ambiente

### 8.13 Testes e Validação
- [ ] Fluxos principais:
  - [ ] Login com token direto
  - [ ] Login com seleção de tenant
  - [ ] Troca de tenant pós-login
  - [ ] Logout e re-login
- [ ] Proteção de rotas:
  - [ ] Acesso sem cookie → redirect `/login`
  - [ ] Token inválido → redirect `/login`
- [ ] Refresh em `/select-tenant` não quebra o fluxo
- [ ] Cookies e CORS funcionando corretamente

### 8.13 Mobile (React Native) - Futuro
- [ ] Criar projeto React Native
- [ ] Configurar autenticação (OAuth Google)
- [ ] Telas: Login, Lista de Escalas, Detalhes de Escala
- [ ] Integração com API

---

## 📝 Notas de Implementação

### Filosofia: Mínimo Testável
- Cada etapa entrega algo **visível e testável**
- Testar via Swagger (`/docs`) ou curl antes de avançar
- Não criar abstrações antes da hora (ex: AI Provider interface completa)
- Evoluir domínio quando realmente precisar (ex: Demand como tabela)

### Ordem de Prioridade
1. **Crítico**: Fases 1-4 (fundações, auth, storage, jobs básicos)
2. **Importante**: Fase 5 (API endpoints)
3. **Necessário**: Fase 6 (integração)
4. **Desejável**: Fase 7 (testes)
5. **Em Andamento**: Fase 8.1-8.12 (frontend web)
6. **Futuro**: Fase 8.13 (mobile)

### Boas Práticas
- Sempre validar `tenant_id` em queries
- Sempre criar Job antes de enfileirar
- Sempre usar StorageService para arquivos (nunca salvar no banco)
- Manter código legado funcionando durante migração
- Commits pequenos e frequentes
- Testar cada etapa antes de avançar

### Pontos de Atenção
- Não quebrar `app.py` (código legado ainda pode ser usado)
- Performance: jobs assíncronos são essenciais (solver pode demorar)
- Segurança: validar tenant_id em TODOS os endpoints
- Storage: MinIO em dev, S3 real em produção (configurar via env)
- Saída: apenas PDF (não Excel/CSV)

### Evolução Futura (Quando Necessário)
- [ ] Promover Demand de JSON para tabela (quando precisar queryar diretamente)
- [ ] Criar modelo Schedule (quando precisar múltiplas versões por schedule)
- [ ] Criar modelo Professional (quando precisar CRUD de profissionais)
- [ ] Abstração completa de AI Provider (quando precisar plugar outro provedor)
- [ ] Endpoints mobile específicos (quando criar app React Native)

---

## Checklist de Validação Final

Antes de considerar completo, verificar:

- [x] Modelos SQLModel criados e migrados (Tenant, Account, Membership, Job, File, ScheduleVersion, AuditLog)
- [x] Modelo Account sem tenant_id (email único global)
- [x] Modelo Membership implementado (vínculo Account↔Tenant com role e status)
- [x] Autenticação funcionando com tenant_id no JWT (role do Membership)
- [x] Fluxos de convites e seleção de tenant funcionando
- [x] Multi-tenant enforcement ativo em todos os endpoints (via Membership)
- [x] Storage S3/MinIO funcionando (upload/download)
- [x] Jobs Arq processando corretamente (PING, EXTRACT, GENERATE)
- [x] API endpoints completos seguindo princípios arquiteturais
- [x] Padrões de segurança documentados (`SECURITY.md`)
- [x] Docker Compose sobe sem erros (script de validação criado: `script_validate_docker_compose.py`)
- [x] Migrações Alembic aplicam sem erros
- [x] Fluxo completo testável via `/docs` (login → selecionar tenant → usar API)

---

**Última atualização**: Refatorado para abordagem incremental e testável.

## Scripts de Teste

### `script_validate_docker_compose.py`
Script de validação da infraestrutura Docker Compose:

**Uso:**
```bash
python script_validate_docker_compose.py [--base-url BASE_URL] [--skip-worker]
```

**Validações:**
- Verifica se todos os serviços estão rodando (`docker compose ps`)
- Testa conectividade com PostgreSQL (porta 5433)
- Testa conectividade com Redis (porta 6379)
- Verifica acesso ao MinIO (porta 9000)
- Valida resposta da API (`GET /health`)
- Opcionalmente testa worker criando um job PING

### `script_test_e2e.py`
Script automatizado para teste end-to-end do fluxo completo:

**Uso:**
```bash
python script_test_e2e.py [--base-url BASE_URL] [--test-file FILE_PATH]
```

**Exemplo:**
```bash
python script_test_e2e.py --base-url http://localhost:8000 --test-file test/escala_dia1.pdf
```

**O que testa:**
1. Criar tenant e autenticar (via `/auth/dev/token`)
2. Upload de arquivo (`POST /file/upload`)
3. Criação e processamento de job de extração (`POST /job/extract`)
4. Criação de ScheduleVersion e job de geração (`POST /schedule/generate`)
5. Processamento de job de geração
6. Publicação de escala (`POST /schedule/{id}/publish`)
7. Download do PDF (`GET /schedule/{id}/pdf`)

**Requisitos:**
- API rodando (Docker Compose ou local)
- Worker rodando (para processar jobs)
- Redis disponível
- Arquivo de teste (PDF)
