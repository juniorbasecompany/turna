# Checklist de Implementação - Stack Fase 1

Este checklist organiza as tarefas necessárias para aderir completamente à stack definida em `stack.md`, seguindo uma abordagem **incremental** em cada etapa.

## Status Geral

- **Infraestrutura**: Docker Compose configurado (PostgreSQL na porta 5433, Redis, MinIO)
- **Dependências**: Bibliotecas instaladas (FastAPI, SQLModel, Arq, psycopg2-binary, etc.)
- **Endpoint básico**: `/health` funcionando
- **Modelos**: ✅ Tenant, Account, Member, Job, File, ScheduleVersion, AuditLog, Hospital, Demand criados e migrados
- **Autenticação**: ✅ OAuth Google, JWT, Member, convites, multi-tenant isolation
- **Storage**: ✅ S3/MinIO configurado, upload/download funcionando
- **Jobs**: ✅ Arq worker, PING, EXTRACT_DEMAND, GENERATE_SCHEDULE implementados
- **Implementação**: ~90% - Fundações completas, CRUDs implementados, falta página de escalas e alguns itens opcionais

## Caminho Mínimo Incremental

Cada etapa abaixo entrega algo **visível e funcional** via Swagger (`/docs`) ou curl, sem quebrar o que já funciona.

### Etapa 0: Base (Já feito)
- [x] Docker Compose sobe sem erros
- [x] `/health` retorna `{"status": "ok"}`
- [x] Dependências instaladas

### Etapa 1: DB + 3 tabelas básicas
- [x] Modelos: Tenant, Account, Job
- [x] Alembic configurado e migração aplicada
- [x] Endpoint `POST /tenant` (criar tenant simples)

### Etapa 2: OAuth + JWT + `/me`
- [x] OAuth Google integrado
- [x] JWT com `tenant_id` no token
- [x] Endpoint `GET /me` retorna Account do banco

### Etapa 3: Upload + File + MinIO
- [x] Modelo File
- [x] StorageService básico (upload/download)
- [x] Endpoint `POST /file/upload` retorna URL/presigned

### Etapa 4: Arq - Job fake primeiro
- [x] WorkerSettings configurado
- [x] Job `PING_JOB` (fake, só valida fila)
- [x] Endpoint `POST /job/ping` cria Job e enfileira
- [x] Endpoint `GET /job/{job_id}` retorna status/resultado (validando tenant)

### Etapa 5: Arq - EXTRACT_DEMAND
- [x] Job `EXTRACT_DEMAND` com OpenAI (adaptar `demand/read.py`)
- [x] Salvar resultado como JSON no `Job.result_data`
- [x] Endpoint `POST /job/extract` (recebe file_id)

### Etapa 6: ScheduleVersion + GenerateSchedule
- [x] Modelo ScheduleVersion
- [x] Job `GENERATE_SCHEDULE` (usar código de `strategy/`)
- [x] Salvar resultado no ScheduleVersion
- [x] Endpoint `POST /schedule/generate`

### Etapa 7: PDF + Publicação
- [x] Gerar PDF (adaptar `output/day.py`)
- [x] Upload PDF para S3
- [x] Endpoint `POST /schedule/{id}/publish`
- [x] Endpoint `GET /schedule/{id}/pdf` (download)

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
  - [x] Email único global (um Account pode participar de múltiplos tenants via Member)
- [x] Criar `app/model/member.py`:
  - [x] Modelo `Member` (id, tenant_id, account_id, role, status, created_at, updated_at)
  - [x] UniqueConstraint em `(tenant_id, account_id)`
  - [x] Role e status como Enums (MemberRole, MemberStatus)
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
- [x] Criar `app/model/demand.py` (modelo Demand criado e implementado)

### 1.2 Configuração do Alembic
- [x] Atualizar `alembic/env.py`:
  - [x] Importar `Base` do SQLModel (ou metadata do SQLAlchemy)
  - [x] Definir `target_metadata` apontando para os modelos
  - [x] Garantir que `compare_type=True` está ativo
- [x] Criar migração inicial: `alembic revision --autogenerate -m "Initial schema - Tenant, Account, Job"`
- [x] Revisar migração gerada (verificar se 3 tabelas foram incluídas)
- [x] Verificar se tabelas foram criadas no PostgreSQL

### 1.3 Utilitários de Banco
- [x] Criar `app/db/__init__.py`
- [x] Criar `app/db/session.py`:
  - [x] Função `get_session()` (dependency do FastAPI)
  - [x] Configurar engine do SQLModel com `DATABASE_URL`
  - [x] Criar engine singleton
- [x] Criar `app/db/base.py`:
  - [x] Função para criar todas as tabelas

## FASE 2: Autenticação e Multi-Tenant

### 2.1 Integração de Autenticação
- [x] Criar `app/auth/__init__.py`
- [x] Criar `app/auth/jwt.py`:
  - [x] Função `create_access_token(account_id, tenant_id, role)` retornando JWT
  - [x] Função `verify_token(token)` retornando payload (account_id, tenant_id, role)
  - [x] Usar `JWT_SECRET` e `JWT_ISSUER` do ambiente
  - [x] Claims obrigatórios: `account_id`, `tenant_id`, `role`, `exp`, `iat`, `iss`
  - [x] Role vem do Member (implementado)
- [x] Criar `app/auth/dependencies.py`:
  - [x] Dependency `get_current_account(session, token)` retornando Account
  - [x] Dependency `get_current_member(session, token)` validando acesso via Member ACTIVE
  - [x] Dependency `require_role(role: str)` para verificar permissões (usa Member)
  - [x] Dependency `get_current_tenant(session, token)` retornando Tenant (usa Member)
- [x] Migrar lógica do `login.py` para `app/auth/oauth.py`:
  - [x] Função `verify_google_token(token)` com clock_skew_in_seconds
- [x] Criar `app/api/auth.py`:
  - [x] Endpoint `POST /auth/google` (login - busca Account por email, valida members)
  - [x] Endpoint `POST /auth/google/register` (cria Account sem tenant_id, cria Member se necessário)
  - [x] Endpoint `POST /auth/google/select-tenant` (seleciona tenant e emite JWT)
  - [x] Endpoint `POST /auth/google/create-tenant` (cria tenant automaticamente quando account não tem nenhum tenant ACTIVE)
  - [x] Endpoint `POST /auth/switch-tenant` (trocar tenant quando já autenticado)
  - [x] Endpoint `GET /auth/tenant/list` (lista tenants disponíveis e convites pendentes)
  - [x] Endpoint `GET /auth/invites` (lista convites pendentes do usuário)
  - [x] Endpoint `POST /auth/invites/{member_id}/accept` (aceitar convite)
  - [x] Endpoint `POST /auth/invites/{member_id}/reject` (rejeitar convite)
