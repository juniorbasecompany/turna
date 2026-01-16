# Checklist de Implementação - Stack Fase 1

Este checklist organiza as tarefas necessárias para aderir completamente à stack definida em `stack.md`, seguindo uma abordagem **incremental e testável** em cada etapa.

---

## Status Geral

- **Infraestrutura**: Docker Compose configurado (PostgreSQL na porta 5433, Redis, MinIO)
- **Dependências**: Bibliotecas instaladas (FastAPI, SQLModel, Arq, psycopg2-binary, etc.)
- **Endpoint básico**: `/health` funcionando
- **Etapa 1**: ✅ Concluída - Modelos Tenant, User, Job criados e migrados
- **Implementação**: ~25% - Fundações do banco de dados e modelos básicos implementados

---

## Caminho Mínimo Incremental

Cada etapa abaixo entrega algo **visível e testável** via Swagger (`/docs`) ou curl, sem quebrar o que já funciona.

### Etapa 0: Base (Já feito)
- [x] Docker Compose sobe sem erros
- [x] `/health` retorna `{"status": "ok"}`
- [x] Dependências instaladas

### Etapa 1: DB + 3 tabelas básicas
- [x] Modelos: Tenant, User, Job
- [x] Alembic configurado e migração aplicada
- [x] Endpoint `POST /tenant` (criar tenant simples)
- [x] Testar: criar tenant via `/docs`, verificar no banco

### Etapa 2: OAuth + JWT + `/me`
- [x] OAuth Google integrado
- [x] JWT com `tenant_id` no token
- [x] Endpoint `GET /me` retorna User do banco
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
    - [ ] `tenant_id: int` (ForeignKey para Tenant, nullable=False) - *Nota: BaseModel não tem tenant_id, apenas modelos filhos*
- [x] Criar `app/model/tenant.py`:
  - [x] Modelo `Tenant` (id, name, slug, created_at, updated_at)
  - [x] Sem `tenant_id` (é a raiz do multi-tenant)
- [x] Criar `app/model/user.py`:
  - [x] Modelo `User` (id, email, name, role, tenant_id FK, auth_provider, created_at, updated_at)
  - [x] Índice único em `(email, tenant_id)`
  - [ ] **Nota**: Será corrigido na seção 2.3 - remover `tenant_id` e criar tabela `membership` (Membership)
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
- [x] Criar migração inicial: `alembic revision --autogenerate -m "Initial schema - Tenant, User, Job"`
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
  - [ ] **Nota**: Será ajustado na seção 2.3 para usar role do Membership
- [x] Criar `app/auth/dependencies.py`:
  - [x] Dependency `get_current_user(session, token)` retornando User
  - [x] Dependency `require_role(role: str)` para verificar permissões
  - [x] Dependency `get_current_tenant(session, token)` retornando Tenant
  - [ ] **Nota**: Será ajustado na seção 2.3 para usar Membership em vez de User.tenant_id
- [x] Migrar lógica do `login.py` para `app/auth/oauth.py`:
  - [x] Função `verify_google_token(token)` com clock_skew_in_seconds
  - [x] Endpoint `POST /auth/google` (adaptar do login.py)
  - [x] Endpoint `POST /auth/google/register` (adaptar do login.py)
  - [x] Integrar com modelos User/Tenant (criar usuário no banco, não JSON)
  - [ ] **Nota**: Será ajustado na seção 2.3 para criar User sem tenant_id e usar Memberships
- [x] Atualizar `app/api/routes.py`:
  - [x] Importar router de autenticação
  - [x] Incluir rotas de auth
  - [x] Endpoint `GET /me` na raiz
- [x] Testar autenticação:
  - [x] Login com Google retorna JWT válido
  - [x] JWT contém `tenant_id`
  - [x] `GET /me` retorna dados do usuário do banco
  - [ ] **Nota**: Testes serão atualizados na seção 2.3 para validar modelo correto

### 2.2 Multi-Tenant Enforcement
- [ ] Criar `app/services/tenant_service.py`:
  - [ ] Função `get_tenant_by_id(tenant_id)`
  - [ ] Função `create_tenant(name, slug)`
- [ ] Criar `app/middleware/tenant.py`:
  - [ ] Middleware que extrai `tenant_id` do JWT e adiciona ao `request.state`
  - [ ] Validar que tenant existe no banco
- [ ] Aplicar middleware em `app/main.py`
- [ ] Criar helper `get_tenant_id(request)` para endpoints
- [ ] Documentar padrão: todas as queries devem usar `tenant_id` do `request.state`

