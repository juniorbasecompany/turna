# Plano de Implementação: Geração de Escala a partir de Demandas

## Objetivo

Adaptar o fluxo de geração de escalas do `app.py` para funcionar integrado ao sistema, lendo demandas diretamente da tabela `demand` (campo `source`) em vez de arquivo JSON, usando o intervalo definido pelos filtros do painel de schedule, e salvando o resultado na tabela `schedule` (ScheduleVersion).

## Contexto Atual

### Fluxo Legado (app.py)
1. Lê demandas do arquivo `demandas.json` (organizadas por dia)
2. Lê profissionais do arquivo `profissionais.json`
3. Executa solver (greedy ou CP-SAT)
4. Exibe resultados no console
5. Gera PDF opcional do dia 1

### Fluxo Atual do Sistema
1. **Frontend**: Painel de schedule com filtros de período (`periodStartDate`, `periodEndDate`)
2. **Backend**: 
   - Tabela `demand` com campo `source` (JSON) contendo dados originais
   - Tabela `schedule` (ScheduleVersion) para armazenar escalas geradas
   - Job `GENERATE_SCHEDULE` que lê de `Job.result_data` (extração de arquivo)
   - Worker assíncrono processa jobs

### Diferenças Principais
- **Fonte de dados**: JSON file → Tabela `demand.source`
- **Intervalo**: Um dia fixo → Intervalo definido pelo filtro do painel
- **Trigger**: Execução direta → Botão "Calcular a escala" no frontend
- **Saída**: Console → Tabela `schedule`

## Análise do Fluxo Proposto

### 1. Fonte de Dados: `demand.source`

**Estrutura esperada**:
- Campo `source` na tabela `demand` é um JSON (`dict` em Python)
- Contém dados originais da extração (similar ao formato do `demandas.json`)
- Pode conter estrutura organizada por dia ou lista plana de demandas

**Considerações**:
- Precisamos entender a estrutura exata de `demand.source`
- Pode ser necessário transformar de formato plano para formato por dia
- Validação de que `source` não é NULL

### 2. Intervalo: Filtros do Painel Schedule

**Fonte**:
- `periodStartDate` e `periodEndDate` do componente `TenantDatePicker` no frontend
- Valores são `Date` objects no frontend, convertidos para ISO 8601 com timezone

**Considerações**:
- Validação de que período está definido (já existe no frontend)
- Conversão de timezone (frontend → UTC para backend)
- Filtro de demandas por `start_time` dentro do intervalo

### 3. Trigger: Botão "Calcular a escala"

**Localização**: `frontend/app/(protected)/schedule/page.tsx`
- Função: `handleCreateCardClick()`
- Validação: Verifica se `periodStartDate` e `periodEndDate` estão definidos
- Ação atual: Chama `handleCreateClick()` (cria ScheduleVersion vazia)

**Mudança necessária**:
- Em vez de criar ScheduleVersion vazia, criar ScheduleVersion + Job GENERATE_SCHEDULE
- Passar período como parâmetros

### 4. Saída: Tabela `schedule`

**Estrutura atual**:
- `ScheduleVersion` já existe e suporta `result_data` (JSON)
- Campo `result_data` armazena resultado do solver
- Status: DRAFT, PUBLISHED, ARCHIVED

**Considerações**:
- Formato de `result_data` deve ser compatível com o formato atual
- Manter compatibilidade com geração de PDF existente

## Plano de Implementação

### Fase 1: Preparação e Análise

#### 1.1 Entender Estrutura de `demand.source`
- [ ] Analisar exemplos reais de `demand.source` no banco
- [ ] Documentar estrutura esperada
- [ ] Identificar diferenças com formato de `demandas.json`
- [ ] Criar função de transformação se necessário

#### 1.2 Mapear Formato de Dados
- [ ] Documentar formato de entrada esperado pelo solver
- [ ] Documentar formato de saída do solver
- [ ] Garantir compatibilidade com `ScheduleVersion.result_data`

### Fase 2: Backend - Adaptação do Worker

#### 2.1 Criar Função de Leitura de Demandas
**Arquivo**: `backend/app/worker/job.py` (nova função ou adaptar existente)

**Função**: `_demands_from_database()`
- [ ] Receber: `tenant_id`, `period_start_at`, `period_end_at`
- [ ] Query: Buscar demandas onde `start_time` está no intervalo
- [ ] Ler `demand.source` de cada demanda
- [ ] Transformar para formato esperado pelo solver (similar a `_demands_from_extract_result`)
- [ ] Agrupar por dia (se necessário)
- [ ] Retornar: `(demands: list[dict], days: int)`

**Validações**:
- [ ] Filtrar por `tenant_id` (segurança multi-tenant)
- [ ] Validar que `source` não é NULL
- [ ] Validar formato de `source`
- [ ] Validar que há demandas no período

#### 2.2 Adaptar Job GENERATE_SCHEDULE
**Arquivo**: `backend/app/worker/job.py` (função `generate_schedule_job`)

