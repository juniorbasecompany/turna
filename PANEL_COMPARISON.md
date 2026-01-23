# 📊 Tabela Comparativa Completa dos Painéis

## Comparação Detalhada: Hospital, Tenant, Member, Demand, File

| Aspecto | Hospital | Tenant (Clínicas) | Member (Associados) | Demand (Demandas) | File (Arquivos) |
|---------|----------|-------------------|---------------------|-------------------|-----------------|
| **Hook de Gerenciamento** | ✅ `useEntityPage` | ✅ `useEntityPage` | ❌ Estado manual (`useState`) | ❌ Estado manual (`useState`) | ❌ Estado manual (`useState`) |
| **EntityCard** | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa (conteúdo customizado) |
| **CardFooter** | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa | ❌ Não usa (estrutura customizada) |
| **CardActionButtons** | ✅ (via CardFooter) | ✅ (via CardFooter) | ✅ (via CardFooter) | ✅ (via CardFooter) | ✅ Usa diretamente |
| **EditForm** | ✅ Usa | ✅ Usa | ❌ Usa `editContent` no CardPanel | ✅ Usa | ✅ Usa |
| **FilterPanel** | ❌ N/A (sem filtros) | ❌ N/A (sem filtros) | ✅ Usa | ❌ N/A (sem filtros) | ✅ Usa |
| **useEntityFilters** | ❌ N/A | ❌ N/A | ✅ Usa | ❌ N/A | ✅ Usa |
| **useActionBarButtons** | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ Usa diretamente | ✅ Usa diretamente | ❌ Customizado (useMemo) |
| **getActionBarErrorProps** | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ Usa diretamente | ✅ Usa diretamente | ✅ Usa diretamente |
| **paginationHandlers** | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ (via usePagination) | ✅ (via usePagination) | ✅ (via usePagination) |
| **Estrutura de Edição** | ✅ `EditForm` separado | ✅ `EditForm` separado | ✅ `EditForm` separado | ✅ `EditForm` separado | ✅ `EditForm` separado |
| **Filtros vs Edição** | ✅ N/A | ✅ N/A | ✅ Mutuamente exclusivos | ✅ N/A | ✅ Mutuamente exclusivos |
| **Container do Card** | Cor dinâmica (`hospital.color`) | Gradiente fixo azul | Gradiente fixo azul | Cor dinâmica (`hospital.color`) | Estrutura customizada (thumbnail) |
| **Borda no Container** | ✅ `border-gray-200` | ✅ `border-blue-200` | ❌ Não tem | ✅ `border-gray-200` | ❌ Não tem |
| **Gradiente no Container** | ❌ Não tem | ✅ `bg-gradient-to-br` | ❌ Não tem | ❌ Não tem | ❌ Não tem |
| **Informação Extra no Card** | Apenas nome | Nome + slug | Nome + badges (status/role) | Procedimento + hospital + badges | Thumbnail + status + metadados |
| **Altura do Container** | `h-40 sm:h-48` | `h-40 sm:h-48` | `h-40 sm:h-48` | `h-40 sm:h-48` | Customizado (thumbnail) |
| **Ícone no Card** | ✅ SVG hospital | ✅ SVG clínica | ✅ SVG pessoas | ✅ SVG documento | ❌ Thumbnail/ícone tipo arquivo |
| **Tamanho do Ícone** | `w-16 h-16 sm:w-20 sm:h-20` | `w-16 h-16 sm:w-20 sm:h-20` | `w-16 h-16 sm:w-20 sm:h-20` | `w-16 h-16 sm:w-20 sm:h-20` | Variável (thumbnail) |
| **Cor do Ícone** | `text-blue-500` | `text-blue-600` | `text-blue-500` | `text-blue-500` | Variável (cor do hospital) |
| **Título no Card** | Nome do hospital | Nome da clínica | Nome/email do member | Procedimento | Nome do arquivo |
| **Badges/Status no Card** | ❌ Não tem | ❌ Não tem | ✅ Status + Role | ✅ Pediátrica + Prioridade | ✅ Status com ícone + spinner |
| **Detalhes Adicionais** | ❌ Não tem | Slug abaixo do nome | Badges abaixo do nome | Lista de detalhes (sala, datas, etc) | Metadados (data, tamanho) |
| **Estrutura Visual** | Container grande → Footer | Container grande → Footer | Container grande → Footer | Container grande → Detalhes → Footer | Thumbnail → Status → Metadados/Ações |
| **Paginação** | ✅ `paginationHandlers` | ✅ `paginationHandlers` | ❌ Manual inline | ❌ Manual inline | ❌ Manual inline |
| **Carregamento de Dados** | ✅ Via `useEntityPage` | ✅ Via `useEntityPage` | ❌ Manual (`loadMembers`) | ❌ Manual (`loadDemands`) | ❌ Manual (`loadFiles`) |
| **Filtros** | ❌ Não tem | ❌ Não tem | ✅ Status + Role | ❌ Não tem | ✅ Hospital + Data + Status |
| **Seleção Múltipla** | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim (exclusão + leitura) |
| **Ações Customizadas** | ❌ Não tem | ❌ Não tem | ✅ Enviar convite | ❌ Não tem | ✅ Ler conteúdo |
| **Ordem dos Botões** | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada (customizado) |
| **Estrutura de Erro** | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada (com emailMessage) | ✅ Padronizada | ✅ Padronizada |

