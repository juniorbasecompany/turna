# 📊 Análise de Viabilidade: Migração para `useEntityPage`

## Resumo Executivo

**Status Geral**: ⚠️ **Parcialmente Viável**

- ✅ **Demand**: ✅ **VIÁVEL** - Pode ser migrado com adaptações moderadas
- ⚠️ **File**: ⚠️ **VIÁVEL COM EXTENSÕES** - Requer extensões significativas no hook
- ❌ **Member**: ❌ **NÃO VIÁVEL** - Arquitetura fundamentalmente diferente (carrega todos os dados)

---

## 1. Demand - ✅ VIÁVEL

### Situação Atual
- Carrega dados paginados do backend via `loadDemands()`
- Filtro de texto por procedimento (frontend)
- Carrega lista de hospitais separadamente
- Lógica de validação de datas
- Campos complexos (skills array, source object)

### Compatibilidade com `useEntityPage`
✅ **Alta compatibilidade**

### Adaptações Necessárias

#### 1.1 Filtro de Procedimento
**Problema**: Filtro de texto no frontend  
**Solução**: 
- Opção A: Mover filtro para backend (recomendado)
- Opção B: Aplicar filtro após receber dados do `useEntityPage`

```typescript
// Usar additionalListParams para filtro no backend
const { items: demands } = useEntityPage({
  // ...
  additionalListParams: procedureFilter 
    ? { procedure: procedureFilter } 
    : undefined,
})
```

#### 1.2 Lista de Hospitais
**Problema**: Carrega hospitais separadamente  
**Solução**: Manter carregamento separado (não afeta `useEntityPage`)

#### 1.3 Campos Complexos
**Problema**: `skills` (array) e `source` (object)  
**Solução**: `useEntityPage` já suporta através de `mapFormDataToCreateRequest` e `mapFormDataToUpdateRequest`

### Plano de Migração

1. ✅ Criar tipos `DemandFormData`, `DemandCreateRequest`, `DemandUpdateRequest`
2. ✅ Implementar mapeamentos (`mapEntityToFormData`, etc.)
3. ✅ Mover filtro de procedimento para backend OU aplicar após carregamento
4. ✅ Manter carregamento de hospitais separado
5. ✅ Testar validações e campos complexos

### Esforço Estimado
**Médio** (4-6 horas)

---

## 2. File - ⚠️ VIÁVEL COM EXTENSÕES

### Situação Atual
- Carrega dados paginados do backend
- **Múltiplos filtros**: data (start/end), hospital, status
- Depende de `settings` do tenant para conversão de datas
- **Seleção dupla**: exclusão + leitura
- **Ação customizada**: "Ler conteúdo"
- Polling de thumbnails (não afeta carregamento)
- Upload de arquivos (não afeta carregamento)
- `refreshKey` para forçar recarregamento

### Compatibilidade com `useEntityPage`
⚠️ **Compatibilidade média - requer extensões**

### Desafios Principais

#### 2.1 Múltiplos Filtros Dinâmicos
**Problema**: `useEntityList` suporta `additionalParams`, mas precisa ser reativo a mudanças de `startDate`, `endDate`, `selectedHospitalId`, `statusFilters`  
**Solução**: 
- Estender `useEntityList` para aceitar função de `additionalParams` que seja reativa
- OU usar `useEffect` para atualizar `additionalListParams` quando filtros mudarem

```typescript
// Opção: Estender useEntityList
const additionalParams = useMemo(() => ({
  start_at: startDate ? localDateToUtcStart(startDate, settings) : null,
  end_at: endDate ? localDateToUtcEndExclusive(endDate, settings) : null,
  hospital_id: selectedHospitalId || null,
  status: Array.from(statusFilters.selectedFilters).join(','),
}), [startDate, endDate, selectedHospitalId, statusFilters, settings])
```

#### 2.2 Dependência de `settings`
**Problema**: `useEntityList` carrega antes de `settings` estar disponível  
**Solução**: Usar `listEnabled` para desabilitar carregamento até `settings` estar disponível

