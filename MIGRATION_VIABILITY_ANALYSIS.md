# 📊 Análise de Viabilidade: Migração para `useEntityPage`

## File - ⚠️ PENDENTE

### Situação Atual
- ❌ **NÃO MIGRADO** - Ainda utiliza padrão antigo com `useState`, `useEffect` e `protectedFetch` manual
- Carrega dados paginados do backend manualmente
- **Múltiplos filtros**: data (start/end), hospital, status
- Depende de `settings` do tenant para conversão de datas
- **Seleção dupla**: exclusão + leitura
- **Ação customizada**: "Ler conteúdo"
- Polling de thumbnails (não afeta carregamento)
- Upload de arquivos (não afeta carregamento)
- `refreshKey` para forçar recarregamento

### Compatibilidade com `useEntityPage`
✅ **Viável** - Todos os padrões necessários já foram estabelecidos

### Desafios Principais

#### 1.1 Múltiplos Filtros Dinâmicos
**Solução**: Usar `useMemo` para calcular `additionalListParams` reativo (apenas filtros suportados pela API)

**IMPORTANTE**: A API `/api/file/list` não aceita parâmetro `status`. O filtro de status deve ser aplicado no frontend após receber os dados (similar ao padrão usado em Member quando há múltiplos filtros).

```typescript
// Filtros enviados à API (apenas start_at, end_at, hospital_id)
const additionalListParams = useMemo(() => ({
  start_at: startDate ? localDateToUtcStart(startDate, settings) : null,
  end_at: endDate ? localDateToUtcEndExclusive(endDate, settings) : null,
  hospital_id: selectedHospitalId || null,
}), [startDate, endDate, selectedHospitalId, settings])

// Filtro de status aplicado no frontend (após receber dados)
const filteredFiles = useMemo(() => {
  return files.filter((file) => {
    const status = file.job_status === null ? null : (file.job_status as JobStatus)
    return statusFilters.selectedFilters.has(status)
  })
}, [files, statusFilters.selectedFilters])
```

#### 1.2 Dependência de `settings`
**Solução**: Usar `listEnabled` para desabilitar carregamento até `settings` estar disponível

```typescript
const { items: files } = useEntityPage({
  // ...
  listEnabled: !!settings,
  additionalListParams: settings ? computedParams : undefined,
})
```

#### 1.3 Seleção Dupla
**Solução**: Manter seleção de leitura separada (não afeta carregamento)

```typescript
// useEntityPage gerencia selectedFiles (exclusão)
// Manter selectedFilesForReading separado
const [selectedFilesForReading, setSelectedFilesForReading] = useState<Set<number>>(new Set())
```

#### 1.4 Ação Customizada "Ler conteúdo"
**Solução**: Usar extensão existente de `useActionBarButtons`

#### 1.5 RefreshKey
**Solução**: Chamar `loadItems()` manualmente quando necessário

```typescript
const { loadItems } = useEntityPage({...})

// Após upload bem-sucedido
await loadItems()
```

#### 1.6 Filtro de Status no Frontend
**Solução**: Aplicar filtro de status no frontend após receber dados (API não suporta)

**IMPORTANTE**: Quando há filtro de status no frontend, a paginação também deve ser aplicada no frontend (similar ao padrão usado em Member).

