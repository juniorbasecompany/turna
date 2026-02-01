# Stack do Projeto

Documento que descreve as tecnologias, modelos e princípios de arquitetura do projeto. Indica o que está em uso e o que está planejado para o futuro.

## Estrutura do repositório

- **Monorepo**: um único repositório `turna`.
- **Backend**: pasta `backend/` (API FastAPI, worker Arq, modelos, Alembic, demand, output, strategy). Docker: `context: ./backend`, volume `./backend:/app`. Variáveis em `backend/.env`.
- **Frontend**: pasta `frontend/` (Next.js). Variáveis em `frontend/.env.local`.
- **Orquestração**: `docker-compose.yml` na raiz; comandos Docker e Alembic a partir da raiz.

## Objetivo

MVP SaaS multi-tenant para clínicas gerarem escalas e relatórios (PDF):

- **Web (admin)**: cadastros, importação, geração e publicação de escalas, relatórios. **Implementado.**
- **Mobile (profissionais)**: consulta de escalas publicadas e interações simples. **Planejado.**

## Tecnologias

### Backend (implementado)
- Python 3.11+, FastAPI, Pydantic v2, Uvicorn
- PostgreSQL 16, SQLModel, Alembic
- Redis 7, Arq (jobs: PING, EXTRACT_DEMAND, GENERATE_SCHEDULE, GENERATE_THUMBNAIL)
- OpenAI (extração de demandas a partir de PDF/JPEG/PNG)
- S3-compatível (MinIO em dev), Pillow (thumbnails)
- ReportLab (PDF de escalas); pypdfium2, pdfplumber, PyMuPDF (leitura de PDFs)
- Resend (emails transacionais – convites)

### Backend (planejado)
- Google OR-Tools (CP-SAT) como solver alternativo ao Greedy
- Interface formal para trocar provedor de IA

### Frontend (implementado)
- Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS

### Frontend / Mobile (planejado)
- React Native para app de profissionais

### Autenticação (implementado)
- OAuth 2.0 (Google), JWT (claims: account_id, tenant_id). Dados de sessão obtidos via endpoints.

### Infra (implementado)
- Docker, Docker Compose. Produção inicial: VPS simples (1 servidor). **Planejado:** evoluir conforme necessidade.

## Modelos de dados

### Entidades (implementadas)
- **Tenant**: clínica (entidade organizacional).
- **Account**: pessoa física (login Google, email único global, sem tenant_id). Dados privados.
- **Member**: vínculo Account↔Tenant com role e status. Dados públicos na clínica.
- **Hospital**: hospital por tenant (nome, prompt para extração IA, cor).
- **File**: metadados de arquivos no S3/MinIO; pertence a um Hospital.
- **Demand**: demanda cirúrgica (extraída ou manual); inclui estado da escala (schedule_status, schedule_result_data, pdf_file_id, generated_at, published_at). Uma única tabela para demanda e escala; período da geração fica em `job.input_data`.
- **Job**: jobs assíncronos (Arq). Para GENERATE_SCHEDULE, `result_data` guarda apenas mínimo (ex.: allocation_count).
- **AuditLog**: eventos (member_invited, member_status_changed, tenant_switched).

### Regras de modelo
- **Demand**: `start_time` e `end_time` são início e fim da cirurgia. Não há `period_start_at`/`period_end_at` na Demand.
- **Profissionais para escala**: carregados de `member` do tenant (`member.attribute`: sequence, can_peds, vacation); apenas members ACTIVE.

## Formatos

- **Entrada**: PDF, JPEG, PNG, XLSX, XLS, CSV
- **Saída**: PDF

## Princípios de arquitetura

1. Requests HTTP não executam solver nem IA: criam Job e retornam `job_id`.
2. Estado da escala fica na Demand; publicação é passo separado (endpoint de publish gera PDF e atualiza Demand).
3. Multi-tenant por `tenant_id` em todas as tabelas; validação via `get_current_member()`.
4. Arquivos em object storage; banco guarda apenas metadados/URLs.
5. Separação Account (privado) vs Member (público).
