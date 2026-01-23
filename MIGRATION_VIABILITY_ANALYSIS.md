# 📊 Análise de Viabilidade: Migração para `useEntityPage`

## Resumo Executivo

**Status Geral**: ⚠️ **Parcialmente Viável**

- ✅ **Demand**: ✅ **MIGRADO** - Já utiliza `useEntityPage`
- ✅ **Member**: ✅ **MIGRADO** - Já utiliza `useEntityPage` (com filtros híbridos frontend/backend)
- ⚠️ **File**: ⚠️ **VIÁVEL COM EXTENSÕES** - Requer extensões significativas no hook

---

## 1. File - ⚠️ VIÁVEL COM EXTENSÕES

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

#### 1.1 Múltiplos Filtros Dinâmicos
**Problema**: `useEntityList` suporta `additionalParams`, mas precisa ser reativo a mudanças de `startDate`, `endDate`, `selectedHospitalId`, `statusFilters`  
**Solução**: 
- Estender `useEntityList` para aceitar função de `additionalParams` que seja reativa
- OU usar `useMemo` para calcular `additionalListParams` reativo (similar ao Member)

```typescript
// Opção: Usar useMemo (similar ao Member)
const additionalListParams = useMemo(() => ({
  start_at: startDate ? localDateToUtcStart(startDate, settings) : null,
  end_at: endDate ? localDateToUtcEndExclusive(endDate, settings) : null,
  hospital_id: selectedHospitalId || null,
  status: Array.from(statusFilters.selectedFilters).join(','),
}), [startDate, endDate, selectedHospitalId, statusFilters, settings])
```

#### 1.2 Dependência de `settings`
**Problema**: `useEntityList` carrega antes de `settings` estar disponível  
**Solução**: Usar `listEnabled` para desabilitar carregamento até `settings` estar disponível

```typescript
const { items: files } = useEntityPage({
  // ...
  listEnabled: !!settings, // Só carregar quando settings estiver disponível
  additionalListParams: settings ? computedParams : undefined,
})
```

#### 1.3 Seleção Dupla
**Problema**: `useEntityPage` só gerencia uma seleção  
**Solução**: Manter seleção de leitura separada (não afeta carregamento)

```typescript
// useEntityPage gerencia selectedFiles (exclusão)
// Manter selectedFilesForReading separado
const [selectedFilesForReading, setSelectedFilesForReading] = useState<Set<number>>(new Set())
```

#### 1.4 Ação Customizada "Ler conteúdo"
**Problema**: `useActionBarButtons` já foi estendido para suportar ações customizadas  
**Solução**: Usar extensão existente de `useActionBarButtons`

#### 1.5 RefreshKey
**Problema**: Precisa forçar recarregamento após upload/processamento  
**Solução**: Chamar `loadItems()` manualmente quando necessário

```typescript
const { loadItems } = useEntityPage({...})

// Após upload bem-sucedido
await loadItems()
```

### Plano de Migração

1. [ ] Implementar mapeamentos de dados (`FileFormData`, `mapEntityToFormData`, etc.)
2. [ ] Configurar `listEnabled` baseado em `settings`
3. [ ] Usar `useMemo` para calcular `additionalListParams` reativo (similar ao Member)
4. [ ] Manter seleção de leitura separada
5. [ ] Usar extensão existente de `useActionBarButtons` para ação customizada
6. [ ] Implementar `refreshKey` via `loadItems()`

### Esforço Estimado
**Alto** (8-12 horas)

**Nota**: Não é necessário estender os hooks. O padrão usado no Member (usar `useMemo` para calcular `additionalListParams` reativo) já é suficiente e pode ser replicado no File.

---

## 2. Status das Migrações

### ✅ Demand - MIGRADO
- ✅ Já utiliza `useEntityPage`
- ✅ Filtro de procedimento mantido no frontend (aplicado após carregamento)
- ✅ Carregamento de hospitais mantido separado
- ✅ Campos complexos (skills, source) funcionando corretamente

### ✅ Member - MIGRADO
- ✅ Já utiliza `useEntityPage`
- ✅ Implementa filtros híbridos: usa `additionalListParams` quando apenas 1 filtro está selecionado, filtra no frontend quando múltiplos estão selecionados
- ✅ Paginação funciona corretamente com filtros híbridos
- ✅ Funcionalidades customizadas (envio de convite, validação JSON) mantidas

---

## 3. Recomendações Finais

### Prioridade de Migração

1. ⚠️ **File** - **CONDICIONAL** (viável com extensões, esforço alto)

### Plano de Ação Sugerido

#### Migração do File (Opcional)
- ⚠️ Implementar mapeamentos de dados (`FileFormData`, etc.)
- ⚠️ Usar `useMemo` para calcular `additionalListParams` reativo (similar ao Member)
- ⚠️ Configurar `listEnabled` baseado em `settings`
- ⚠️ Manter seleção de leitura separada
- ⚠️ Usar extensão existente de `useActionBarButtons` para ação customizada
- ⚠️ Implementar `refreshKey` via `loadItems()`
- **Benefício**: Padronização completa, mas requer implementação dos mapeamentos

---

## 4. Checklist de Migração

### File
- [ ] Criar tipos `FileFormData`, `FileCreateRequest`, `FileUpdateRequest`
- [ ] Implementar `mapEntityToFormData`
- [ ] Implementar `mapFormDataToCreateRequest`
- [ ] Implementar `mapFormDataToUpdateRequest`
- [ ] Implementar `validateFormData`
- [ ] Implementar `isEmptyCheck`
- [ ] Usar `useMemo` para calcular `additionalListParams` reativo (similar ao Member)
- [ ] Configurar `listEnabled` baseado em `settings`
- [ ] Manter seleção de leitura separada (`selectedFilesForReading`)
- [ ] Usar extensão existente de `useActionBarButtons` para ação customizada "Ler conteúdo"
- [ ] Implementar `refreshKey` via `loadItems()` após upload/processamento
- [ ] Atualizar `PANEL_COMPARISON.md`

---

## 5. Conclusão

**Resumo**:
- ✅ **Demand**: ✅ **MIGRADO** - Já utiliza `useEntityPage`
- ✅ **Member**: ✅ **MIGRADO** - Já utiliza `useEntityPage` (com filtros híbridos)
- ⚠️ **File**: Viável com extensões, esforço alto - **CONDICIONAL**

**Próximo Passo**: Decidir se deseja migrar File para `useEntityPage`. A migração é viável, mas requer implementação dos mapeamentos de dados e configuração adequada dos filtros reativos.
