# Checklist de Implementação

Este checklist resume o que **está implementado** e o que **está pendente ou planejado** no projeto, alinhado a `STACK.md`, `DIRECTIVES.md` e `SECURITY.md`.

## Status geral

- **Estrutura**: Backend em `backend/` (API FastAPI, worker Arq, Alembic, demand, output, strategy). Frontend em `frontend/`. `docker-compose.yml` na raiz; build context `./backend`, volume `./backend:/app`.
- **Infraestrutura**: Docker Compose (PostgreSQL 5433, Redis, MinIO). Endpoint `/health`.
- **Modelos**: Tenant, Account, Member, Job, File, AuditLog, Hospital, Demand. Demand inclui estado da escala (schedule_status, schedule_result_data, pdf_file_id, generated_at, published_at).
- **Autenticação**: OAuth Google, JWT, Member, convites, isolamento multi-tenant.
- **Storage**: S3/MinIO; upload/download; File com hospital_id; upload de PDF da escala por Demand.
- **Jobs**: Arq worker; PING, EXTRACT_DEMAND, GENERATE_SCHEDULE. Worker atualiza Demand com resultado da alocação; `Job.result_data` mínimo para GENERATE_SCHEDULE.
- **API**: Endpoints de tenant, member, account, hospital, file, demand, job; rotas de escala (`/schedule/*`) operando sobre Demand (id = demand_id). Validação de tenant em todos os endpoints.
- **Frontend**: Next.js (App Router), login OAuth, seleção de tenant, dashboard, páginas de hospitais, clínicas, associados, arquivos, demandas, jobs. Menu lateral; `protectedFetch()`; CORS configurado. Resend para convites.
- **Pendente**: Página de escalas (listagem e detalhe); alguns itens opcionais (toasts, Docker frontend, CP-SAT, etc.).

---

## Implementado

### Infra e base
- Docker Compose sobe sem erros. Dependências instaladas. Alembic configurado; migrações aplicadas.
- Modelos: Tenant, Account, Member, Job, File, AuditLog, Hospital, Demand. Demand com campos de escala; sem tabela Schedule separada.
- DB: session, engine, `get_session()`; migrations para todos os modelos.

### Autenticação e multi-tenant
- OAuth Google, JWT (account_id, tenant_id, role do Member). Endpoints: `/auth/google`, `/auth/google/register`, `/auth/google/select-tenant`, `/auth/google/create-tenant`, `/auth/switch-tenant`, `/auth/tenant/list`, `/auth/invites`, accept/reject. `GET /me`.
- Middleware extrai tenant_id do JWT. Validação real em `get_current_member()`. Convites e member PENDING/ACTIVE; auditoria em audit_log.
- Separação Account (privado) vs Member (público); painel de member sem dados do Account; convite por email com Resend.

### Storage
- S3/MinIO; StorageService; upload de arquivo (File com hospital_id); upload de PDF da escala (`upload_demand_pdf`). Presigned URL.

### Jobs (Arq)
- PING, EXTRACT_DEMAND (OpenAI, resultado em Job.result_data), GENERATE_SCHEDULE (solver greedy; atualiza Demand; result_data mínimo). Endpoints: `/job/ping`, `/job/extract`, `/schedule/generate`, `/schedule/generate-from-demands`. Job.started_at; requeue (admin). Listagem e detalhe de job.

### API
- Tenant: POST, GET list, GET me, PUT, DELETE. Hospital default na criação do tenant.
- Member: POST, GET list, GET id, PUT, DELETE, invite. Account: POST, GET list, PUT, DELETE (admin).
- Hospital: POST, GET list, GET id, PUT, DELETE (validação de arquivos).
- File: upload (hospital_id obrigatório), list (filtros, paginação, job_status), get, download, thumbnail, delete.
- Demand: POST, GET list, GET id, PUT, DELETE. Escala: GET/POST/PUT/DELETE `/schedule/*` (id = demand_id); publish; PDF. Geração em lote cria Job; worker atualiza Demand(s).
- Validação de tenant_id em todos os endpoints; padrões em SECURITY.md.

### Frontend
- Login OAuth, seleção de tenant, criação automática de clínica. Layout protegido; Header (tenant, menu usuário). Dashboard (totais, links). Páginas: Hospitais, Clínicas, Associados, Arquivos, Demandas, Jobs. Sidebar (ordem e admin-only). Upload de arquivos (hospital obrigatório); “Ler conteúdo” (EXTRACT_DEMAND); polling de status; filtro por período e hospital; paginação. CRUD de demandas, members, tenants, hospitais. Convite com Resend; feedback no ActionBar. `protectedFetch()`; tratamento de 401 sem redirecionar indevidamente em F5. CORS no backend.

### Integração
- Solver greedy integrado; geração de PDF (ReportLab; `render_multi_day_pdf_bytes`); publicação gera PDF e faz upload; download de PDF da escala. Demand com schedule_result_data; fragmentos por Demand.job_id.

---

## Pendente

- **Página de escalas**: listagem (`GET /schedule/list`), paginação, filtros por status, ordenação; detalhe (`GET /schedule/{id}`), ações Publicar e Download PDF, loading e erros.
- **Solver CP-SAT**: integrar `strategy/cd_sat/solve.py` no worker (hoje apenas greedy).
- **Serviço de escala**: (opcional) `app/services/schedule_service.py` com função `generate_schedule(demand_list, member_list, allocation_mode)`; hoje chamado direto no worker.
- **UX**: toasts de sucesso/erro (opcional; hoje ActionBar).
- **Docker frontend**: (opcional) Dockerfile e serviço no docker-compose para frontend.
- **Documentação**: conceito de hospital e prompt como contrato de extração; README/.env.example para Resend.

---

## Futuro (planejado)

- **Mobile**: React Native; autenticação OAuth; telas de login, lista de escalas, detalhe de escala; integração com API.
- **AI**: abstração para trocar provedor de IA (interface formal).
- **Painel de Account**: regras de acesso restritas (apenas o próprio usuário vê seus dados).
- **Emails**: templates Resend; email de notificação de escala publicada; outros tipos conforme necessidade.

---

## Validação final

Antes de considerar uma fase completa, verificar:

- [ ] Modelos criados e migrados; Demand com estado da escala.
- [ ] Autenticação com tenant_id no JWT; convites e seleção de tenant ok.
- [ ] Multi-tenant ativo em todos os endpoints (get_current_member).
- [ ] Storage S3/MinIO ok; jobs PING, EXTRACT_DEMAND, GENERATE_SCHEDULE ok.
- [ ] Padrões de segurança seguidos (SECURITY.md).
- [ ] Docker Compose sobe; migrações Alembic aplicam.

---

## Notas

- **Boas práticas**: validar tenant_id em queries; criar Job antes de enfileirar; usar StorageService para arquivos; não expor credenciais.
- **Job.result_data**: EXTRACT_DEMAND persiste demandas em JSON; GENERATE_SCHEDULE persiste apenas mínimo (ex.: allocation_count).
- **Demand**: `start_time` e `end_time` são início/fim da cirurgia; período da geração em `job.input_data`. Profissionais da escala vêm de `member.attribute` (ACTIVE).