- [x] Atualizar `app/api/routes.py`:
  - [x] Importar router de autenticação
  - [x] Incluir rotas de auth
  - [x] Endpoint `GET /me` na raiz

### 2.2 Multi-Tenant Enforcement
- [x] Criar `app/services/tenant_service.py`:
  - [x] Função `get_tenant_by_id(tenant_id)`
  - [x] Função `create_tenant(name, slug)`
- [x] Criar `app/middleware/tenant.py`:
  - [x] Middleware que extrai `tenant_id` do JWT e adiciona ao `request.state` (contexto, sem DB)
  - [x] **Nota**: validação/enforcement real continua no `get_current_member()` (não consultar DB no middleware)
- [x] Aplicar middleware em `app/main.py`
- [x] Criar helper `get_tenant_id(request)` para endpoints
- [x] Documentar padrão: `tenant_id` nunca vem do body/querystring; sempre do contexto (member/JWT/request.state)

### 2.3 Sistema de Member e Convites

**Modelo implementado**:
- **Tenant** = clínica (entidade organizacional)
- **Account** = pessoa física (login Google, único global por email, sem tenant_id)
- **Member** = vínculo Account↔Tenant com role e status (um usuário pode estar em múltiplos tenants)

- [x] Modelo `Member` implementado com:
  - [x] UniqueConstraint em `(tenant_id, account_id)`
  - [x] Role e status como Enums (MemberRole, MemberStatus)
  - [x] Índices em `tenant_id`, `account_id`, `status`
- [x] Endpoints de autenticação:
  - [x] `POST /auth/google` (login - busca Account por email, valida members)
  - [x] `POST /auth/google/register` (cria Account sem tenant_id, cria Member se necessário)
  - [x] `POST /auth/switch-tenant` (trocar tenant quando já autenticado)
  - [x] `GET /auth/tenant/list` (lista tenants disponíveis e convites pendentes)
- [x] Endpoints de convites:
  - [x] `POST /tenant/{tenant_id}/invite` (admin convida email, cria Member PENDING)
  - [x] `GET /auth/invites` (lista convites pendentes do usuário)
  - [x] `POST /auth/invites/{member_id}/accept` (aceitar convite)
  - [x] `POST /auth/invites/{member_id}/reject` (rejeitar convite)
- [x] Endpoint `POST /tenant` (criar clínica):
  - [x] Cria Tenant e Member ADMIN ACTIVE para o usuário
- [x] Validações de segurança:
  - [x] Não permitir criar member duplicado (constraint no banco + tratamento HTTP 409 na API)
  - [x] Não permitir remover último member ACTIVE de um account (soft-delete bloqueia)
  - [x] CHECK constraints no banco para validar role e status válidos
- [x] Logs/auditoria:
  - [x] Tabela `audit_log` para rastrear eventos (member_invited, member_status_changed, tenant_switched)
  - [x] Logs em endpoints relevantes (`app/api/auth.py`, `app/api/route.py`)

### 2.4 JWT e Dependencies
- [x] JWT implementado com campos mínimos (`sub`, `tenant_id`, `iat`, `exp`, `iss`)
- [x] Dependencies implementadas (`get_current_account`, `get_current_member`, `require_role`, `get_current_tenant`)

### 2.5 Separação Account.name (privado) vs Member.name (público)

Ver `DIRECTIVES.md` para decisões e regras completas.

**Estado atual:**
- **Account.name**: Privado - apenas o próprio usuário vê. Sempre vem do Google OAuth, nunca de `Member.name`
- **Account.email**: Privado - usado apenas para login/autenticação
- **Member.name**: Público - nome na clínica, editável por admin. Preenchido automaticamente se NULL (ao aceitar convite ou primeiro login)
- **Member.email**: Público - email na clínica, editável por admin. Sincroniza uma vez com `account.email` se estiver vazio ao aceitar/rejeitar convite
- **Member.account_id**: Pode ser NULL para convites pendentes
- **JWT**: Contém apenas `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`. Dados sempre vêm do banco via endpoints
- **Endpoint `/me`**: Retorna ambos `account_name` e `member_name`
- **Endpoint `/member/list`**: Retorna apenas `member_name` e `member_email`
- **Endpoint `PUT /member/{id}`**: Permite editar `member.name` e `member.email` (apenas admin)
- **Email de convite**: Usa `member.email`
- **AuditLog**: Registra `member.name` e `member.email`

**Pendente:**
- [x] Header implementado com nome do tenant e menu do usuário

**Futuro:**
- Painel de Accounts terá regras de acesso restritas (apenas o próprio usuário vê seus dados)

### 2.6 Member Independente de Account (Painel)

**Estado atual:**
- **Account (Privado)**: `account.email` e `account.name` são privados, usados apenas para autenticação
- **Member (Público)**: `member.email` e `member.name` são públicos, editáveis livremente pelo admin
- **Painel de Member**: Não tem relação com Account. Não usa `account_id` para criar ou editar member
- **Sincronização de email**: `accept_invite()`, `auth_google_select_tenant()` e `switch_tenant()` preenchem `member.email` se vazio
- **Schema `MemberCreate`**: Aceita `email` e `name` (sem `account_id` obrigatório)
- **Endpoint `POST /member`**: Permite criar member com `email` e `name` públicos
- **Endpoint `PUT /member/{id}`**: Permite atualizar `member.email` (campo público)
- **Endpoint de envio de convite**: Usa `member.email` como principal
- **`MemberResponse`**: Inclui `member_email`
- **`list_members()`**: Retorna `member_email` (não `account_email`)
- **Frontend**: Painel permite criar e editar member com `email` e `name` públicos, sem referência a Account

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

**Nota**: Abstração completa de AI Provider (interface formal) fica para depois, quando precisar plugar outro provedor.

## FASE 5: API Endpoints Completos

### 5.1 Endpoints de Tenants
- [x] `POST /tenant` (criar tenant - já implementado em `app/api/route.py`)
  - [x] Cria Tenant e Member ADMIN ACTIVE para o criador
  - [x] Cria hospital default automaticamente
- [x] `GET /tenant/list` (listar tenants - apenas admin)
- [x] `GET /tenant/me` (tenant atual do usuário - implementado em `app/api/route.py`)
- [x] `PUT /tenant/{tenant_id}` (atualizar tenant - apenas admin)
- [x] `DELETE /tenant/{tenant_id}` (excluir tenant - apenas admin)

