# Checklist: Validação e Gerenciamento de Demandas

Este checklist organiza as melhorias no sistema de validação e gerenciamento de demandas cirúrgicas, baseado na análise da proposta de arquitetura.

## Princípios

- **Incremental**: Cada grupo pode ser implementado e testado independentemente
- **Não quebrar**: Manter compatibilidade com código existente
- **Estrutura atual**: Manter modelo estruturado (não migrar para JSONB)
- **Validação centralizada**: Reutilizar regras entre backend e frontend

---

## GRUPO 1: Schema Pydantic Reutilizável (Backend)

**Objetivo**: Centralizar validação de Demand em um schema Pydantic reutilizável.

**Arquivos afetados**:
- `backend/app/schema/demand.py` (novo)
- `backend/app/api/route.py` (refatorar)
- `backend/app/worker/job.py` (usar schema)

### Tarefas

- [ ] **1.1** Criar estrutura de diretório `backend/app/schema/`
  - [ ] Criar `backend/app/schema/__init__.py`
  - [ ] Criar `backend/app/schema/demand.py`

- [ ] **1.2** Criar `DemandSchema` base (Pydantic v2)
  - [ ] Definir campos: `id`, `room`, `start_time`, `end_time`, `procedure`, `anesthesia_type`, `complexity`, `skills`, `priority`, `is_pediatric`, `notes`, `source`
  - [ ] Validadores:
    - [ ] `procedure` não pode ser vazio
    - [ ] `end_time > start_time`
    - [ ] `start_time` e `end_time` devem ter timezone
    - [ ] `priority` normalizado para "Urgente" ou "Emergência" (ou None)
    - [ ] `skills` como lista de strings
  - [ ] Documentação em português nos campos

- [ ] **1.3** Criar `DemandCreateSchema` (herda de `DemandSchema`)
  - [ ] Campos opcionais conforme necessário
  - [ ] Validações específicas de criação

- [ ] **1.4** Criar `DemandUpdateSchema` (todos campos opcionais)
  - [ ] Validações específicas de atualização
  - [ ] Permitir atualização parcial

- [ ] **1.5** Refatorar `DemandCreate` em `route.py`
  - [ ] Usar `DemandCreateSchema` do novo módulo
  - [ ] Manter compatibilidade com endpoints existentes
  - [ ] Testar via Swagger

- [ ] **1.6** Refatorar `DemandUpdate` em `route.py`
  - [ ] Usar `DemandUpdateSchema` do novo módulo
  - [ ] Manter compatibilidade com endpoints existentes
  - [ ] Testar via Swagger

- [ ] **1.7** Testes manuais
  - [ ] `POST /demand` com dados válidos → 201
  - [ ] `POST /demand` com `end_time <= start_time` → 422
  - [ ] `POST /demand` com `procedure` vazio → 422
  - [ ] `PUT /demand/{id}` com atualização parcial → 200
  - [ ] Validar normalização de `priority`

---

## GRUPO 2: Status e Erros de Validação (Backend)

**Objetivo**: Adicionar rastreamento de status e erros de validação nas Demand.

**Arquivos afetados**:
- `backend/app/model/demand.py`
- `backend/alembic/versions/XXXX_add_demand_status_validation.py` (nova migração)
- `backend/app/api/route.py`
- `backend/app/worker/job.py`

### Tarefas

- [ ] **2.1** Criar migração Alembic
  - [ ] Adicionar coluna `status` (VARCHAR, default 'validated')
  - [ ] Adicionar coluna `validation_errors` (JSONB, nullable)
  - [ ] Valores possíveis de `status`: 'draft', 'validated', 'scheduled'
  - [ ] Índice em `status` para queries

- [ ] **2.2** Atualizar modelo `Demand`
  - [ ] Adicionar campo `status: str = Field(default="validated")`
  - [ ] Adicionar campo `validation_errors: Optional[dict] = Field(default=None, sa_column=Column(JSON))`
  - [ ] Atualizar docstring

- [ ] **2.3** Atualizar schemas Pydantic
  - [ ] Adicionar `status` em `DemandSchema` (opcional, default 'validated')
  - [ ] Adicionar `validation_errors` em `DemandSchema` (opcional)
  - [ ] Validador para valores válidos de `status`

- [ ] **2.4** Atualizar `DemandCreate` e `DemandUpdate`
  - [ ] Permitir definir `status` na criação (default 'validated')
  - [ ] Permitir atualizar `status` e `validation_errors`
  - [ ] Validar valores de `status`