**Mudanças**:
- [ ] Adicionar modo de operação: "from_extract" (atual) vs "from_demands" (novo)
- [ ] Se modo "from_demands":
  - [ ] Não requerer `extract_job_id`
  - [ ] Usar `_demands_from_database()` em vez de `_demands_from_extract_result()`
  - [ ] Manter resto da lógica igual (solver, salvamento)
- [ ] Manter compatibilidade com modo "from_extract" (não quebrar fluxo existente)

**Input do Job**:
```python
{
    "schedule_version_id": int,
    "mode": "from_demands" | "from_extract",  # novo campo
    "extract_job_id": int | None,  # opcional se mode == "from_demands"
    "period_start_at": str,  # ISO 8601, se mode == "from_demands"
    "period_end_at": str,  # ISO 8601, se mode == "from_demands"
    "allocation_mode": "greedy" | "cp-sat",
    "pros_by_sequence": list[dict] | None  # opcional, fallback para mock
}
```

#### 2.3 Criar Endpoint de Geração
**Arquivo**: `backend/app/api/schedule.py` (novo endpoint)

**Endpoint**: `POST /schedule/generate-from-demands`

**Request**:
```python
class ScheduleGenerateFromDemandsRequest(PydanticBaseModel):
    name: str
    period_start_at: datetime  # timestamptz, ISO 8601
    period_end_at: datetime  # timestamptz, ISO 8601
    allocation_mode: str = "greedy"  # "greedy" | "cp-sat"
    pros_by_sequence: Optional[list[dict]] = None  # opcional
    version_number: int = 1
```

**Lógica**:
- [ ] Validar período (start < end, timezone explícito)
- [ ] Validar que há demandas no período (query rápida)
- [ ] Criar `ScheduleVersion` (status DRAFT)
- [ ] Criar `Job` (tipo GENERATE_SCHEDULE, status PENDING)
- [ ] Enfileirar job no Arq
- [ ] Retornar `{job_id, schedule_version_id}`

**Validações de Segurança**:
- [ ] Usar `get_current_member()` para obter `tenant_id`
- [ ] Filtrar demandas por `tenant_id` (nunca aceitar do body)
- [ ] Validar que período está dentro de limites razoáveis

### Fase 3: Frontend - Integração com Botão

#### 3.1 Adaptar Handler do Botão
**Arquivo**: `frontend/app/(protected)/schedule/page.tsx`

**Função**: `handleCreateCardClick()` ou nova função

**Mudanças**:
- [ ] Em vez de chamar `handleCreateClick()`, chamar nova função
- [ ] Nova função: `handleGenerateScheduleClick()`
- [ ] Validar que `periodStartDate` e `periodEndDate` estão definidos (já existe)
- [ ] Converter datas para UTC (usar `localDateToUtcStart` e `localDateToUtcEndExclusive`)
- [ ] Chamar endpoint `POST /schedule/generate-from-demands`
- [ ] Criar ScheduleVersion + Job
- [ ] Mostrar feedback (loading, sucesso, erro)
- [ ] Redirecionar ou atualizar lista após sucesso

#### 3.2 Adicionar Estados de Loading
- [ ] Estado para indicar que geração está em andamento
- [ ] Desabilitar botão durante geração
- [ ] Mostrar mensagem de progresso

#### 3.3 Polling de Status do Job (Opcional)
- [ ] Após criar job, iniciar polling de status
- [ ] Atualizar ScheduleVersion quando job completar
- [ ] Mostrar erro se job falhar
- [ ] Considerar usar WebSocket no futuro (não na Fase 1)

### Fase 4: Profissionais

#### 4.1 Fonte de Profissionais
**Opções**:
1. **Mock temporário**: Usar função `_load_pros_from_repo_test()` (já existe)
2. **Tabela futura**: Criar tabela `professional` (fora do escopo desta fase)
3. **Input do usuário**: Permitir passar `pros_by_sequence` no request (opcional)

**Decisão para Fase 1**:
- [ ] Usar mock temporário (já funciona)
- [ ] Campo `pros_by_sequence` opcional no endpoint
- [ ] Se não fornecido, usar mock
- [ ] Documentar que é temporário

### Fase 5: Validações e Tratamento de Erros

#### 5.1 Validações no Backend
- [ ] Período válido (start < end, timezone explícito)
- [ ] Há demandas no período (query de verificação)
- [ ] Demandas têm `source` não NULL
- [ ] `source` tem formato válido
- [ ] Tenant isolation (todas as queries filtram por `tenant_id`)

#### 5.2 Tratamento de Erros
- [ ] Erro: Nenhuma demanda no período → HTTP 400 com mensagem clara
- [ ] Erro: Demandas sem `source` → HTTP 400 com mensagem clara
- [ ] Erro: Formato inválido de `source` → HTTP 400 com mensagem clara
- [ ] Erro: Solver falha → Job FAILED, mensagem no `error_message`
- [ ] Erro: Período inválido → HTTP 400 com mensagem clara