### 2.3 Correção do Modelo Multi-Tenant (Account sem tenant_id)

**Contexto**: O modelo atual tem `user.tenant_id`, mas o correto é:
- **Tenant** = clínica (entidade organizacional)
- **User** = pessoa física (login Google, único global por email)
- **Membership** = vínculo User↔Tenant com role e status (um usuário pode estar em múltiplos tenants)

**Objetivo**: Migrar para modelo correto sem quebrar o que já funciona, mantendo abordagem incremental e testável.

#### 2.3.1 Ajuste do Modelo de Dados

- [x] Criar modelo `app/model/membership.py`:
  - [x] Modelo `Membership` com:
    - [x] `id: int` (PK)
    - [x] `tenant_id: int` (FK para Tenant, não nullable)
    - [x] `account_id: int` (FK para User, não nullable)
    - [x] `role: str` (ADMIN/USER no MVP) - usar Enum
    - [x] `status: str` (PENDING, ACTIVE, REJECTED, REMOVED) - usar Enum
    - [x] `created_at: datetime`
    - [x] `updated_at: datetime`
    - [x] UniqueConstraint em `(tenant_id, account_id)` - um usuário só pode ter um membership por tenant
  - [x] Índices: `tenant_id`, `account_id`, `status`
  - [ ] Relationships SQLModel (opcional, se necessário para queries)
- [x] Criar migração Alembic `add_membership_table`:
  - [x] Criar tabela `membership`
  - [x] Adicionar constraints e índices
  - [x] **NÃO remover** `user.tenant_id` ainda (fazer depois)
- [x] Atualizar `app/model/user.py`:
  - [x] Remover constraint único `(email, tenant_id)`
  - [x] Adicionar constraint único em `email` apenas (email único global)
  - [x] Manter `tenant_id` temporariamente (será removido depois)
  - [x] Adicionar índice único em `email`
- [x] Criar migração Alembic `make_user_email_unique`:
  - [x] Remover constraint `uq_user_email_tenant`
  - [x] Adicionar constraint único em `email`
  - [x] **Como testar**: Verificar que não é possível criar dois usuários com mesmo email

#### 2.3.2 Migração de Dados Existentes

- [x] Criar script de migração `script_migrate_to_memberships.py`:
  - [x] Ler todos os usuários existentes (`user` com `tenant_id`)
  - [x] Para cada usuário:
    - [x] Criar `Membership` com:
      - [x] `tenant_id` = `user.tenant_id`
      - [x] `account_id` = `user.id`
      - [x] `role` = `user.role` (ou ADMIN se for admin)
      - [x] `status` = ACTIVE
      - [x] `created_at` = `user.created_at`
      - [x] `updated_at` = `user.updated_at`
  - [x] Validar que todos os usuários foram migrados (contagem)
  - [x] **Como testar**: Executar script, verificar que cada user tem membership ACTIVE correspondente
- [x] Criar migração Alembic `migrate_existing_account_to_memberships`:
  - [x] Executar lógica de migração via SQL ou Python (usar `alembic.op.execute()` se necessário)
  - [x] Garantir que nenhum usuário fica sem membership
  - [x] **Como testar**: Verificar no banco que todos os account têm pelo menos 1 membership ACTIVE

#### 2.3.3 Ajuste de Fluxos de Autenticação e Entrada

- [x] Atualizar `app/auth/oauth.py` (ou `app/api/auth.py`):
  - [x] Após login Google, identificar User por email (criar se não existir, SEM tenant_id)
  - [x] Criar função `get_user_memberships(session, account_id)`:
    - [x] Retornar memberships com status ACTIVE (tenants disponíveis)
    - [x] Retornar memberships com status PENDING (convites pendentes)
  - [x] Criar função `get_active_tenant_for_user(session, account_id)`:
    - [x] Se 0 ACTIVE: retornar None (usuário precisa criar tenant ou aceitar convite)
    - [x] Se 1 ACTIVE: retornar esse tenant (seleção automática)
    - [x] Se >1 ACTIVE: retornar None (exigir seleção)
- [x] Atualizar endpoint `POST /auth/google`:
  - [x] Buscar User por email (sem filtro de tenant)
  - [x] Carregar memberships do usuário
  - [x] Se não tiver nenhum ACTIVE: retornar erro ou permitir criar tenant
  - [x] Se tiver 1 ACTIVE: emitir JWT com esse tenant_id
  - [x] Se tiver >1 ACTIVE: retornar lista de tenants disponíveis (não emitir JWT ainda)