### 5.2 Endpoints de Schedule
- [x] Criar `app/api/schedule.py`:
  - [x] `GET /schedule/list` (listar ScheduleVersions - filtrado por tenant)
  - [x] `POST /schedule` (criar ScheduleVersion - filtrado por tenant)
  - [x] `GET /schedule/{id}` (detalhes - validar tenant)
  - [x] `POST /schedule/{id}/publish` (publicar versão - validar tenant)
  - [x] `GET /schedule/{id}/pdf` (download PDF - validar tenant)
  - [x] Retornar URL presignada do S3

### 5.3 Endpoint de Job
- [x] Endpoints implementados em `app/api/route.py`:
  - [x] `POST /job/ping` (criar job PING para teste)
  - [x] `POST /job/extract` (criar job EXTRACT_DEMAND)
  - [x] `GET /job/list` (listar jobs do tenant, com paginação e filtros por tipo/status)
  - [x] `GET /job/{job_id}` (detalhes - validar tenant)
  - [x] `POST /job/{job_id}/requeue` (re-enfileirar job - apenas admin)

### 5.4 Endpoints de Member
- [x] Endpoints implementados em `app/api/route.py`:
  - [x] `POST /member` (criar member - apenas admin)
  - [x] `GET /member/list` (listar members do tenant - apenas admin)
  - [x] `GET /member/{member_id}` (detalhes - apenas admin)
  - [x] `PUT /member/{member_id}` (atualizar member - apenas admin)
  - [x] `DELETE /member/{member_id}` (excluir member - apenas admin)
  - [x] `POST /member/{member_id}/invite` (enviar email de convite - apenas admin)

### 5.5 Endpoints de Account
- [x] Endpoints implementados em `app/api/route.py`:
  - [x] `POST /account` (criar account - apenas admin)
  - [x] `GET /account/list` (listar accounts - apenas admin)
  - [x] `PUT /account/{account_id}` (atualizar account - apenas admin)
  - [x] `DELETE /account/{account_id}` (excluir account - apenas admin)

### 5.6 Endpoints de Demand
- [x] Endpoints implementados em `app/api/route.py`:
  - [x] `POST /demand` (criar demand)
  - [x] `GET /demand/list` (listar demands do tenant)
  - [x] `GET /demand/{demand_id}` (detalhes - validar tenant)
  - [x] `PUT /demand/{demand_id}` (atualizar demand - validar tenant)
  - [x] `DELETE /demand/{demand_id}` (excluir demand - validar tenant)

### 5.7 Endpoints de File
- [x] `POST /file/upload` (upload de arquivo - já implementado em `app/api/route.py`)
- [x] `GET /file/list` (listar arquivos do tenant com paginação e filtros):
  - [x] Parâmetros de query:
    - [x] `start_at` (opcional, timestamptz em ISO 8601) - filtro por `created_at >= start_at`
    - [x] `end_at` (opcional, timestamptz em ISO 8601) - filtro por `created_at <= end_at`
    - [x] `limit` (padrão: 20, ge=1, le=100) - número máximo de itens
    - [x] `offset` (padrão: 0, ge=0) - offset para paginação
  - [x] Filtrar exclusivamente pelo campo `created_at` (não usar `uploaded_at` ou `updated_at`)
  - [x] Sempre filtrar por `tenant_id` do JWT (via `get_current_member()`)
  - [x] Não aceitar `tenant_id` via request (usar contexto do JWT)
  - [x] Ordenar por `created_at` (decrescente)
  - [x] Retornar total de registros para suporte à paginação
  - [x] Response: `{items: FileResponse[], total: int}` (seguindo padrão de `/job/list`)
  - [x] Retornar `job_status` (status do job EXTRACT_DEMAND mais recente do arquivo)
- [x] `GET /file/{file_id}` (obter informações do arquivo e URL presignada)
- [x] `GET /file/{file_id}/download` (download direto do arquivo)
- [x] `DELETE /file/{file_id}` (excluir arquivo do banco e S3/MinIO - sem restrições)

### 5.8 Endpoints de Autenticação Adicionais
- [x] Endpoints implementados em `app/api/auth.py`:
  - [x] `POST /auth/google/create-tenant` (criar tenant automaticamente quando account não tem nenhum tenant ACTIVE)
  - [x] `POST /auth/dev/token` (endpoint de desenvolvimento para gerar token)

### 5.9 Validações e Segurança
- [x] Garantir que TODOS os endpoints validam tenant_id:
  - [x] Extrair de JWT via `get_current_member()` (implementado em todos os endpoints)
  - [x] Validar que tenant existe (validação implícita em `get_current_member()`)
  - [x] Filtrar queries por tenant_id (implementado em todos os endpoints de listagem)
- [x] Garantir que endpoints de criação/atualização não permitem alterar tenant_id:
  - [x] Endpoints de criação usam `member.tenant_id` (não aceitam do body)
  - [x] Endpoints de atualização validam `tenant_id` e não permitem alteração
- [x] Documentar padrões de segurança:
  - [x] Criado `SECURITY.md` com padrões de validação multi-tenant
  - [x] Documentação de exemplos corretos e incorretos
  - [x] Checklist de validação para novos endpoints
- [x] Documentar API com OpenAPI/Swagger (FastAPI já faz isso automaticamente)

## FASE 6: Integração de Código Existente

### 6.1 Adaptação de Solvers
- [x] Revisar `strategy/greedy/solve.py`:
  - [x] Adaptar para receber demandas como List[dict] (do JSON) - já recebe `demands: list[dict]`
  - [x] Adaptar para receber profissionais como List[dict] - já recebe `pros_by_sequence: list[dict]`
  - [x] Retornar resultado como dict (compatível com ScheduleVersion.result_data) - retorna `tuple[list[dict], int]` que é usado diretamente
- [ ] Revisar `strategy/cd_sat/solve.py`:
  - [ ] Mesma adaptação acima (CP-SAT ainda não integrado no worker, apenas greedy)
- [ ] Criar `app/services/schedule_service.py`:
  - [ ] Função `generate_schedule(demands, professionals, allocation_mode) -> dict` (atualmente chamado diretamente no worker)

### 6.2 Adaptação de Geração de PDF
- [x] Revisar `output/day.py`:
  - [x] Retornar bytes do PDF (helpers `render_pdf_bytes()` e `render_multi_day_pdf_bytes()`)
- [x] Integrar geração de PDF (via endpoint `POST /schedule/{id}/publish`):
  - [x] Gerar PDF em memória (`render_multi_day_pdf_bytes()`)
  - [x] Upload para S3 via StorageService (`upload_schedule_pdf()`)
  - [x] **Nota**: PDF é gerado no endpoint de publicação, não no job de geração (conforme arquitetura: ScheduleVersion imutável, publicação separada)