- [ ] **2.5** Atualizar worker `extract_demand_job`
  - [ ] Após extração, validar cada demanda do `result_data`
  - [ ] Se houver erros, criar Demand com `status='draft'` e `validation_errors` preenchido
  - [ ] Se válido, criar com `status='validated'`
  - [ ] Formato de `validation_errors`: `{"field_name": ["erro1", "erro2"]}`

- [ ] **2.6** Atualizar endpoint `GET /demand/list`
  - [ ] Adicionar filtro opcional `status` (Query parameter)
  - [ ] Retornar `status` e `validation_errors` na resposta

- [ ] **2.7** Atualizar endpoint `GET /demand/{id}`
  - [ ] Retornar `status` e `validation_errors` na resposta

- [ ] **2.8** Testes manuais
  - [ ] Criar Demand manualmente com `status='draft'` → verificar no banco
  - [ ] Criar Demand com `validation_errors` → verificar JSONB
  - [ ] Filtrar por `status` em `GET /demand/list`
  - [ ] Extrair PDF com erro na IA → verificar Demand criada como 'draft'

---

## GRUPO 3: Validação de JSON da IA (Backend)

**Objetivo**: Endpoint para validar JSON bruto da IA antes de criar Demand.

**Arquivos afetados**:
- `backend/app/api/route.py`
- `backend/app/schema/demand.py` (reutilizar)

### Tarefas

- [ ] **3.1** Criar função `validate_demand_json()` em `schema/demand.py`
  - [ ] Recebe dict (JSON bruto da IA)
  - [ ] Valida usando `DemandSchema`
  - [ ] Retorna `{"valid": bool, "errors": dict, "normalized": dict}`
  - [ ] Formato de `errors`: `{"field_name": ["erro1", "erro2"]}`

- [ ] **3.2** Criar endpoint `POST /api/job/{job_id}/validate-demands`
  - [ ] Buscar Job e validar tenant
  - [ ] Verificar se Job tem `result_data` com `demands[]`
  - [ ] Validar cada demanda do array
  - [ ] Retornar:
    ```json
    {
      "valid": bool,
      "total": int,
      "valid_count": int,
      "invalid_count": int,
      "demands": [
        {
          "index": int,
          "valid": bool,
          "errors": dict,
          "normalized": dict
        }
      ]
    }
    ```

- [ ] **3.3** Adicionar endpoint `POST /api/demand/validate` (validação de demanda única)
  - [ ] Recebe JSON de demanda no body
  - [ ] Valida usando `DemandSchema`
  - [ ] Retorna `{"valid": bool, "errors": dict, "normalized": dict}`

- [ ] **3.4** Testes manuais
  - [ ] Validar JSON válido → `valid: true`
  - [ ] Validar JSON com `end_time <= start_time` → `valid: false`, `errors` preenchido
  - [ ] Validar JSON com `procedure` vazio → `valid: false`
  - [ ] Validar múltiplas demandas de um Job → retornar array com status de cada uma

---

## GRUPO 4: Metadados de Campos (Frontend)

**Objetivo**: Criar definições centralizadas de campos para uso no frontend.

**Arquivos afetados**:
- `frontend/shared/field-definitions.ts` (novo)
- Componentes de formulário (atualizar)

### Tarefas

- [ ] **4.1** Criar estrutura de diretório `frontend/shared/`
  - [ ] Criar `frontend/shared/field-definitions.ts`

- [ ] **4.2** Definir interface `FieldDefinition`
  ```typescript
  interface FieldDefinition {
    title: string
    description: string
    type: 'string' | 'number' | 'boolean' | 'datetime' | 'array'
    required: boolean
    editable?: boolean
    min?: number
    max?: number
    options?: string[]
    // ... outros metadados
  }
  ```

- [ ] **4.3** Criar objeto `demandFieldDefinitions`
  - [ ] Definir metadados para cada campo:
    - `id`: título, descrição, tipo, não editável
    - `room`: título, descrição, tipo string
    - `start_time`: título, descrição, tipo datetime, obrigatório
    - `end_time`: título, descrição, tipo datetime, obrigatório
    - `procedure`: título, descrição, tipo string, obrigatório
    - `anesthesia_type`: título, descrição, tipo string, opcional
    - `complexity`: título, descrição, tipo string, opcional
    - `skills`: título, descrição, tipo array, opcional
    - `priority`: título, descrição, tipo string, opções ["Urgente", "Emergência"]
    - `is_pediatric`: título, descrição, tipo boolean
    - `notes`: título, descrição, tipo string, opcional
    - `status`: título, descrição, tipo string, opções ["draft", "validated", "scheduled"]
    - `validation_errors`: título, descrição, tipo object, não editável