- [x] Atualizar endpoint `POST /auth/google/register`:
  - [x] Criar User SEM tenant_id (ou com tenant_id NULL temporariamente)
  - [x] Se for primeiro usuário do sistema: criar Tenant + Membership ADMIN ACTIVE
  - [ ] Caso contrário: criar Membership PENDING (aguardar convite) ou permitir criar tenant
  - [x] Emitir JWT apenas se tiver membership ACTIVE
- [x] Criar endpoint `POST /auth/select-tenant`:
  - [ ] Receber `tenant_id` no body
  - [ ] Validar que User tem membership ACTIVE nesse tenant
  - [ ] Emitir novo JWT com `tenant_id` escolhido + `role` do membership
  - [ ] **Como testar**: Login → selecionar tenant → verificar JWT contém tenant_id correto
- [x] Criar endpoint `GET /auth/tenant/list`:
  - [x] Retornar lista de tenants disponíveis (memberships ACTIVE do usuário)
  - [x] Retornar lista de convites pendentes (memberships PENDING)
  - [x] **Como testar**: Chamar endpoint após login, verificar lista de tenants e convites

#### 2.3.4 Implementação de Convites

- [x] Criar endpoint `POST /tenant/{tenant_id}/invite`:
  - [x] Requer role ADMIN no tenant
  - [x] Receber `email` no body
  - [x] Buscar User por email (criar se não existir, SEM tenant_id)
  - [x] Verificar se já existe membership (não criar duplicado)
  - [x] Criar `Membership` com:
    - [x] `tenant_id` = tenant do admin
    - [x] `account_id` = usuário encontrado/criado
    - [x] `role` = user/admin (MVP)
    - [x] `status` = PENDING
  - [x] Retornar `{membership_id, email, status: "PENDING"}`
  - [ ] **Como testar**: Admin convida email → verificar membership PENDING criado
- [x] Criar endpoint `GET /auth/invites`:
  - [x] Retornar lista de memberships PENDING do usuário autenticado
  - [x] Incluir informações do tenant (name, slug)
  - [ ] **Como testar**: Listar convites pendentes após login
- [x] Criar endpoint `POST /auth/invites/{membership_id}/accept`:
  - [x] Validar que membership pertence ao usuário autenticado
  - [x] Validar que status é PENDING
  - [x] Atualizar `status` para ACTIVE
  - [ ] Opcional: emitir novo JWT com tenant_id do membership aceito
  - [x] Retornar `{membership_id, tenant_id, status: "ACTIVE"}`
  - [ ] **Como testar**: Aceitar convite → verificar status ACTIVE → poder selecionar tenant
- [x] Criar endpoint `POST /auth/invites/{membership_id}/reject`:
  - [x] Validar que membership pertence ao usuário autenticado
  - [x] Validar que status é PENDING
  - [x] Atualizar `status` para REJECTED (não deletar)
  - [x] Retornar `{membership_id, status: "REJECTED"}`
  - [ ] **Como testar**: Recusar convite → verificar status REJECTED (não deletado)
- [ ] Criar endpoint `POST /tenant` (criar clínica):
  - [ ] Permitir se usuário não tem nenhum membership ACTIVE (primeiro tenant)
  - [ ] Criar Tenant
  - [ ] Criar Membership ADMIN ACTIVE para o usuário
  - [ ] Emitir JWT com novo tenant_id
  - [ ] **Como testar**: Criar tenant → verificar membership ADMIN ACTIVE criado

#### 2.3.5 Ajuste de JWT e Enforcement

- [x] Atualizar `app/auth/jwt.py`:
  - [x] Manter `create_access_token(account_id, tenant_id, role, email, name)`
  - [x] **Importante**: `role` agora vem do Membership, não do User
  - [x] Adicionar claim opcional `membership_id` (se necessário para auditoria)
- [x] Atualizar `app/auth/dependencies.py`:
  - [x] Modificar `get_current_user()`:
    - [x] Extrair `account_id` do JWT (sem mudança)
    - [x] Buscar User por `account_id` (sem filtro de tenant)
  - [x] Criar nova dependency `get_current_membership()`:
    - [x] Extrair `tenant_id` e `account_id` do JWT
    - [x] Buscar `Membership` com `tenant_id` + `account_id` + `status=ACTIVE`
    - [x] Retornar objeto Membership (ou erro se não existir)
  - [x] Modificar `get_current_tenant()`:
    - [x] Usar `get_current_membership()` para validar acesso
    - [x] Buscar Tenant por `tenant_id` do JWT
  - [x] Modificar `require_role(required_role)`:
    - [x] Usar `get_current_membership()` em vez de `get_current_user()`
    - [x] Verificar `membership.role == required_role`