### 6.3 Manutenção de Compatibilidade
- [x] Manter `app.py` funcionando (código legado mantido e funcional)

## FASE 7: Frontend e Mobile

### 8.1 Organização do Repositório (Monorepo)
- [x] Manter **um único repositório `turna`** (monorepo)
- [x] Criar pasta `frontend/` para o projeto Next.js
- [x] **Não mover o backend neste momento**
  - [x] Manter código FastAPI na estrutura atual
  - [x] Evitar impacto em imports, Alembic, Docker e scripts existentes
- [x] Manter `docker-compose.yml` na raiz do projeto
- [x] Garantir independência entre backend e frontend:
  - [x] Backend com seu próprio `requirements.txt`
  - [x] Frontend com seu próprio `package.json`
  - [x] Comunicação exclusivamente via API HTTP
  - [x] Nenhuma dependência direta de código entre as camadas

### 8.2 Frontend Web (Next.js) – Setup Básico
- [x] Criar projeto Next.js:
  - [x] Executar `npx create-next-app@latest frontend` com **App Router**
  - [x] Configurar TypeScript
  - [x] Configurar ESLint (Prettier opcional)
  - [x] Criar estrutura inicial:
    - `app/`
    - `components/`
    - `lib/`
    - `hooks/`
    - `types/`
- [x] Configurar Tailwind CSS (opcional, recomendado):
  - [x] Instalar e configurar Tailwind
  - [x] Definir tema mínimo (cores e tipografia)
