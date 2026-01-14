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
- [x] Endpoint `POST /tenants` (criar tenant simples)
- [x] Testar: criar tenant via `/docs`, verificar no banco

### Etapa 2: OAuth + JWT + `/me`
- [ ] OAuth Google integrado
- [ ] JWT com `tenant_id` no token
- [ ] Endpoint `GET /me` retorna User do banco
- [ ] Testar: login via Google, verificar JWT, chamar `/me`

### Etapa 3: Upload + File + MinIO
- [ ] Modelo File
- [ ] StorageService básico (upload/download)
- [ ] Endpoint `POST /files/upload` retorna URL/presigned
- [ ] Testar: upload arquivo, verificar MinIO e banco

### Etapa 4: Arq - Job fake primeiro
- [ ] WorkerSettings configurado
- [ ] Job `PING_JOB` (fake, só valida fila)
- [ ] Endpoint `POST /jobs/ping` cria Job e enfileira
- [ ] Testar: criar job, ver worker processar, ver status

### Etapa 5: Arq - EXTRACT_DEMANDS
- [ ] Job `EXTRACT_DEMANDS` com OpenAI (adaptar `demand/read.py`)
- [ ] Salvar resultado como JSON no `Job.result_data`
- [ ] Endpoint `POST /jobs/extract` (recebe file_id)
- [ ] Testar: upload → extract → ver resultado no Job

### Etapa 6: ScheduleVersion + GenerateSchedule
- [ ] Modelo ScheduleVersion
- [ ] Job `GENERATE_SCHEDULE` (usar código de `strategy/`)
- [ ] Salvar resultado no ScheduleVersion
- [ ] Endpoint `POST /schedules/generate`
- [ ] Testar: gerar escala, ver ScheduleVersion criado

### Etapa 7: PDF + Publicação
- [ ] Gerar PDF (adaptar `output/day.py`)
- [ ] Upload PDF para S3
- [ ] Endpoint `POST /schedules/{id}/publish`
- [ ] Endpoint `GET /schedules/{id}/pdf` (download)
- [ ] Testar: gerar → publicar → download PDF

---

## FASE 1: Fundações - Modelos e Banco de Dados

### 1.1 Modelos SQLModel (Mínimo Inicial: 5 tabelas)

**Começar simples, evoluir depois:**

- [x] Criar `app/models/__init__.py`
- [x] Criar `app/models/base.py`:
  - [x] Classe base `BaseModel` (SQLModel) com:
    - [x] `id: int` (primary key)
    - [x] `created_at: datetime`
    - [x] `updated_at: datetime`
    - [ ] `tenant_id: int` (ForeignKey para Tenant, nullable=False) - *Nota: BaseModel não tem tenant_id, apenas modelos filhos*
- [x] Criar `app/models/tenant.py`:
  - [x] Modelo `Tenant` (id, name, slug, created_at, updated_at)
  - [x] Sem `tenant_id` (é a raiz do multi-tenant)
- [x] Criar `app/models/user.py`:
  - [x] Modelo `User` (id, email, name, role, tenant_id FK, auth_provider, created_at, updated_at)
  - [x] Índice único em `(email, tenant_id)`