- [x] Atualizar `app/api/auth.py`:
  - [x] Ao emitir JWT, buscar role do Membership (não do User)
  - [x] Garantir que JWT só é emitido se membership existe e está ACTIVE
- [x] Criar endpoint `POST /auth/switch-tenant`:
  - [x] Receber `tenant_id` no body
  - [x] Validar que User tem membership ACTIVE nesse tenant
  - [x] Buscar role do membership
  - [x] Emitir novo JWT com `tenant_id` + `role` atualizados
  - [x] Retornar novo token
  - [x] **Como testar**: Trocar de tenant → verificar JWT atualizado → chamar `/me` com novo token
- [x] Garantir que TODAS as queries continuam filtradas por `tenant_id`:
  - [x] Revisar todos os endpoints existentes
  - [x] Validar que usam `tenant_id` do JWT (via `get_current_tenant()` ou `request.state`)
  - [ ] Documentar padrão: sempre filtrar por `tenant_id` do JWT, nunca confiar em parâmetros do body

#### 2.3.6 Remoção Final de tenant_id de Account

- [ ] Criar migração Alembic `remove_tenant_id_from_account`:
  - [ ] Validar que todos os account têm pelo menos 1 membership (não pode ter user órfão)
  - [ ] Remover coluna `tenant_id` de `user`
  - [ ] Remover índice `ix_user_tenant_id`
  - [ ] Remover foreign key constraint de `user.tenant_id`
- [ ] Atualizar `app/model/user.py`:
  - [ ] Remover campo `tenant_id`
  - [ ] Remover relacionamento direto com Tenant (se existir)
- [ ] Atualizar código que ainda referencia `user.tenant_id`:
  - [ ] Buscar todas as referências a `user.tenant_id` no código
  - [ ] Substituir por lógica que busca membership ACTIVE (ou usar `get_current_membership()`)
  - [ ] **Como testar**: Executar testes completos, verificar que nenhum código quebra
- [x] Criar script de validação `script_validate_memberships.py`:
  - [x] Verificar que todos os account têm pelo menos 1 membership
  - [ ] Verificar que não há memberships com account_id ou tenant_id inválidos
  - [x] Verificar que não há duplicatas (tenant_id, account_id)
  - [x] **Como testar**: Executar script antes e depois da remoção de tenant_id

#### 2.3.7 Testes e Validação da Migração

- [ ] Testar fluxo completo de login:
  - [ ] Usuário novo cria tenant → membership ADMIN ACTIVE criado
  - [ ] Usuário existente com 1 tenant → login automático
  - [ ] Usuário existente com múltiplos tenants → precisa selecionar
  - [ ] **Como testar**: Via Swagger, testar cada cenário
- [ ] Testar fluxo de convites:
  - [ ] Admin convida email → membership PENDING criado
  - [ ] Usuário lista convites → vê convite pendente
  - [ ] Usuário aceita convite → membership ACTIVE
  - [ ] Usuário pode trocar para novo tenant
  - [ ] **Como testar**: Via Swagger, criar dois usuários, testar convite completo
- [ ] Testar multi-tenant isolation:
  - [ ] Usuário em Tenant A não vê dados de Tenant B
  - [ ] Trocar tenant → ver dados do novo tenant
  - [ ] **Como testar**: Criar dados em dois tenants, trocar entre eles, verificar isolamento
- [ ] Testar que endpoints existentes continuam funcionando:
  - [ ] `GET /me` retorna dados corretos
  - [ ] Endpoints de Job respeitam tenant_id do JWT
  - [ ] Endpoints futuros de File/Schedule respeitam tenant_id
  - [ ] **Como testar**: Executar suite de testes via Swagger

#### 2.3.8 Rollback e Segurança

- [ ] Documentar plano de rollback:
  - [ ] Manter migração `remove_tenant_id_from_account` reversível (se possível)
  - [ ] Se necessário rollback: recriar coluna `tenant_id` e popular com membership ACTIVE principal
- [ ] Adicionar validações de segurança:
  - [ ] Não permitir criar membership duplicado (tenant_id, account_id)
  - [ ] Não permitir deletar último membership ACTIVE de um user (ou exigir transferência de admin)
  - [ ] Validar que role existe no enum
  - [ ] Validar que status existe no enum
- [ ] Adicionar logs/auditoria:
  - [ ] Logar criação de memberships (para rastrear convites)
  - [ ] Logar mudanças de status (aceitar/rejeitar convites)
  - [ ] Logar troca de tenant (switch-tenant)