```typescript
const { items: files } = useEntityPage({
  // ...
  listEnabled: !!settings, // Só carregar quando settings estiver disponível
  additionalListParams: settings ? computedParams : undefined,
})
```

#### 2.3 Seleção Dupla
**Problema**: `useEntityPage` só gerencia uma seleção  
**Solução**: Manter seleção de leitura separada (não afeta carregamento)

```typescript
// useEntityPage gerencia selectedFiles (exclusão)
// Manter selectedFilesForReading separado
const [selectedFilesForReading, setSelectedFilesForReading] = useState<Set<number>>(new Set())
```

#### 2.4 Ação Customizada "Ler conteúdo"
**Problema**: `useActionBarButtons` já foi estendido para suportar ações customizadas  
**Solução**: Usar extensão existente de `useActionBarButtons`

#### 2.5 RefreshKey
**Problema**: Precisa forçar recarregamento após upload/processamento  
**Solução**: Chamar `loadItems()` manualmente quando necessário

```typescript
const { loadItems } = useEntityPage({...})

// Após upload bem-sucedido
await loadItems()
```

### Plano de Migração

1. ✅ Estender `useEntityList` para suportar `additionalParams` reativo (função ou objeto reativo)
2. ✅ Implementar mapeamentos de dados
3. ✅ Configurar `listEnabled` baseado em `settings`
4. ✅ Manter seleção de leitura separada
5. ✅ Usar extensão existente de `useActionBarButtons` para ação customizada
6. ✅ Implementar `refreshKey` via `loadItems()`

### Esforço Estimado
**Alto** (8-12 horas)

### Extensões Necessárias no Hook

```typescript
// useEntityList.ts - Adicionar suporte a função reativa
interface UseEntityListOptions<T> {
  // ...
  additionalParams?: Record<string, string | number | boolean | null> 
    | (() => Record<string, string | number | boolean | null>)
}
```

---

## 3. Member - ❌ NÃO VIÁVEL

### Situação Atual
- **Carrega TODOS os dados de uma vez** (múltiplas requisições paginadas)
- **Filtra no frontend** (status e role)
- **Pagina no frontend** (após filtrar)
- Funcionalidade de "enviar convite" customizada
- Validação de JSON customizada
- Mensagens de email customizadas

### Compatibilidade com `useEntityPage`
❌ **Incompatível - arquitetura fundamentalmente diferente**

### Problemas Fundamentais

#### 3.1 Carregamento Completo vs Paginação
**Problema**: Member carrega TODOS os dados de uma vez, enquanto `useEntityPage` carrega dados paginados do backend  
**Impacto**: 
- Member: Carrega tudo → Filtra no frontend → Pagina no frontend
- `useEntityPage`: Carrega página do backend → Backend filtra → Backend pagina

**Por que não funciona**:
- Se mover filtros para backend, perde a capacidade de filtrar todos os dados de uma vez
- Se manter carregamento completo, não usa a paginação do `useEntityPage`
- Se usar paginação do backend, não pode filtrar todos os dados no frontend

#### 3.2 Filtros no Frontend
**Problema**: Filtros de status e role são aplicados no frontend após carregar todos os dados  
**Impacto**: Não pode usar `additionalListParams` porque os filtros são aplicados após o carregamento

#### 3.3 Total Baseado em Filtros
**Problema**: O `total` é calculado baseado nos dados filtrados no frontend  
**Impacto**: `useEntityPage` retorna `total` do backend, não do frontend

### Alternativas

#### Opção A: Migrar Filtros para Backend
**Viabilidade**: ✅ Técnicamente viável  
**Problema**: Requer mudanças no backend e perde flexibilidade de filtros no frontend

#### Opção B: Criar Hook Especializado
**Viabilidade**: ✅ Viável  
**Problema**: Não usa `useEntityPage`, mas pode criar `useEntityPageFullLoad` similar