- [x] Configurar variáveis de ambiente:
  - [x] `NEXT_PUBLIC_API_URL` (ex.: `http://localhost:8000`)
  - [x] `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
  - [x] Criar `.env.local` para desenvolvimento

### 8.3 Cliente HTTP e Infraestrutura
- [x] Criar wrapper de chamadas HTTP (`lib/api.ts`):
  - [x] Baseado em `fetch`
  - [x] Usar `credentials: "include"` (cookies httpOnly)
  - [x] Função única para chamadas à API
  - [x] Tratamento centralizado de erros:
    - 401 → redirecionar para `/login`
    - 403 → mensagem clara de acesso negado
- [x] Criar types TypeScript:
  - [x] `AuthResponse`
  - [x] `TenantOption`
  - [x] `TokenResponse`
  - [x] Types para demais endpoints consumidos
- [x] Gerenciamento de estado (mínimo):
  - [x] Zustand ou Context API
  - [x] Estado para informações de sessão (usuário, tenant atual)
  - [x] Evitar armazenar JWT em estado ou storage

### 8.4 Autenticação – Login e OAuth Google
- [x] Implementar página de login (`app/(auth)/login/page.tsx`):
  - [x] Botão “Entrar com Google” (Google Identity Services)
  - [x] Obter `id_token` do Google
  - [x] Enviar `id_token` para handler do Next.js
  - [x] Loading state durante autenticação
- [x] Criar handlers de autenticação no Next.js:
  - [x] `app/api/auth/google/login`
    - Recebe `id_token`
    - Chama `POST /auth/google` no backend
    - Grava JWT em **cookie httpOnly**
    - Retorna estado para o frontend
  - [x] `app/api/auth/google/select-tenant`
    - Recebe `id_token` + `tenant_id`
    - Chama backend
    - Atualiza cookie com novo JWT
  - [x] `app/api/auth/logout`
    - Remove cookie de autenticação
- [x] Tratamento de resposta no login:
  - [x] Token direto → redirect dashboard
  - [x] `requires_tenant_selection = true` → redirect seleção de tenant
  - [x] 403 → mensagem clara (“usuário sem acesso a nenhum tenant”)

### 8.5 Seleção de Tenant
- [x] Implementar página de seleção (`app/(auth)/select-tenant/page.tsx`):
  - [x] Listar tenants via `GET /auth/tenant/list`
  - [x] Usar response do login apenas como atalho inicial
  - [x] Permitir refresh da página sem quebrar o fluxo
  - [x] Loading state durante seleção
- [x] Seleção de tenant:
  - [x] Chamar handler `api/auth/google/select-tenant`
  - [x] Atualizar cookie httpOnly
  - [x] Redirect para dashboard

### 8.6 Layout Autenticado e Header
- [x] Criar layout autenticado (`app/(protected)/layout.tsx` ou similar):
  - [x] Considerar `(protected)` ou `(app)` como grupo de rotas
  - [x] **NÃO usar middleware de proteção** que redirecione automaticamente
  - [x] Cada página do layout deve usar `fetch()` direto seguindo padrão de `/dashboard`
  - [x] Carregar tenant atual (`GET /tenant/me`) usando padrão `try { try { fetch() } catch {} } catch {}`
- [x] Criar componente Header:
  - [x] Nome do tenant atual (apenas exibição, não clicável)
  - [x] Menu do usuário (email, logout)
  - [x] Header deve funcionar mesmo se carregar tenant falhar (não quebrar layout)
  - [x] **NOTA**: Troca de tenant deve ser feita saindo do Dashboard (via botão "Sair" → `/select-tenant`), não diretamente no Header

### 8.7 Dashboard
- [x] Implementar página Dashboard (`app/(protected)/dashboard/page.tsx`):
  - [x] Layout simples e direto
  - [x] Cards informativos com totais:
    - [x] Total de hospitais
    - [x] Total de associados
    - [x] Total de demandas
    - [x] Total de arquivos
    - [x] Total de jobs
    - [x] Jobs em execução
  - [x] Links rápidos:
    - [x] Nova Importação (link para `/import`)
    - [x] Ver Escalas (link para `/schedules`)

### 8.8 Página de Importação (Integrada em Arquivos)
- [x] Upload integrado na página de arquivos (`app/(protected)/file/page.tsx`):
  - [x] Upload de arquivo (PDF, JPEG, PNG, XLSX, XLS, CSV)
  - [x] Validação de tipo (extensão e MIME type)
  - [x] Chamar `POST /file/upload` (via `/api/file/upload`)
  - [x] Receber `file_id`
  - [x] Criar job (`POST /job/extract` via `/api/job/extract`)
  - [x] Polling de status (`GET /job/{id}` via `/api/job/[id]`)
  - [x] Estados: PENDING, RUNNING, COMPLETED, FAILED
  - [x] Feedback visual claro (spinners, mensagens de progresso, ícones de status)
  - [x] Tratamento de erro de job (exibe mensagem de erro e permite novo upload)

### 8.9 Página de Escalas
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

### 8.10 Página de Demandas
- [x] Implementar página de demandas (`app/(protected)/demand/page.tsx`):
  - [x] Listagem de demandas do tenant
  - [x] CRUD completo (criar, editar, excluir)
  - [x] Filtros e paginação
  - [x] Validação de tenant_id

### 8.11 Página de Associados
- [x] Implementar página de associados (`app/(protected)/member/page.tsx`):
  - [x] Listagem de members do tenant (apenas admin)
  - [x] CRUD completo (criar, editar, excluir)
  - [x] Envio de convite por email
  - [x] Seleção múltipla para exclusão em lote
  - [x] Validação de tenant_id e permissões

### 8.12 Página de Clínicas
- [x] Implementar página de clínicas (`app/(protected)/tenant/page.tsx`):
  - [x] Listagem de tenants (apenas admin)
  - [x] CRUD completo (criar, editar, excluir)
  - [x] Envio de convites
  - [x] Validação de permissões

### 8.13 Menu Lateral
- [x] Implementar menu lateral (`frontend/components/Sidebar.tsx`):
  - [x] Ordem: Dashboard, Hospitais, Clínicas, Associados, Arquivos, Demandas
  - [x] Itens admin-only (Clínicas, Associados)
  - [x] Ícones e navegação
  - [x] Responsivo com drawer em mobile/tablet

### 8.14 Página de Arquivos
- [x] Navegação:
  - [x] Adicionar opção **Arquivos** no menu principal (Sidebar)
  - [x] Ao clicar, redirecionar para `/file`
- [x] Listagem de arquivos (`app/(protected)/file/page.tsx`):
  - [x] Chamar `GET /file/list` (via handler `/api/file/list`)
  - [x] Listar apenas arquivos do tenant atual (filtrado automaticamente pelo backend)
  - [x] Ordenar por `created_at` (decrescente) - aplicado no backend
  - [x] Exibir cada arquivo como um **card**
  - [x] Cada card deve mostrar:
    - [x] Nome do arquivo (`filename`)
    - [x] Tipo de conteúdo (`content_type`)
    - [x] Ícone visual baseado no tipo de arquivo (PDF, imagem, planilha, etc.)
    - [x] Preview de imagem quando aplicável
    - [x] Tamanho do arquivo (`file_size`) - formatado (ex: "1.5 MB")
    - [x] Data/hora de criação (`created_at`) - formatada no timezone do tenant
    - [x] Status do job (acima da data, em letras pequenas):
      - [x] 'pronto para ser lido' (quando não tem job)
      - [x] 'na fila para ser lido' (PENDING)
      - [x] 'lendo o conteúdo do arquivo' (RUNNING)
      - [x] 'conteúdo lido' (COMPLETED)
      - [x] 'não foi possível ler o conteúdo' (FAILED)
    - [x] Botão para visualizar arquivo (lupa)
    - [x] Botão para marcar para exclusão (ícone de lixeira)
  - [x] Layout responsivo e consistente com outras páginas
- [x] Upload de arquivos:
  - [x] Drag & drop de arquivos
  - [x] Seleção de arquivos via input
  - [x] Suporte a múltiplos arquivos simultâneos
  - [x] Upload automático ao adicionar arquivos
  - [x] Cards de arquivos pendentes durante upload
  - [x] Feedback visual de progresso (texto "Enviando...")
  - [x] Remoção automática de arquivos pendentes após upload bem-sucedido
  - [x] Recarregamento automático da lista após upload
- [x] Visualização de arquivos:
  - [x] Botão de visualizar (lupa) em cada card
  - [x] Abre arquivo em nova aba via `/api/file/{id}/proxy`
  - [x] Preview de imagens no card
- [x] Exclusão de arquivos:
  - [x] Seleção múltipla de arquivos para exclusão
  - [x] Botão de exclusão sempre visível (sem restrições)
  - [x] Exclusão em lote via botão na barra inferior
  - [x] Feedback visual de arquivos selecionados
- [x] Processamento de arquivos (Ler conteúdo):
  - [x] Seleção múltipla de arquivos para leitura
  - [x] Botão "Ler conteúdo" na barra inferior
  - [x] Criação de job EXTRACT_DEMAND para cada arquivo selecionado
  - [x] Atualização automática do status após criar jobs
  - [x] Polling inteligente que atualiza apenas cards afetados (sem recarregar toda a lista)
  - [x] Polling para arquivos com jobs PENDING ou RUNNING
  - [x] Parada automática do polling quando não há mais jobs em andamento
- [x] Filtro por período:
  - [x] Criar filtro com campos de data (data de início e data de fim)
  - [x] Filtrar exclusivamente pelo campo `created_at`
  - [x] Por padrão, exibir apenas arquivos **criados no dia atual** (definir `start_at` e `end_at` no frontend)
  - [x] Validar intervalo (data inicial ≤ data final) no frontend
  - [x] Enviar filtros como query params (`start_at`, `end_at`) na chamada da API
  - [x] Resetar paginação ao mudar filtros
- [x] Paginação:
  - [x] Implementar paginação usando `limit` e `offset`
  - [x] Definir limite padrão de 19 itens por página
  - [x] Exibir controles de navegação (próxima / anterior)
  - [x] Mostrar total de registros e página atual
  - [x] Usar padrão similar a `/job/list` e `/schedule/list`
- [x] Regras gerais:
  - [x] Não expor arquivos de outros tenants (garantido pelo backend)
  - [x] Usar `fetch()` direto seguindo padrão de `/dashboard` (não usar `api.get()`)
  - [x] Datas sempre em `timestamptz` e armazenadas em UTC (conversão de timezone apenas para exibição)
  - [x] Upload não cria job automaticamente (apenas faz upload)
  - [x] Job é criado apenas ao clicar em "Ler conteúdo"

### 8.15 UX Essencial e Tratamento de Erros
- [x] Loading states:
  - [x] Login OAuth
  - [x] Seleção de tenant
  - [x] Upload e processamento
- [x] Mensagens claras:
  - [x] 401 → “Sessão expirada”
  - [x] 403 → “Sem acesso a este tenant”
  - [x] Erros de upload e job (exibidos no ActionBar)
- [x] Indicadores de status:
  - [x] LoadingSpinner em todas as páginas
  - [x] Estados visuais de botões e ações (loading states nos botões do ActionBar)
  - [x] Estados visuais de arquivos (PENDING, RUNNING, COMPLETED, FAILED)
- [ ] Feedback visual (opcional):
  - [ ] Toasts de sucesso/erro (atualmente usando ActionBar para feedback persistente)

### 8.16 Integração com Docker Compose (pós-MVP)
- [x] Rodar frontend local sem Docker durante desenvolvimento inicial
- [ ] Criar Dockerfile para frontend (opcional - frontend roda localmente)
- [ ] Adicionar serviço frontend no `docker-compose.yml` (opcional - frontend roda localmente):
  - [ ] Porta 3000
  - [ ] Variáveis de ambiente
  - [ ] Hot-reload em desenvolvimento
- [x] Configurar CORS no backend:
  - [x] Permitir `http://localhost:3000` (e `http://localhost:3001` por padrão)
  - [x] Habilitar credentials (`allow_credentials=True`)
  - [x] Origin configurável via variável de ambiente `CORS_ORIGINS` (implementado em `app/main.py`)