- [x] Criar `app/models/job.py`:
  - [x] Modelo `Job` (id, tenant_id, job_type, status, input_data JSON, result_data JSON, error_message, created_at, updated_at, completed_at)
  - [x] Enum para `job_type`: `PING`, `EXTRACT_DEMANDS`, `GENERATE_SCHEDULE`
  - [x] Enum para `status`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`
  - [x] **Nota**: `result_data` guarda Demandas como JSON inicialmente
- [ ] Criar `app/models/file.py`:
  - [ ] Modelo `File` (id, tenant_id, filename, content_type, s3_key, s3_url, file_size, uploaded_at, created_at)
- [ ] Criar `app/models/schedule_version.py`:
  - [ ] Modelo `ScheduleVersion` (id, tenant_id, name, period_start, period_end, status, version_number, job_id FK nullable, pdf_file_id FK nullable, result_data JSON, generated_at, published_at, created_at)
  - [ ] Enum para `status`: `DRAFT`, `PUBLISHED`, `ARCHIVED`
  - [ ] **Nota**: `result_data` guarda resultado da geração (alocação) como JSON

**Evolução futura (quando necessário):**
- [ ] Criar `app/models/schedule.py` (quando precisar de múltiplas versões por schedule)
- [ ] Criar `app/models/demand.py` (quando precisar queryar demandas diretamente)
- [ ] Criar `app/models/professional.py` (quando precisar CRUD de profissionais)

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
- [ ] Criar `app/auth/__init__.py`
- [ ] Criar `app/auth/jwt.py`:
  - [ ] Função `create_access_token(user_id, tenant_id, role)` retornando JWT
  - [ ] Função `verify_token(token)` retornando payload (user_id, tenant_id, role)
  - [ ] Usar `JWT_SECRET` e `JWT_ISSUER` do ambiente
  - [ ] Claims obrigatórios: `user_id`, `tenant_id`, `role`, `exp`, `iat`, `iss`
- [ ] Criar `app/auth/dependencies.py`:
  - [ ] Dependency `get_current_user(session, token)` retornando User
  - [ ] Dependency `require_role(role: str)` para verificar permissões
  - [ ] Dependency `get_current_tenant(session, token)` retornando Tenant
- [ ] Migrar lógica do `login.py` para `app/auth/oauth.py`:
  - [ ] Função `verify_google_token(token)`
  - [ ] Endpoint `POST /auth/google` (adaptar do login.py)
  - [ ] Endpoint `POST /auth/google/register` (adaptar do login.py)
  - [ ] Integrar com modelos User/Tenant (criar usuário no banco, não JSON)
- [ ] Atualizar `app/api/routes.py`:
  - [ ] Importar router de autenticação
  - [ ] Incluir rotas de auth
- [ ] Testar autenticação:
  - [ ] Login com Google retorna JWT válido
  - [ ] JWT contém `tenant_id`
  - [ ] `GET /me` retorna dados do usuário do banco

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

---

## FASE 3: Storage (S3/MinIO)

### 3.1 Configuração S3/MinIO
- [ ] Criar `app/storage/__init__.py`
- [ ] Criar `app/storage/config.py`:
  - [ ] Classe `S3Config` lendo variáveis: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_REGION`, `S3_USE_SSL`
- [ ] Criar `app/storage/client.py`:
  - [ ] Classe `S3Client` usando boto3
  - [ ] Método `upload_file(file_path, s3_key, content_type) -> s3_url`
  - [ ] Método `download_file(s3_key, local_path)`
  - [ ] Método `get_presigned_url(s3_key, expiration)`
  - [ ] Método `ensure_bucket_exists()` (criar bucket se não existir)
- [ ] Criar `app/storage/service.py`:
  - [ ] Classe `StorageService` que usa `S3Client`
  - [ ] Método `upload_imported_file(tenant_id, file, filename) -> File model`
  - [ ] Método `upload_schedule_pdf(tenant_id, schedule_version_id, pdf_bytes) -> File model`
  - [ ] Método `get_file_url(file_id, tenant_id) -> str`
  - [ ] Padrão de S3 keys: `{tenant_id}/{file_type}/{filename}`

### 3.2 Integração com Modelos
- [ ] Criar endpoint `POST /files/upload`:
  - [ ] Receber arquivo via multipart
  - [ ] Upload para S3 (StorageService)
  - [ ] Criar File no banco
  - [ ] Retornar `{file_id, s3_url, presigned_url}`
- [ ] Testar upload/download:
  - [ ] Upload de arquivo cria registro no banco e arquivo no MinIO
  - [ ] Download retorna arquivo correto
  - [ ] URLs presignadas funcionam

---

## FASE 4: Jobs Assíncronos (Arq) - Incremental

### 4.1 Configuração Básica de Workers
- [ ] Atualizar `app/workers/worker_settings.py`:
  - [ ] Classe `WorkerSettings` (herdando de `arq.worker.WorkerSettings`)
  - [ ] Configurar `redis_settings` usando `REDIS_URL`
  - [ ] Configurar `max_jobs=10` (inicial)
- [ ] Atualizar `app/workers/run.py`:
  - [ ] Usar `WorkerSettings` corretamente
  - [ ] Iniciar worker com `arq.run_worker(WorkerSettings)`

### 4.2 Job Fake (PING) - Validar Fila
- [ ] Criar `app/jobs/__init__.py`
- [ ] Criar `app/jobs/ping.py`:
  - [ ] Função `ping_job(ctx, job_id, tenant_id, message)` decorada com `@arq.job`
  - [ ] Lógica simples: atualizar Job com `result_data={"message": message}`
- [ ] Criar endpoint `POST /jobs/ping`:
  - [ ] Criar Job no banco (tipo PING, status PENDING)
  - [ ] Enfileirar job no Arq
  - [ ] Retornar `{job_id}`
- [ ] Criar endpoint `GET /jobs/{job_id}`:
  - [ ] Retornar status e resultado do Job
- [ ] Testar: criar job ping, ver worker processar, verificar status COMPLETED