#### Opção C: Manter Como Está
**Viabilidade**: ✅ Viável  
**Recomendação**: ✅ **RECOMENDADO** - Member tem requisitos específicos que justificam carregamento completo

### Conclusão
❌ **NÃO RECOMENDADO migrar Member para `useEntityPage`**

**Razão**: Arquitetura fundamentalmente diferente (carregamento completo vs paginação). A migração exigiria mudar a arquitetura do Member, o que pode não ser desejável.

---

## 4. Recomendações Finais

### Prioridade de Migração

1. ✅ **Demand** - **RECOMENDADO** (viável, esforço médio)
2. ⚠️ **File** - **CONDICIONAL** (viável com extensões, esforço alto)
3. ❌ **Member** - **NÃO RECOMENDADO** (incompatível, arquitetura diferente)

### Plano de Ação Sugerido

#### Fase 1: Demand (Recomendado)
- ✅ Migrar Demand para `useEntityPage`
- ✅ Mover filtro de procedimento para backend OU aplicar após carregamento
- ✅ Manter carregamento de hospitais separado
- **Benefício**: Padronização sem grandes complexidades

#### Fase 2: File (Opcional)
- ⚠️ Estender `useEntityList` para suportar `additionalParams` reativo
- ⚠️ Migrar File para `useEntityPage` com extensões
- ⚠️ Manter seleção de leitura separada
- **Benefício**: Padronização completa, mas requer extensões no hook

#### Fase 3: Member (Não Recomendado)
- ❌ **NÃO MIGRAR** - Manter arquitetura atual
- ✅ Documentar que Member usa carregamento completo por design
- ✅ Considerar criar `useEntityPageFullLoad` no futuro se necessário

---

## 5. Extensões Necessárias nos Hooks

### 5.1 `useEntityList` - Suporte a Parâmetros Reativos

```typescript
// useEntityList.ts
interface UseEntityListOptions<T> {
  // ...
  additionalParams?: 
    | Record<string, string | number | boolean | null>
    | (() => Record<string, string | number | boolean | null>)
}

// Na implementação:
const params = typeof additionalParams === 'function' 
  ? additionalParams() 
  : additionalParams
```

### 5.2 `useEntityPage` - Passar `additionalParams` Reativo

```typescript
// useEntityPage.ts
interface UseEntityPageOptions<TFormData, TEntity, TCreateRequest, TUpdateRequest> {
  // ...
  additionalListParams?: 
    | Record<string, string | number | boolean | null>
    | (() => Record<string, string | number | boolean | null>)
}
```

---

## 6. Checklist de Migração

### Demand
- [ ] Criar tipos `DemandFormData`
- [ ] Implementar `mapEntityToFormData`
- [ ] Implementar `mapFormDataToCreateRequest`
- [ ] Implementar `mapFormDataToUpdateRequest`
- [ ] Mover filtro de procedimento para backend OU aplicar após carregamento
- [ ] Testar validações
- [ ] Testar campos complexos (skills, source)
- [ ] Atualizar `PANEL_COMPARISON.md`

### File
- [ ] Estender `useEntityList` para suportar `additionalParams` reativo
- [ ] Estender `useEntityPage` para passar `additionalParams` reativo
- [ ] Criar tipos `FileFormData`
- [ ] Implementar mapeamentos
- [ ] Configurar `listEnabled` baseado em `settings`
- [ ] Manter seleção de leitura separada
- [ ] Testar múltiplos filtros
- [ ] Testar conversão de datas
- [ ] Testar refreshKey
- [ ] Atualizar `PANEL_COMPARISON.md`

---

## 7. Conclusão

**Resumo**:
- ✅ **Demand**: Viável, esforço médio - **RECOMENDADO**
- ⚠️ **File**: Viável com extensões, esforço alto - **CONDICIONAL**
- ❌ **Member**: Não viável - **NÃO RECOMENDADO**

**Próximo Passo**: Decidir se deseja migrar Demand e/ou File, e se deseja estender os hooks para suportar File.