### 8.17 Mobile (React Native) - Futuro
- [ ] Criar projeto React Native
- [ ] Configurar autenticação (OAuth Google)
- [ ] Telas: Login, Lista de Escalas, Detalhes de Escala
- [ ] Integração com API

## 📝 Notas de Implementação

### Filosofia: Mínimo Incremental
- Cada etapa entrega algo **visível e funcional**
- Não criar abstrações antes da hora (ex: AI Provider interface completa)
- Evoluir domínio quando realmente precisar (ex: Demand como tabela)

### Ordem de Prioridade
1. **Crítico**: Fases 1-4 (fundações, auth, storage, jobs básicos)
2. **Importante**: Fase 5 (API endpoints)
3. **Necessário**: Fase 6 (integração)
4. **Em Andamento**: Fase 7.1-7.13 (frontend web)
5. **Futuro**: Fase 7.13 (mobile)

### Boas Práticas
- Sempre validar `tenant_id` em queries
- Sempre criar Job antes de enfileirar
- Sempre usar StorageService para arquivos (nunca salvar no banco)
- Manter código legado funcionando durante migração
- Commits pequenos e frequentes

### Pontos de Atenção
- Não quebrar `app.py` (código legado ainda pode ser usado)
- Performance: jobs assíncronos são essenciais (solver pode demorar)
- Segurança: validar tenant_id em TODOS os endpoints
- Storage: MinIO em dev, S3 real em produção (configurar via env)
- Saída: apenas PDF (não Excel/CSV)

### Migração para pasta backend
- Ao reorganizar o backend na pasta `backend/`, seguir o **BACKEND_MIGRATION_CHECKLIST.md**.
- Garantir conformidade com DIRECTIVES, SECURITY e STACK; não quebrar Docker, Alembic, jobs nem `app.py`.

### Evolução Futura (Quando Necessário)
- [ ] Promover Demand de JSON para tabela (quando precisar queryar diretamente)
- [ ] Criar modelo Schedule (quando precisar múltiplas versões por schedule)
- [ ] Abstração completa de AI Provider (quando precisar plugar outro provedor)
- [ ] Endpoints mobile específicos (quando criar app React Native)

## Checklist de Validação Final

Antes de considerar completo, verificar:

- [x] Modelos SQLModel criados e migrados (Tenant, Account, Member, Job, File, ScheduleVersion, AuditLog)
- [x] Modelo Account sem tenant_id (email único global)
- [x] Modelo Member implementado (vínculo Account↔Tenant com role e status)
- [x] Autenticação funcionando com tenant_id no JWT (role do Member)
- [x] Fluxos de convites e seleção de tenant funcionando
- [x] Multi-tenant enforcement ativo em todos os endpoints (via Member)
- [x] Storage S3/MinIO funcionando (upload/download)
- [x] Jobs Arq processando corretamente (PING, EXTRACT, GENERATE)
- [x] API endpoints completos seguindo princípios arquiteturais
- [x] Padrões de segurança documentados (`SECURITY.md`)
- [x] Docker Compose sobe sem erros (script de validação criado: `script_validate_docker_compose.py`)
- [x] Migrações Alembic aplicam sem erros

**Última atualização**: Revisado e atualizado com todas as funcionalidades implementadas. Menu atualizado: Dashboard, Hospitais, Clínicas, Associados, Arquivos, Demandas.

## FASE 9: Hospital como Origem das Demandas

### 9.1 Banco de Dados / Modelos
- [x] Criar tabela `hospital`
  - [x] `id` (PK)
  - [x] `tenant_id` (FK, obrigatório)
  - [x] `name` (obrigatório)
  - [x] `prompt` (nullable, pode ser None)
  - [x] `color` (nullable, formato hexadecimal)
  - [x] `created_at` (`timestamptz`)
  - [x] `updated_at` (`timestamptz`)
  - [x] Índice por `tenant_id`
  - [x] Constraint `unique (tenant_id, name)`

- [x] Alterar tabela `file`
  - [x] Adicionar coluna `hospital_id` (FK para `hospital.id`)
  - [x] Definir `hospital_id` como `NOT NULL`
  - [x] Criar índice em `hospital_id`

- [x] Criar migration Alembic
  - [x] Migração `0105op678901_add_hospital_table_and_hospital_id_to_file.py` criada e aplicada
  - [x] Migração `0106qr789012_make_hospital_prompt_nullable.py` (prompt nullable)
  - [x] Migração `0107st890123_add_hospital_color.py` (campo color)

### 9.2 API – Hospital
- [x] Criar endpoints de Hospital (escopo do tenant)
  - [x] `POST /hospital` (admin)
  - [x] `GET /hospital/list`
  - [x] `GET /hospital/{id}`
  - [x] `PUT /hospital/{id}` (admin)
  - [x] `DELETE /hospital/{id}` (admin, com validação de arquivos associados)

- [x] Validações obrigatórias
  - [x] Hospital sempre pertence ao tenant atual
  - [x] Nome obrigatório (prompt pode ser nullable)

### 9.3 Upload de Arquivos
- [x] Ajustar endpoint de upload
  - [x] Exigir `hospital_id` (Query parameter obrigatório)
  - [x] Validar existência do hospital
  - [x] Validar que o hospital pertence ao tenant
  - [x] Criar `file` sempre com `hospital_id`

- [x] Garantir erro claro
  - [x] Upload sem hospital → erro 400 ("hospital_id é obrigatório")
  - [x] Hospital de outro tenant → erro 403 ("Hospital não pertence ao tenant atual")

### 9.4 Processamento / IA
- [x] Ao processar arquivo
  - [x] Carregar hospital via `file.hospital_id` (implementado em `app/worker/job.py`)
  - [x] Usar `hospital.prompt` como prompt base da leitura (passado para `extract_demand()`)
  - [x] Registrar `hospital_id` no job (input/meta) - salvo em `meta["hospital_id"]` e `meta["hospital_name"]`