---

## 🚨 Aspectos Fora do Padrão

### 1. **Hook de Gerenciamento**

**Fora do padrão:**
- ❌ **Member**: Usa estado manual em vez de `useEntityPage`
- ❌ **Demand**: Usa estado manual em vez de `useEntityPage`
- ❌ **File**: Usa estado manual em vez de `useEntityPage`

**Padrão:**
- ✅ **Hospital**: Usa `useEntityPage`
- ✅ **Tenant**: Usa `useEntityPage`

**Sugestão:**
- Avaliar se Member, Demand e File podem migrar para `useEntityPage`
- Se a complexidade for muito alta, criar hooks especializados que estendam `useEntityPage`
- Documentar quando usar `useEntityPage` vs. estado manual

---

### 2. **Estrutura de Edição**

**✅ PADRONIZADO:**
- ✅ **Hospital**: `EditForm` separado
- ✅ **Tenant**: `EditForm` separado
- ✅ **Member**: `EditForm` separado (migrado)
- ✅ **Demand**: `EditForm` separado
- ✅ **File**: `EditForm` separado

**Status:** ✅ **Implementado** - Member foi migrado para usar `EditForm` separado

---

### 3. **Paginação**

**✅ PADRONIZADO:**
- ✅ **Hospital**: `paginationHandlers` do `useEntityPage`
- ✅ **Tenant**: `paginationHandlers` do `useEntityPage`
- ✅ **Member**: `paginationHandlers` do `usePagination` (migrado)
- ✅ **Demand**: `paginationHandlers` do `usePagination` (migrado)
- ✅ **File**: `paginationHandlers` do `usePagination` (migrado)

**Status:** ✅ **Implementado** - Member, Demand e File agora usam o hook `usePagination` reutilizável

---

### 4. **Estrutura Visual dos Cards**

**Status:**
- ✅ **File**: Estrutura customizada mantida (justificada: thumbnail, status complexo)
- ✅ **Hospital**: Cor dinâmica + borda sutil (`border-gray-200`) (padronizado)
- ✅ **Tenant**: Gradiente fixo + borda (`border-blue-200`)
- ✅ **Member**: Gradiente fixo azul
- ✅ **Demand**: Cor dinâmica + borda sutil (`border-gray-200`) (padronizado)

**Status:** ✅ **Implementado** - Hospital e Demand agora têm borda sutil para consistência visual, mantendo a cor dinâmica funcional

---

### 5. **Filtros**

**Fora do padrão:**
- ❌ **Member**: Usa `editContent` + `filterContent` (mutuamente exclusivos, mas via CardPanel)
- ⚠️ **File**: Filtros customizados (hospital + data) além de status

**Padrão:**
- ✅ **File**: Usa `FilterPanel` e `useEntityFilters` para status
- ✅ **Member**: Usa `FilterPanel` e `useEntityFilters`

**Sugestão:**
- **File**: Manter filtros customizados (hospital + data) dentro do `FilterPanel` (já está correto)
- **Member**: Migrar para `EditForm` separado (remover `editContent`)

---

### 6. **Botões do ActionBar**

**Fora do padrão:**
- ❌ **File**: Customizado com `useMemo` em vez de `useActionBarButtons`

**Padrão:**
- ✅ **Hospital**: Via `useEntityPage`
- ✅ **Tenant**: Via `useEntityPage`
- ✅ **Member**: Via `useActionBarButtons`
- ✅ **Demand**: Via `useActionBarButtons`