- [ ] **4.4** Exportar funções auxiliares
  - [ ] `getFieldDefinition(fieldName: string): FieldDefinition | undefined`
  - [ ] `getRequiredFields(): string[]`
  - [ ] `getEditableFields(): string[]`

- [ ] **4.5** Testes
  - [ ] Verificar que todas as definições estão corretas
  - [ ] Testar funções auxiliares

---

## GRUPO 5: Validação no Frontend

**Objetivo**: Implementar validação em tempo real no frontend usando metadados.

**Arquivos afetados**:
- `frontend/lib/validation.ts` (novo ou atualizar)
- Componentes de formulário

### Tarefas

- [ ] **5.1** Criar `frontend/lib/demandValidation.ts`
  - [ ] Função `validateDemandField(field: string, value: any): string[]` (retorna erros)
  - [ ] Função `validateDemand(data: Record<string, any>): Record<string, string[]>`
  - [ ] Usar `demandFieldDefinitions` para regras
  - [ ] Validar:
    - Campos obrigatórios
    - Tipos de dados
    - `end_time > start_time`
    - Valores de enum (`priority`, `status`)

- [ ] **5.2** Criar hook `useDemandValidation`
  - [ ] Retorna `{ errors, validate, validateField, clearErrors }`
  - [ ] Validação em tempo real (onChange)
  - [ ] Validação completa antes de submit

- [ ] **5.3** Atualizar componente de edição de Demand (se existir)
  - [ ] Usar `useDemandValidation`
  - [ ] Exibir erros abaixo de cada campo
  - [ ] Desabilitar submit se houver erros

- [ ] **5.4** Atualizar componente de criação de Demand (se existir)
  - [ ] Usar `useDemandValidation`
  - [ ] Exibir erros em tempo real

- [ ] **5.5** Testes manuais
  - [ ] Criar demanda com `end_time <= start_time` → erro exibido
  - [ ] Criar demanda sem `procedure` → erro exibido
  - [ ] Corrigir erro → erro desaparece
  - [ ] Submit com erros → botão desabilitado

---

## GRUPO 6: Exibição de Erros de Validação (Frontend)

**Objetivo**: Mostrar erros de validação da IA na interface.

**Arquivos afetados**:
- Componentes de listagem/visualização de Demand
- Componente de edição de JSON (se existir)

### Tarefas

- [ ] **6.1** Atualizar componente de listagem de Demand
  - [ ] Exibir badge/ícone para Demand com `status='draft'`
  - [ ] Exibir badge/ícone para Demand com `validation_errors`
  - [ ] Tooltip com resumo de erros

- [ ] **6.2** Atualizar componente de detalhes de Demand
  - [ ] Seção "Erros de Validação" (se houver `validation_errors`)
  - [ ] Listar erros por campo
  - [ ] Formatação clara (cores, ícones)

- [ ] **6.3** Atualizar componente de edição de JSON (em `file/page.tsx`)
  - [ ] Validar JSON antes de salvar
  - [ ] Exibir erros de validação inline
  - [ ] Destacar campos com erro no JSON

- [ ] **6.4** Criar componente `ValidationErrorsDisplay`
  - [ ] Recebe `validation_errors` (dict)
  - [ ] Renderiza lista de erros por campo
  - [ ] Estilo consistente (alert/warning)

- [ ] **6.5** Testes manuais
  - [ ] Visualizar Demand com erros → erros exibidos
  - [ ] Editar JSON com erro → erro destacado
  - [ ] Corrigir erro → erro desaparece

---

## GRUPO 7: Endpoint de Validação em Lote (Backend)

**Objetivo**: Validar e corrigir múltiplas Demand de um Job.

**Arquivos afetados**:
- `backend/app/api/route.py`

### Tarefas