**Notas importantes**:
- Esta correção é **incremental**: cada sub-etapa pode ser testada isoladamente
- Manter `user.tenant_id` temporariamente durante transição permite rollback seguro
- Não quebrar endpoints existentes: ajustar gradualmente, manter compatibilidade durante migração
- JWT continua contendo `tenant_id` e `role`, mas agora `role` vem do Membership, não do User
- Todos os testes devem ser feitos via Swagger (`/docs`) ou curl após cada etapa

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
- [ ] Criar `app/api/tenant.py`:
  - [ ] `POST /tenant` (criar tenant - apenas admin ou primeiro usuário)
  - [ ] `GET /tenant/me` (tenant atual do usuário)

### 5.2 Endpoints de Schedule
- [x] Criar `app/api/schedule.py`:
  - [ ] `GET /schedule/list` (listar ScheduleVersions - filtrado por tenant)
  - [ ] `POST /schedule` (criar ScheduleVersion - filtrado por tenant)
  - [ ] `GET /schedule/{id}` (detalhes - validar tenant)
  - [x] `POST /schedule/{id}/publish` (publicar versão - validar tenant)
  - [x] `GET /schedule/{id}/pdf` (download PDF - validar tenant)
  - [x] Retornar URL presignada do S3

### 5.3 Endpoint de Job
- [ ] Atualizar `app/api/job.py`:
  - [ ] `GET /job/list` (listar jobs do tenant)
  - [ ] `GET /job/{job_id}` (detalhes - validar tenant)

### 5.4 Validações e Segurança
- [ ] Garantir que TODOS os endpoints validam tenant_id:
  - [ ] Extrair de JWT
  - [ ] Validar que tenant existe
  - [ ] Filtrar queries por tenant_id
- [ ] Garantir que endpoints de criação/atualização não permitem alterar tenant_id
- [ ] Documentar API com OpenAPI/Swagger (FastAPI já faz isso)

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
- [ ] Criar script de migração de dados se necessário:
  - [ ] Criar tenant padrão
  - [ ] Associar usuários existentes a tenant

---

## FASE 7: Testes e Validação

### 7.1 Testes Básicos
- [ ] Testar fluxo completo via `/docs`:
  1. Criar tenant
  2. Login (obter JWT)
  3. Upload arquivo
  4. Job de extração processa
  5. Criar ScheduleVersion
  6. Job de geração processa
  7. Publicar escala
  8. Download PDF
- [ ] Testar multi-tenant isolation (usuário de tenant A não vê dados de tenant B)
- [ ] Testar que jobs respeitam tenant_id

### 7.2 Validação de Princípios
- [ ] Princípio 1: Requests HTTP nunca rodam solver/IA (sempre criam Job)
- [ ] Princípio 2: ScheduleVersion imutável, publicação separada
- [ ] Princípio 3: Multi-tenant por tenant_id em todas as tabelas
- [ ] Princípio 4: Storage fora do banco (S3, banco só metadados)

---

## FASE 8: Frontend e Mobile (Futuro)

### 8.1 Frontend Web (Next.js)
- [ ] Criar projeto Next.js
- [ ] Configurar autenticação (OAuth Google)
- [ ] Páginas: Login, Dashboard, Importação, Escalas
- [ ] Integração com API

### 8.2 Mobile (React Native)
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
5. **Futuro**: Fase 8 (frontend/mobile)

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

- [x] 3 modelos SQLModel criados e migrados (Tenant, User, Job) - *Fase 1 concluída*
- [x] Modelo Membership criado e migrado (tabela `membership`) - *Seção 2.3*
- [ ] Modelo User corrigido (sem tenant_id, email único global) - *Seção 2.3*
- [ ] Modelos File e ScheduleVersion (próximas etapas)
- [x] Autenticação funcionando com tenant_id no JWT (role do Membership) - *Seção 2.3*
- [ ] Fluxos de convites e seleção de tenant funcionando - *Seção 2.3*
- [x] Multi-tenant enforcement ativo em todos os endpoints (via Membership)
- [ ] Storage S3/MinIO funcionando (upload/download)
- [ ] Jobs Arq processando corretamente (PING, EXTRACT, GENERATE)
- [ ] API endpoints seguindo princípios arquiteturais
- [ ] Código legado ainda funciona (ou foi migrado)
- [ ] Docker Compose sobe sem erros
- [x] Migrações Alembic aplicam sem erros (incluindo migrações de correção multi-tenant)
- [ ] Fluxo completo testável via `/docs` (login → selecionar tenant → usar API)

---

**Última atualização**: Refatorado para abordagem incremental e testável.