#### 5.3 Mensagens ao Usuário
- [ ] Frontend: Exibir mensagens de erro claras no ActionBar
- [ ] Frontend: Exibir progresso durante geração
- [ ] Frontend: Exibir sucesso quando job completar

### Fase 6: Testes e Validação

#### 6.1 Testes Manuais
- [ ] Criar demandas de teste com `source` válido
- [ ] Testar geração com período válido
- [ ] Testar geração com período sem demandas
- [ ] Testar geração com demandas sem `source`
- [ ] Testar validação de tenant (não deve ver demandas de outros tenants)
- [ ] Verificar que ScheduleVersion é criada corretamente
- [ ] Verificar que `result_data` tem formato correto

#### 6.2 Validação de Compatibilidade
- [ ] Verificar que fluxo antigo (from_extract) ainda funciona
- [ ] Verificar que PDF ainda funciona com novo formato
- [ ] Verificar que não quebrou endpoints existentes

### Fase 7: Documentação

#### 7.1 Atualizar Documentação
- [ ] Documentar novo endpoint em `CHECKLIST.md`
- [ ] Documentar formato de `demand.source` esperado
- [ ] Documentar diferenças entre modos "from_extract" e "from_demands"
- [ ] Atualizar `DIRECTIVES.md` se necessário

## Considerações de Segurança

### Multi-Tenant Isolation
- ✅ Todas as queries de demandas devem filtrar por `tenant_id` do member
- ✅ Endpoint usa `get_current_member()` para obter `tenant_id`
- ✅ Nunca aceitar `tenant_id` do body
- ✅ Validar que ScheduleVersion pertence ao tenant

### Validação de Dados
- ✅ Validar formato de `demand.source` antes de processar
- ✅ Validar período antes de criar job
- ✅ Sanitizar dados antes de passar para solver

## Considerações de Performance

### Otimização de Queries
- [ ] Índice em `demand.start_time` (já existe)
- [ ] Índice em `demand.tenant_id` (já existe)
- [ ] Query eficiente para contar demandas no período

### Jobs Assíncronos
- ✅ Geração sempre via job assíncrono (não bloquear API)
- ✅ Retornar `job_id` imediatamente
- ✅ Frontend pode fazer polling opcional

## Riscos e Mitigações

### Risco 1: Formato de `demand.source` inconsistente
**Mitigação**: 
- Validar formato antes de processar
- Tratar erros graciosamente
- Documentar formato esperado

### Risco 2: Performance com muitas demandas
**Mitigação**:
- Usar jobs assíncronos (já implementado)
- Considerar paginação se necessário no futuro
- Monitorar tempo de execução

### Risco 3: Quebrar fluxo existente
**Mitigação**:
- Manter modo "from_extract" funcionando
- Testes de regressão
- Deploy incremental

## Checklist de Implementação

### Backend
- [ ] Criar função `_demands_from_database()`
- [ ] Adaptar `generate_schedule_job()` para suportar modo "from_demands"
- [ ] Criar endpoint `POST /schedule/generate-from-demands`
- [ ] Adicionar validações de segurança
- [ ] Adicionar tratamento de erros
- [ ] Testes manuais

### Frontend
- [ ] Adaptar `handleCreateCardClick()` ou criar nova função
- [ ] Integrar com endpoint novo
- [ ] Adicionar estados de loading
- [ ] Adicionar tratamento de erros
- [ ] Testes manuais

### Documentação
- [ ] Documentar formato de `demand.source`
- [ ] Atualizar `CHECKLIST.md`
- [ ] Documentar novo endpoint

## Ordem de Implementação Recomendada

1. **Fase 1**: Entender estrutura de `demand.source` (análise)
2. **Fase 2.1**: Criar função `_demands_from_database()`
3. **Fase 2.2**: Adaptar job para suportar modo "from_demands"
4. **Fase 2.3**: Criar endpoint `POST /schedule/generate-from-demands`
5. **Fase 3**: Integrar frontend com novo endpoint
6. **Fase 5**: Adicionar validações e tratamento de erros
7. **Fase 6**: Testes e validação
8. **Fase 7**: Documentação

## Notas Importantes

- **Não quebrar código existente**: Manter compatibilidade com fluxo "from_extract"
- **Segurança primeiro**: Sempre validar `tenant_id` e filtrar queries
- **Jobs assíncronos**: Nunca executar solver diretamente no endpoint
- **Formato de dados**: Manter compatibilidade com formato existente de `result_data`
- **Profissionais**: Usar mock temporário, planejar tabela futura

## Próximos Passos Após Implementação

- [ ] Criar tabela `professional` para gerenciar profissionais
- [ ] Permitir seleção de profissionais no frontend
- [ ] Adicionar suporte a CP-SAT (além de greedy)
- [ ] Melhorar feedback de progresso (WebSocket)
- [ ] Adicionar métricas e monitoramento