- [ ] **7.1** Criar endpoint `POST /api/job/{job_id}/validate-and-create-demands`
  - [ ] Buscar Job e validar tenant
  - [ ] Validar cada demanda do `result_data.demands[]`
  - [ ] Criar Demand para cada item válido (`status='validated'`)
  - [ ] Criar Demand para cada item inválido (`status='draft'`, `validation_errors` preenchido)
  - [ ] Retornar:
    ```json
    {
      "created": int,
      "validated": int,
      "drafts": int,
      "demand_ids": [int]
    }
    ```

- [ ] **7.2** Criar endpoint `PUT /api/demand/batch` (atualização em lote)
  - [ ] Receber array de `{id, updates}`
  - [ ] Validar cada atualização
  - [ ] Atualizar em transação
  - [ ] Retornar resultados por item

- [ ] **7.3** Testes manuais
  - [ ] Validar e criar demandas de um Job → verificar criação
  - [ ] Job com demandas inválidas → criar como 'draft'
  - [ ] Atualizar múltiplas demandas → verificar atualização

---

## GRUPO 8: Versionamento (Opcional - Fase 2)

**Objetivo**: Adicionar versionamento de Demand para auditoria.

**Arquivos afetados**:
- `backend/app/model/demand_version.py` (novo)
- `backend/alembic/versions/XXXX_add_demand_version.py` (nova migração)
- `backend/app/api/route.py`

### Tarefas

- [ ] **8.1** Criar modelo `DemandVersion`
  - [ ] Campos: `id`, `demand_id`, `version`, `demand_data` (JSONB), `changed_by` (account_id), `changed_at`
  - [ ] Foreign key para `demand.id`

- [ ] **8.2** Criar migração Alembic
  - [ ] Tabela `demand_version`
  - [ ] Índices apropriados

- [ ] **8.3** Atualizar endpoints de atualização
  - [ ] Criar `DemandVersion` antes de atualizar `Demand`
  - [ ] Incrementar `version` automaticamente

- [ ] **8.4** Criar endpoint `GET /api/demand/{id}/versions`
  - [ ] Listar versões de uma Demand
  - [ ] Retornar histórico ordenado por `changed_at`

- [ ] **8.5** Testes manuais
  - [ ] Atualizar Demand → verificar versão criada
  - [ ] Listar versões → verificar histórico

---

## GRUPO 9: Testes Automatizados (Opcional)

**Objetivo**: Adicionar testes unitários e de integração.

**Arquivos afetados**:
- `backend/tests/` (estrutura de testes)

### Tarefas

- [ ] **9.1** Testes do schema Pydantic
  - [ ] Validação de campos obrigatórios
  - [ ] Validação de `end_time > start_time`
  - [ ] Normalização de `priority`

- [ ] **9.2** Testes de endpoints
  - [ ] `POST /demand` com dados válidos
  - [ ] `POST /demand` com dados inválidos
  - [ ] `PUT /demand/{id}` com atualização parcial

- [ ] **9.3** Testes de validação
  - [ ] `POST /api/demand/validate` com JSON válido
  - [ ] `POST /api/demand/validate` com JSON inválido
  - [ ] `POST /api/job/{job_id}/validate-demands`

---

## Ordem de Implementação Recomendada

1. **GRUPO 1** (Schema Pydantic) - Base para tudo
2. **GRUPO 2** (Status e Erros) - Necessário para rastreamento
3. **GRUPO 3** (Validação de JSON) - Útil para debug
4. **GRUPO 4** (Metadados Frontend) - Base para frontend
5. **GRUPO 5** (Validação Frontend) - Melhora UX
6. **GRUPO 6** (Exibição de Erros) - Completa ciclo de validação
7. **GRUPO 7** (Validação em Lote) - Otimização
8. **GRUPO 8** (Versionamento) - Opcional, pode ficar para depois
9. **GRUPO 9** (Testes) - Pode ser feito em paralelo

---

## Notas de Implementação

- **Compatibilidade**: Manter endpoints existentes funcionando
- **Migrações**: Testar rollback de migrações antes de aplicar
- **Frontend**: Testar em diferentes navegadores
- **Performance**: Validar impacto de validações em lote
- **Documentação**: Atualizar Swagger docs para novos endpoints

---

## Critérios de Aceitação

Cada grupo deve atender:

- ✅ Código funciona sem quebrar funcionalidades existentes
- ✅ Testes manuais passam
- ✅ Swagger docs atualizados (backend)
- ✅ Sem erros de lint/type check
- ✅ Migrações aplicadas com sucesso (se aplicável)