### 9.5 Painel de Arquivos – Filtro por Hospital
- [x] Backend
  - [x] Listagem de arquivos aceita filtro opcional `hospital_id` (Query parameter)
  - [x] Validar hospital pertence ao tenant
  - [x] Retornar `hospital_id` e `hospital_name` (e `hospital_color`) em cada arquivo

- [x] Frontend
  - [x] Dropdown de hospital (opção vazia = todos)
  - [x] Aplicar filtro ao listar arquivos
  - [x] Mostrar hospital em cada card de arquivo (com cor do hospital)

### 9.6 Tela de Upload – Hospital Obrigatório
- [x] Dropdown de hospital obrigatório
- [x] Botão de upload desabilitado sem hospital selecionado (flash visual quando tenta fazer upload sem selecionar)
- [x] Enviar `hospital_id` junto com o arquivo (via query parameter)
- [x] Mensagem clara ao usuário quando não selecionado (flash visual vermelho no card e no campo)

### 9.7 Consistência e Revisão Final
- [x] Confirmar uso de `timestamptz` em todos os campos de data
- [x] Confirmar padrão multi-tenant em todas as queries
- [x] Atualizar documentação / checklist do projeto

## FASE 10: CRUD de Hospitais + Hospital Default por Tenant

### 10.1 Menu / Navegação

- [x] Adicionar nova opção no menu lateral
  - [x] Posição: abaixo de **Dashboard**
  - [x] Label: **Hospitais**
  - [x] Ícone coerente com cadastro/configuração
  - [x] Rota: `/hospital`

- [x] Garantir visibilidade apenas para usuários com permissão administrativa do tenant

### 10.2 Backend – Modelo e Regras de Negócio

- [x] Confirmar modelo `hospital`
  - [x] `id`
  - [x] `tenant_id` (FK, obrigatório)
  - [x] `name` (obrigatório)
  - [x] `prompt` (nullable, pode ser None)
  - [x] `color` (nullable, formato hexadecimal)
  - [x] `created_at` (`timestamptz`)
  - [x] `updated_at` (`timestamptz`)
  - [x] `unique (tenant_id, name)`

- [x] Garantir isolamento por tenant em todas as operações (CRUD)

### 10.3 Backend – CRUD de Hospitais

- [x] Endpoints
  - [x] `POST /hospital` (criar)
  - [x] `GET /hospital/list` (listar)
  - [x] `GET /hospital/{id}` (detalhe)
  - [x] `PUT /hospital/{id}` (editar)
  - [x] `DELETE /hospital/{id}` (excluir, com validação de arquivos associados)

