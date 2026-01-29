# Checklist – Refatoração: Fusão Schedule em Demand

Este checklist organiza as tarefas para **unificar a tabela Schedule na tabela Demand**, eliminando a relação 1:1 e usando apenas Demand do início do fluxo até o fim do processo de cálculo que a atualiza.

**Premissas:**
- Relação Demand ↔ Schedule é 1:1; uma única tabela (Demand) é suficiente.
- **Não migrar dados**: tabela `schedule` está vazia.
- **Não persistir** o payload pesado em `Job.result_data` após o cálculo (eliminar ou deixar mínimo, ex.: `allocation_count`).
- **Não incluir** `period_start_at` / `period_end_at` na Demand; `start_time` e `end_time` da Demand são início/fim da cirurgia e não mudam; o período da geração fica só em `job.input_data` quando necessário.

---

## 1. Modelo e banco

### 1.1 Demand – novos campos (vindos de Schedule)
- [x] Adicionar em `app/model/demand.py`:
  - [x] `schedule_status`: enum (DRAFT, PUBLISHED, ARCHIVED), opcional/default para demandas ainda não escaladas
  - [x] `schedule_name`: str, opcional
  - [x] `schedule_version_number`: int, opcional/default 1
  - [x] `pdf_file_id`: FK para `file.id`, opcional
  - [x] `schedule_result_data`: JSON (resultado da alocação), opcional
  - [x] `generated_at`: datetime timestamptz, opcional
  - [x] `published_at`: datetime timestamptz, opcional
- [x] Manter em Demand: `job_id` (já existe); não adicionar `period_start_at` nem `period_end_at`.

### 1.2 Job – result_data
- [x] Em `app/worker/job.py`: não persistir payload pesado em `Job.result_data`; apenas `{"allocation_count": N}`.

### 1.3 Remover Schedule
- [x] Criar migração Alembic que remove a tabela `schedule` (0127 add columns to demand, 0128 drop schedule).
- [x] Remover `app/model/schedule.py`; enum `ScheduleStatus` movido para `demand.py`.
- [x] Atualizar `app/model/__init__.py`: remover export de Schedule; exportar ScheduleStatus de Demand.

---

## 2. API

### 2.1 Endpoints que hoje usam Schedule
- [x] **Listar “escalas”**: `GET /schedule/list` lista Demand com `schedule_status` não nulo; filtros `start_time_from`/`start_time_to` e alias `period_start_at`/`period_end_at`.
- [x] **Detalhe de “escala”**: `GET /schedule/{id}` = Demand por id (id = demand_id); retorna campos de escala.
- [x] **Criar “schedule” manual**: `POST /schedule` atualiza Demand com schedule_status DRAFT, schedule_name, schedule_version_number.
- [x] **Publicar escala**: `POST /schedule/{id}/publish` opera sobre Demand (id = demand_id); usa upload_demand_pdf.
- [x] **PDF da escala**: `GET /schedule/{id}/pdf` opera sobre Demand.
- [x] **Excluir “schedule”**: `DELETE /schedule/{id}` reseta estado de escala na Demand (apenas DRAFT).

### 2.2 Geração em lote (ex.: POST /schedule/generate)
- [x] POST /schedule/generate (from_extract): cria apenas Job; worker não persiste em Demand (sem demand_id). Response schedule_id=None.
- [x] POST /schedule/generate-from-demands: cria apenas Job; worker atualiza Demand(s) com resultado.

### 2.3 Arquivo schedule.py e route.py
- [x] `app/api/schedule.py` refatorado para usar Demand (id no path = demand_id).
- [x] `app/api/route.py`: removida criação de Schedule; POST /schedule/generate cria apenas Job com input_data (mode from_extract).

---

## 3. Worker

### 3.1 generate_schedule_job
- [x] Atualizar Demand com schedule_status, schedule_result_data, generated_at, job_id, schedule_name, schedule_version_number.
- [x] Modo “from_demands”: ler Demand do banco; após solver, atualizar cada Demand com demand_id na alocação.
- [x] Modo “from_extract”: período em input_data; não persiste em Demand (alocações sem demand_id são ignoradas).

### 3.2 Outras referências a Schedule no worker
- [x] Removidos imports e usos de Schedule; ScheduleStatus importado de demand.

---

## 4. Storage e PDF

### 4.1 Upload de PDF
- [x] `upload_demand_pdf(session, tenant_id, demand_id, pdf_bytes)` criado; carrega Demand para hospital_id do File; associa à Demand via pdf_file_id. `upload_schedule_pdf` mantido como alias.

### 4.2 Geração de PDF
- [x] `_day_schedules_from_result` passa a receber Demand; usa schedule_result_data; fragmentos buscados por Demand.job_id.

---

## 5. Frontend

### 5.1 Chamadas de API
- [x] Rotas `/schedule/*` mantidas como alias (id = demand_id); frontend continua usando `/api/schedule/*` sem alteração.
- [x] Listagem aceita `period_start_at`/`period_end_at` como alias de start_time_from/start_time_to.

### 5.2 Páginas e tipos
- [x] Frontend não alterado; ScheduleResponse compatível (id, demand_id, period_start_at/end_at preenchidos com start_time/end_time da Demand).

---

## 6. Documentação do projeto

### 6.1 CHECKLIST.md
- [ ] Status geral: remover “Schedule” da lista de modelos; indicar que Demand concentra demanda + estado de escala.
- [ ] Etapas e fases: substituir referências a “Schedule” e “salvar no Schedule” por “Demand” e “atualizar Demand”.
- [ ] Notas sobre `Job.result_data`: indicar que não se persiste payload pesado após o cálculo.
- [ ] Remover ou ajustar itens que citam `period_start_at`/`period_end_at` em Schedule/Demand.

### 6.2 DIRECTIVES.md
- [ ] Seção “Relação Demand → Schedule (1:1)”: reescrever para “Demand com estado de escala” (campos de status, result_data, PDF, datas; sem tabela Schedule).
- [ ] Profissionais para escala: manter; referir apenas a Demand quando necessário.

### 6.3 SECURITY.md
- [ ] Endpoints de “Schedule”: substituir por endpoints baseados em Demand (listar demandas com filtro de escala, publicar demanda, PDF da demanda, etc.).
- [ ] Exemplos e checklist: usar Demand em vez de Schedule onde aplicável.

### 6.4 STACK.md
- [ ] Modelos: remover Schedule; descrever Demand como entidade que inclui dados da demanda e estado da escala (status, result_data, pdf_file_id, etc.).
- [ ] Relações: remover “Demand → Schedule (1:1)”; indicar que não há período persistido na Demand (`period_start_at`/`period_end_at` não existem).

---

## 7. Testes e validação

- [ ] Rodar migrações em ambiente de dev: tabela `schedule` removida; Demand com novos campos.
- [ ] Fluxo completo: extração → geração de escala → atualização de Demand; publicação e PDF por Demand.
- [ ] Garantir que nenhum código restante referencia tabela ou model Schedule.

---

**Última atualização**: Checklist criado para refatoração Demand + Schedule (tabela schedule vazia; sem migração de dados; sem period_*; job.result_data mínimo).