```typescript
// Verificar se precisa filtrar no frontend
const needsFrontendFilter = useMemo(() => {
  return statusFilters.selectedFilters.size < statusFilters.allFilters.length
}, [statusFilters.selectedFilters.size, statusFilters.allFilters.length])

// Filtrar no frontend quando statusFilters está ativo
const filteredFiles = useMemo(() => {
  if (!needsFrontendFilter) {
    return files  // Backend já retornou todos os dados necessários
  }
  return files.filter((file) => {
    const status = file.job_status === null ? null : (file.job_status as JobStatus)
    return statusFilters.selectedFilters.has(status)
  })
}, [files, statusFilters.selectedFilters, needsFrontendFilter])

// Aplicar paginação no frontend quando há filtro de status
const paginatedFiles = useMemo(() => {
  if (!needsFrontendFilter) {
    return filteredFiles  // Backend já paginou
  }
  // Paginar no frontend
  const start = pagination.offset
  const end = start + pagination.limit
  return filteredFiles.slice(start, end)
}, [filteredFiles, needsFrontendFilter, pagination.offset, pagination.limit])

// Ajustar total para refletir filtro de status
const displayTotal = useMemo(() => {
  if (!needsFrontendFilter) {
    return total  // Usar total do backend
  }
  return filteredFiles.length  // Total após filtro no frontend
}, [filteredFiles, needsFrontendFilter, total])
```

#### 1.7 Upload de Arquivos
**Solução**: Upload é feito via `/api/file/upload` com FormData, não via POST `/api/file`. Manter lógica de upload separada do `useEntityPage`.

```typescript
// Upload não usa handleSave do useEntityPage
// Manter lógica de upload atual (handleFileSelect, handleUpload, etc.)
// Após upload bem-sucedido, chamar loadItems() para recarregar lista
```

#### 1.8 FormData e Mapeamentos Simplificados
**Solução**: File não tem formulário de criação/edição tradicional. Os mapeamentos podem ser simplificados, mas ainda precisam existir para que `useEntityPage` funcione.

**Nota**: O único "formulário" real é para editar o JSON do job result_data, que é uma funcionalidade customizada e não deve usar o `handleSave` do `useEntityPage`.

### Checklist de Migração

- [ ] Criar tipos `FileFormData`, `FileCreateRequest`, `FileUpdateRequest` (simplificados, pois File não tem formulário tradicional)
- [ ] Implementar `mapEntityToFormData` (pode retornar objeto vazio ou mínimo)
- [ ] Implementar `mapFormDataToCreateRequest` (não será usado para upload, mas necessário para o hook)
- [ ] Implementar `mapFormDataToUpdateRequest` (não será usado, mas necessário para o hook)
- [ ] Implementar `validateFormData` (pode retornar null sempre, pois validação é customizada)
- [ ] Implementar `isEmptyCheck` (pode retornar true sempre, pois não há formulário tradicional)
- [ ] Usar `useMemo` para calcular `additionalListParams` reativo (apenas start_at, end_at, hospital_id)
- [ ] Configurar `listEnabled` baseado em `settings`
- [ ] Implementar filtro de status no frontend usando `useMemo` (similar ao Member page)
- [ ] Ajustar paginação no frontend quando filtro de status está ativo
- [ ] Manter seleção de leitura separada (`selectedFilesForReading`)
- [ ] Manter lógica de upload separada (não usar `handleSave` do `useEntityPage`)
- [ ] Manter lógica de edição de JSON separada (não usar `handleSave` do `useEntityPage`)
- [ ] Usar extensão existente de `useActionBarButtons` para ação customizada "Ler conteúdo"
- [ ] Implementar `refreshKey` via `loadItems()` após upload/processamento
- [ ] Atualizar `PANEL_COMPARISON.md`

### Esforço Estimado
**Médio-Alto** (6-10 horas)

**Notas Importantes**:
1. Não é necessário estender os hooks. O padrão de usar `useMemo` para calcular `additionalListParams` reativo já é suficiente.
2. O filtro de status deve ser aplicado no frontend (API não suporta), similar ao padrão usado em Member quando há múltiplos filtros.
3. Upload e edição de JSON são funcionalidades customizadas que não devem usar `handleSave` do `useEntityPage`.
4. Os mapeamentos de FormData podem ser simplificados, mas ainda precisam existir para que o hook funcione corretamente.

---

## Conclusão

**Próximo Passo**: Migrar File para `useEntityPage`. A migração é viável e requer implementação dos mapeamentos de dados e configuração adequada dos filtros reativos usando `useMemo`.