- [x] Validações
  - [x] `name` obrigatório e único por tenant
  - [x] `prompt` pode ser nullable (não obrigatório)
  - [x] `color` opcional, formato hexadecimal (#RRGGBB)
  - [x] Hospital sempre pertence ao tenant do usuário logado

### 10.4 Tenant – Criação de Hospital Default

- [x] Ajustar fluxo de criação de tenant
  - [x] Após criar o tenant, criar automaticamente um hospital default

- [x] Hospital default
  - [x] `name`: **Hospital**
  - [x] `prompt`:

    ```
    Extraia as demandas cirúrgicas do documento.
    Regras:
    - Responda APENAS JSON.
    - O JSON DEVE conter as chaves: meta, demands.
    - demands é uma lista de objetos com:
      - room (string ou null)
      - start_time (ISO datetime com timezone, ex: "2026-01-12T09:30:00-03:00")
      - end_time (ISO datetime com timezone, ex: "2026-01-12T12:00:00-03:00")
      - procedure (string)
      - anesthesia_type (string ou null)
      - skills (lista; se não houver, [])
      - priority ("Urgente" | "Emergência" | null)  # extrair de notes quando houver "Prioridade: ..."
      - complexity (string ou null)  # se existir como complexidade do caso (Baixa/Média/Alta)
      - professionals (lista; se não houver, [])
      - notes (string ou null)
      - source (objeto livre; inclua page e qualquer raw útil)
    - Não invente dados que não estejam no documento.
    ```

- [x] Garantias
  - [x] Todo tenant nasce com exatamente 1 hospital default
  - [x] Upload de arquivos sempre pode usar esse hospital sem configuração adicional

### 10.5 Frontend – Tela de Hospitais (CRUD)

- [x] Página `/hospital`
  - [x] Lista de hospitais do tenant
  - [x] Mostrar: nome, data de criação, cor
  - [x] Ação: editar e excluir

- [x] Criar hospital
  - [x] Campo **Nome**
  - [x] Campo **Prompt** (textarea grande, monoespaçado)
  - [x] Campo **Cor** (ColorPicker para seleção de cor hexadecimal)
  - [x] Validação de obrigatoriedade do nome

- [x] Editar hospital
  - [x] Permitir alterar nome, prompt e cor
  - [x] Bloquear edição do tenant (validação no backend)

- [x] UX
  - [x] Aviso claro de que o prompt influencia a leitura dos arquivos
  - [x] Delete com validação (não permite excluir se houver arquivos associados)
  - [x] Seleção múltipla para exclusão em lote

### 10.6 Integração com Arquivos

- [x] Confirmar que:
  - [x] Todo `file` referencia um `hospital_id`
  - [x] O hospital default pode ser usado no upload sem ajustes
  - [x] O filtro por hospital no painel de arquivos lista este hospital


### 10.8 Documentação

- [x] Atualizar `CHECKLIST.md`
- [ ] Atualizar documentação de domínio:
  - [ ] Conceito de hospital
  - [ ] Hospital como origem semântica das demandas
  - [ ] Prompt como contrato de extração

## FASE 11: CRUD de Demandas

### 11.1 Modelo Demand
- [x] Modelo `Demand` criado e migrado
- [x] Campos: id, tenant_id, hospital_id, room, start_time, end_time, procedure, etc.
- [x] Relacionamento com Hospital

### 11.2 API – Demand
- [x] Endpoints CRUD completos:
  - [x] `POST /demand` (criar)
  - [x] `GET /demand/list` (listar com filtros)
  - [x] `GET /demand/{id}` (detalhes)
  - [x] `PUT /demand/{id}` (atualizar)
  - [x] `DELETE /demand/{id}` (excluir)
- [x] Validação de tenant_id em todos os endpoints

### 11.3 Frontend – Página de Demandas
- [x] Página `/demand` implementada
- [x] CRUD completo com interface
- [x] Filtros e paginação

## FASE 12: Menu e Navegação

### 12.1 Menu Lateral
- [x] Componente Sidebar implementado
- [x] Ordem: Dashboard, Hospitais, Clínicas, Associados, Arquivos, Demandas
- [x] Itens admin-only (Clínicas, Associados)
- [x] Responsivo com drawer em mobile/tablet
- [x] Ícones SVG para cada item

### 12.2 Navegação
- [x] Todas as páginas principais implementadas:
  - [x] Dashboard (`/dashboard`)
  - [x] Hospitais (`/hospital`)
  - [x] Clínicas (`/tenant`)
  - [x] Associados (`/member`)
  - [x] Arquivos (`/file`)
  - [x] Demandas (`/demand`)

## FASE 13: Envio de Emails com Resend

### 13.1 Dependências e Configuração

- [x] Adicionar `resend` ao `requirements.txt`:
  - [x] Versão: `resend>=2.0.0` (suporta type hints e melhorias)
- [ ] Criar conta no Resend (https://resend.com):
  - [ ] Obter API key do dashboard
  - [ ] Verificar domínio
- [x] Configurar variáveis de ambiente:
  - [x] `RESEND_API_KEY` (API key do Resend)
  - [x] `EMAIL_FROM` (endereço remetente, ex: `noreply@seudominio.com`)
  - [x] `APP_URL` (URL do aplicativo para links nos emails, já existe)

### 13.2 Atualização do Serviço de Email

- [x] Atualizar `app/services/email_service.py`:
  - [x] Importar `resend` e configurar API key via variável de ambiente
  - [x] Modificar `send_member_invite()` para usar Resend :
    - [x] Usar `resend.Emails.send()` com parâmetros adequados
    - [x] Definir `from` usando `EMAIL_FROM`
    - [x] Definir `to` com email do profissional
    - [x] Definir `subject` com assunto do convite
    - [x] Definir `html` com corpo do email (template HTML criado)
    - [x] Tratar erros da API do Resend (exceptions)
    - [x] Manter logging para debug
  - [x] Manter fallback para modo "log" quando `RESEND_API_KEY` não estiver configurado (dev)
  - [x] Validar que `EMAIL_FROM` está configurado antes de enviar

### 13.3 Estrutura do Email

- [x] Definir template HTML do email de convite:
  - [x] Cabeçalho com nome da clínica
  - [x] Mensagem de boas-vindas personalizada
  - [x] Link para acessar o aplicativo (`APP_URL`)
  - [x] Instruções claras (login ou criar conta)
  - [x] Rodapé com informações da clínica
  - [x] Estilo básico (CSS inline ou simples)
- [x] Considerar versão texto simples (plain text) como fallback:
  - [x] Versão texto criada manualmente para melhor controle
  - [x] Ambas versões (HTML e texto) são enviadas ao Resend

### 13.4 Configuração do Docker Compose

- [x] Atualizar `docker-compose.yml`:
  - [x] Adicionar variáveis de ambiente no serviço `api`:
    - [x] `RESEND_API_KEY` (placeholder vazio para configurar)
    - [x] `EMAIL_FROM` (ex: `noreply@turna.com` ou configurável)
    - [x] `APP_URL` (URL do aplicativo)
  - [x] Adicionar variáveis no serviço `worker` (mesmas variáveis para consistência)
- [ ] Documentar no README ou `.env.example`:
  - [ ] Como obter API key do Resend
  - [ ] Como configurar domínio verificado
  - [ ] Exemplo de valores para desenvolvimento

### 13.5 Tratamento de Erros e Logging

- [x] Implementar tratamento robusto de erros:
  - [x] Capturar exceções do Resend (Exception genérica com sanitização de API key)
  - [x] Logar erros detalhados (sem expor API key - sanitização implementada)
  - [x] Retornar tupla `(bool, str)` com mensagem de erro específica (mantém compatibilidade)
  - [x] Não quebrar o fluxo de criação/edição do member se email falhar (já implementado no endpoint)
  - [x] Mensagens de erro específicas e úteis (ex: domínio não verificado, API key inválida, etc.)
- [x] Melhorar logging:
  - [x] Logar quando email for enviado com sucesso (com Resend ID, sem dados sensíveis)
  - [x] Logar tentativas de envio e resultados
  - [x] Logar quando Resend não estiver configurado (modo dev com fallback)
  - [x] Logs detalhados em todo o fluxo (frontend, handler Next.js, backend, email service)

### 13.6 Documentação

- [x] Atualizar `STACK.md`:
  - [x] Adicionar informações sobre Resend
- [x] Atualizar `CHECKLIST.md` (esta seção):
  - [x] Marcar itens concluídos conforme implementação

### 13.8 Integração Frontend

- [x] Exibir mensagens de sucesso/erro no ActionBar:
  - [x] Mensagens de sucesso exibidas (verde)
  - [x] Mensagens de erro exibidas (vermelho)
  - [x] Mesmo layout das mensagens de erro (sem bordas, apenas texto)
  - [x] Mensagens não desaparecem automaticamente
- [x] Integração com formulário de member:
  - [x] Checkbox "Enviar convite" funcional
  - [x] Envio automático após salvar/editar member
  - [x] Tratamento de erros sem quebrar fluxo de salvamento

### 13.9 Melhorias Adicionais Implementadas

- [x] Mensagens de erro específicas e úteis:
  - [x] Detecção de erro de domínio não verificado com extração do domínio
  - [x] Mensagens específicas para diferentes tipos de erro (API key inválida, domínio não verificado, limite excedido, etc.)
  - [x] Mensagens traduzidas e amigáveis em português
  - [x] Função retorna tupla `(bool, str)` com mensagem de erro específica
- [x] Logs detalhados em todo o fluxo:
  - [x] Logs no frontend (UI) com prefixo [INVITE-UI]
  - [x] Logs no handler Next.js com prefixo [INVITE-FRONTEND]
  - [x] Logs no backend (endpoint) com prefixo [INVITE]
  - [x] Logs no serviço de email com prefixo [EMAIL]
- [x] Validação de segurança:
  - [x] Tratamento de código antigo em cache (validação de tipo de retorno)
  - [x] Sanitização de API key nos logs
  - [x] Retorno de tupla `(bool, str)` para mensagens de erro específicas

### 13.10 Melhorias Futuras (Opcional)

- [ ] Templates do Resend:
  - [ ] Criar template no dashboard do Resend
  - [ ] Usar template em vez de HTML inline (quando feature sair de beta)
- [ ] Email HTML mais elaborado:
  - [ ] Design responsivo
  - [ ] Imagens/branding da clínica
  - [ ] Links de tracking (se necessário)
- [ ] Outros tipos de email:
  - [ ] Email de boas-vindas ao criar conta
  - [ ] Email de notificação de escala publicada
  - [ ] Email de recuperação de senha (se implementar)