**Sugestão:**
- **File**: Avaliar se pode usar `useActionBarButtons` com extensão para suportar `selectedFilesForReading`
- Se não for possível, documentar a customização e garantir que a ordem dos botões seja mantida

---

### 7. **Carregamento de Dados**

**Fora do padrão:**
- ❌ **Member**: Carrega todos os dados de uma vez (múltiplas requisições)
- ❌ **Demand**: Carregamento manual
- ❌ **File**: Carregamento manual

**Padrão:**
- ✅ **Hospital**: Via `useEntityPage`
- ✅ **Tenant**: Via `useEntityPage`

**Sugestão:**
- Se migrar para `useEntityPage`, carregamento será padronizado
- Se manter manual, garantir que siga o mesmo padrão de tratamento de erros

---

## 📋 Resumo de Padronização

### ✅ Implementado

1. ✅ **Member**: Migrado `editContent` para `EditForm` separado
2. ✅ **Member, Demand, File**: Migrados para usar `usePagination` (hook reutilizável)
3. ✅ **Hospital, Demand**: Adicionada borda sutil (`border-gray-200`) nos containers

### 🔄 Pendente (Avaliação)

4. **Member, Demand, File**: Avaliar migração para `useEntityPage` (se viável)
   - **Nota**: Member carrega todos os dados de uma vez (múltiplas requisições) e filtra no frontend
   - **Nota**: Demand e File têm lógica específica que pode não se encaixar em `useEntityPage`

5. **File**: Avaliar se pode usar `useActionBarButtons` (com extensão para `selectedFilesForReading`)
   - **Nota**: File tem seleção dupla (exclusão + leitura), pode precisar de customização

### ✅ Mantido (Justificado)

6. ✅ **File**: Estrutura customizada mantida (thumbnail, status complexo, múltiplas seleções)
7. ✅ **Hospital, Demand**: Cor dinâmica mantida (funcionalidade específica)

---

## ✅ Aspectos Padronizados

- ✅ **Todos usam `EntityCard`** (File migrado - conteúdo customizado)
- ✅ Todos usam `CardFooter` (exceto File, que tem footer customizado com checkbox de leitura)
- ✅ Todos usam `CardActionButtons` (ordem padronizada)
- ✅ **Todos usam `EditForm` separado** (Member migrado)
- ✅ Todos usam `FilterPanel` quando têm filtros
- ✅ Todos usam `useEntityFilters` quando têm filtros
- ✅ **Todos usam `usePagination` ou `paginationHandlers`** (Member, Demand, File migrados)
- ✅ Todos usam `getActionBarErrorProps` (direto ou via hook)
- ✅ Ordem dos botões padronizada (Cancelar → Excluir → Salvar)
- ✅ Estrutura de cards similar (container grande no topo)
- ✅ **Containers com borda** (Hospital e Demand padronizados)

---

## 🎯 Recomendações Finais

### Padrão Ideal (Baseado em Hospital/Tenant)

1. **Hook**: `useEntityPage` (quando possível)
2. **Edição**: `EditForm` separado (nunca `editContent`)
3. **Cards**: `EntityCard` + `CardFooter`
4. **Filtros**: `FilterPanel` + `useEntityFilters`
5. **Botões**: `useActionBarButtons` (ou via `useEntityPage`)
6. **Erros**: `getActionBarErrorProps` (ou via `useEntityPage`)
7. **Paginação**: `paginationHandlers` (ou via `useEntityPage`)
8. **Visual**: Container grande (`h-40 sm:h-48`) com ícone centralizado

### Exceções Justificadas

- **File**: Estrutura customizada (thumbnail, status complexo, múltiplas seleções)
- **Hospital/Demand**: Cor dinâmica (funcionalidade específica)
- **File**: Botões customizados (suporta `selectedFilesForReading`)

### Próximos Passos

1. ✅ ~~Migrar Member para `EditForm` separado~~ **CONCLUÍDO**
2. ✅ ~~Criar hook `usePagination` e aplicar em Member/Demand/File~~ **CONCLUÍDO**
3. ✅ ~~Adicionar borda sutil nos containers de Hospital/Demand~~ **CONCLUÍDO**
4. Avaliar viabilidade de migrar Member/Demand/File para `useEntityPage` (opcional, pode não ser viável devido à complexidade)
5. Avaliar extensão de `useActionBarButtons` para suportar `selectedFilesForReading` (opcional)
6. Documentar padrões e exceções (já documentado neste arquivo)