### 4.3 Job EXTRACT_DEMANDS (OpenAI)
- [ ] Criar `app/jobs/extract_demands.py`:
  - [ ] Função `extract_demands_job(ctx, job_id, file_id, tenant_id)` decorada com `@arq.job`
  - [ ] Lógica:
    1. Buscar File do banco (validar tenant_id)
    2. Download do S3 para arquivo temporário
    3. Chamar `extract_demands_from_file()` (adaptar `demand/read.py`)
    4. Salvar resultado como JSON no `Job.result_data`
    5. Atualizar Job status (COMPLETED/FAILED)
- [ ] Criar `app/ai/openai_provider.py`:
  - [ ] Função `extract_demands_from_file(file_path, file_type) -> List[dict]`
  - [ ] Adaptar código de `demand/read.py` (OpenAI Vision)
  - [ ] Retornar lista de demandas como dicts
- [ ] Criar endpoint `POST /jobs/extract`:
  - [ ] Receber `file_id`
  - [ ] Criar Job (tipo EXTRACT_DEMANDS, status PENDING)
  - [ ] Enfileirar job no Arq
  - [ ] Retornar `{job_id}`
- [ ] Testar: upload arquivo → extract → ver demandas no `Job.result_data`

### 4.4 Job GENERATE_SCHEDULE
- [ ] Criar `app/jobs/generate_schedule.py`:
  - [ ] Função `generate_schedule_job(ctx, job_id, schedule_version_id, tenant_id, allocation_mode)` decorada com `@arq.job`
  - [ ] Lógica:
    1. Buscar ScheduleVersion do banco (validar tenant_id)
    2. Buscar demandas do `Job.result_data` (do job de extração anterior)
    3. Buscar profissionais (por enquanto, usar dados mock ou JSON)
    4. Chamar solver (greedy ou CP-SAT) - usar código de `strategy/`
    5. Salvar resultado no `ScheduleVersion.result_data`
    6. Gerar PDF (usar código de `output/day.py`)
    7. Upload PDF para S3
    8. Atualizar `ScheduleVersion.pdf_file_id`
    9. Atualizar Job status
- [ ] Criar endpoint `POST /schedules/generate`:
  - [ ] Receber `schedule_version_id`, `allocation_mode`
  - [ ] Criar Job (tipo GENERATE_SCHEDULE, status PENDING)
  - [ ] Enfileirar job no Arq
  - [ ] Retornar `{job_id}`
- [ ] Testar: gerar escala, ver ScheduleVersion criado, ver PDF no S3

**Nota**: Abstração completa de AI Provider (interface formal) fica para depois, quando precisar plugar outro provedor.

---

## FASE 5: API Endpoints Completos

### 5.1 Endpoints de Tenants
- [ ] Criar `app/api/tenants.py`:
  - [ ] `POST /tenants` (criar tenant - apenas admin ou primeiro usuário)
  - [ ] `GET /tenants/me` (tenant atual do usuário)

### 5.2 Endpoints de Schedules
- [ ] Criar `app/api/schedules.py`:
  - [ ] `GET /schedules` (listar ScheduleVersions - filtrado por tenant)
  - [ ] `POST /schedules` (criar ScheduleVersion - filtrado por tenant)
  - [ ] `GET /schedules/{id}` (detalhes - validar tenant)
  - [ ] `POST /schedules/{id}/publish` (publicar versão - validar tenant)
  - [ ] `GET /schedules/{id}/pdf` (download PDF - validar tenant)
  - [ ] Retornar URL presignada do S3

### 5.3 Endpoints de Jobs
- [ ] Atualizar `app/api/jobs.py`:
  - [ ] `GET /jobs` (listar jobs do tenant)
  - [ ] `GET /jobs/{job_id}` (detalhes - validar tenant)

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
- [ ] Revisar `output/day.py`:
  - [ ] Adaptar `render_pdf()` para receber dados do ScheduleVersion
  - [ ] Retornar bytes do PDF (não salvar em arquivo)
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
- [ ] Modelos File e ScheduleVersion (próximas etapas)
- [ ] Autenticação funcionando com tenant_id no JWT
- [ ] Multi-tenant enforcement ativo em todos os endpoints
- [ ] Storage S3/MinIO funcionando (upload/download)
- [ ] Jobs Arq processando corretamente (PING, EXTRACT, GENERATE)
- [ ] API endpoints seguindo princípios arquiteturais
- [ ] Código legado ainda funciona (ou foi migrado)
- [ ] Docker Compose sobe sem erros
- [ ] Migrações Alembic aplicam sem erros
- [ ] Fluxo completo testável via `/docs`

---

**Última atualização**: Refatorado para abordagem incremental e testável.
