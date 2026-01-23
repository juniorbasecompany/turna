# 📊 Tabela Comparativa Completa dos Painéis

## Comparação Detalhada: Hospital, Tenant, Member, Demand, File

| Aspecto | Hospital | Tenant (Clínicas) | Member (Associados) | Demand (Demandas) | File (Arquivos) |
|---------|----------|-------------------|---------------------|-------------------|-----------------|
| **Hook de Gerenciamento** | ✅ `useEntityPage` | ✅ `useEntityPage` | ✅ `useEntityPage` | ✅ `useEntityPage` | ✅ `useEntityPage` |
| **EntityCard** | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa (conteúdo customizado) |
| **CardFooter** | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa (com `secondaryText` e `beforeActions`) |
| **CardActionButtons** | ✅ (via CardFooter) | ✅ (via CardFooter) | ✅ (via CardFooter) | ✅ (via CardFooter) | ✅ (via CardFooter) |
| **EditForm** | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa | ✅ Usa |
| **FilterPanel** | ✅ Usa (filtro por nome) | ✅ Usa (filtro por nome) | ✅ Usa | ✅ Usa (filtro por procedimento) | ✅ Usa |
| **useEntityFilters** | ❌ N/A (filtro de texto) | ❌ N/A (filtro de texto) | ✅ Usa | ❌ N/A (filtro de texto) | ✅ Usa |
| **useActionBarButtons** | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ Usa diretamente | ✅ Usa diretamente | ✅ Usa diretamente (com extensões) |
| **getActionBarErrorProps** | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ Usa diretamente |
| **paginationHandlers** | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ (via useEntityPage) | ✅ (via useEntityPage) |
| **Estrutura de Edição** | ✅ `EditForm` separado | ✅ `EditForm` separado | ✅ `EditForm` separado | ✅ `EditForm` separado | ✅ `EditForm` separado |
| **Filtros vs Edição** | ✅ Mutuamente exclusivos | ✅ Mutuamente exclusivos | ✅ Mutuamente exclusivos | ✅ Mutuamente exclusivos | ✅ Mutuamente exclusivos |
| **Container do Card** | Cor dinâmica (`hospital.color`) | Cor sólida azul (`bg-blue-50`) | Cor sólida azul (`bg-blue-50`) | Cor dinâmica (`hospital.color`) | Cor dinâmica (`hospital.color`) com thumbnail |
| **Borda no Container** | ✅ `border-blue-200` | ✅ `border-blue-200` | ✅ `border-blue-200` | ✅ `border-blue-200` | ✅ `border-blue-200` |
| **Gradiente no Container** | ❌ Não tem | ❌ Não tem | ❌ Não tem | ❌ Não tem | ❌ Não tem |
| **Informação Extra no Card** | Apenas nome | Nome + slug | Nome + badges (status/role) | Procedimento + hospital + badges | Thumbnail + status + metadados |
| **Altura do Container** | `h-40 sm:h-48` | `h-40 sm:h-48` | `h-40 sm:h-48` | `h-40 sm:h-48` | ✅ `h-40 sm:h-48` |
| **Ícone no Card** | ✅ SVG hospital | ✅ SVG clínica | ✅ SVG pessoas | ✅ SVG documento | ❌ Thumbnail/ícone tipo arquivo |
| **Tamanho do Ícone** | `w-16 h-16 sm:w-20 sm:h-20` | `w-16 h-16 sm:w-20 sm:h-20` | `w-16 h-16 sm:w-20 sm:h-20` | `w-16 h-16 sm:w-20 sm:h-20` | Variável (thumbnail) |
| **Cor do Ícone** | `text-blue-500` | `text-blue-600` | `text-blue-600` | `text-blue-500` | Variável (cor do hospital) |
| **Título no Card** | Nome do hospital | Nome da clínica | Nome/email do member | Procedimento | Nome do arquivo |
| **Badges/Status no Card** | ❌ Não tem | ❌ Não tem | ✅ Status + Role | ✅ Pediátrica + Prioridade | ✅ Status com ícone + spinner |
| **Detalhes Adicionais** | ❌ Não tem | Slug abaixo do nome | Badges abaixo do nome | Lista de detalhes (sala, datas, etc) | Metadados (data, tamanho) |
| **Estrutura Visual** | Container grande → Footer | Container grande → Footer | Container grande → Footer | Container grande → Footer | Container grande → Footer |
| **Conteúdo dentro do Container** | Ícone + Nome | Ícone + Nome + Slug | Ícone + Nome + Badges | Ícone + Nome + Badges + Detalhes | Topo (hospital + nome) + Thumbnail + Status |
| **Paginação** | ✅ `paginationHandlers` | ✅ `paginationHandlers` | ✅ `paginationHandlers` | ✅ `paginationHandlers` | ✅ `paginationHandlers` |
| **Uso de paginationHandlers** | ✅ Via objeto | ✅ Via objeto | ✅ Via objeto | ✅ Via objeto | ✅ Via objeto |
| **Carregamento de Dados** | ✅ Via `useEntityPage` | ✅ Via `useEntityPage` | ✅ Via `useEntityPage` | ✅ Via `useEntityPage` | ✅ Via `useEntityPage` |
| **Filtros** | ✅ Nome (texto) | ✅ Nome (texto) | ✅ Status + Role | ✅ Procedimento (texto) | ✅ Hospital + Data + Status |
| **Seleção Múltipla** | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim (exclusão + leitura) |
| **Ações Customizadas** | ❌ Não tem | ❌ Não tem | ✅ Enviar convite | ❌ Não tem | ✅ Ler conteúdo |
| **Ordem dos Botões** | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada (com ação customizada) |
| **Estrutura de Erro** | ✅ Padronizada | ✅ Padronizada | ✅ Padronizada (com emailMessage) | ✅ Padronizada | ✅ Padronizada |

---

## 🚨 Aspectos Fora do Padrão

### 1. **Hook de Gerenciamento**

**✅ PADRONIZADO:**
- ✅ **Hospital**: Usa `useEntityPage`
- ✅ **Tenant**: Usa `useEntityPage`
- ✅ **Member**: Usa `useEntityPage` (migrado)
- ✅ **Demand**: Usa `useEntityPage` (migrado)
- ✅ **File**: Usa `useEntityPage` (migrado)

**Status:** ✅ **Implementado** - Todos os painéis agora usam `useEntityPage` para gerenciamento de estado e dados

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
- ✅ **Member**: `paginationHandlers` do `useEntityPage` (migrado)
- ✅ **Demand**: `paginationHandlers` do `useEntityPage` (migrado)
- ✅ **File**: `paginationHandlers` do `useEntityPage` (migrado)

**Status:** ✅ **Implementado** - Todos os painéis agora usam `paginationHandlers` via `useEntityPage`

---

### 4. **Estrutura Visual dos Cards**

**✅ PADRONIZADO:**

**Estrutura Visual:**
- ✅ **Todos os painéis**: `Container grande → Footer`
- ✅ **Detalhes, thumbnails e status**: Sempre dentro do container grande

**Opções de Cor do Container:**

**Opção 1 - Cor dinâmica do hospital:**
- ✅ **Hospital**: `backgroundColor: hospital.color` + `border-blue-200`
- ✅ **Demand**: `backgroundColor: hospital.color` + `border-blue-200` (com detalhes dentro)
- ✅ **File**: `backgroundColor: hospital.color` + `border-blue-200` (com thumbnail e status dentro)

**Opção 2 - Cor sólida azul:**
- ✅ **Tenant**: `bg-blue-50` + `border-blue-200`
- ✅ **Member**: `bg-blue-50` + `border-blue-200` (com badges dentro)

**Status:** ✅ **Implementado** - Todos os painéis seguem a estrutura padronizada "Container grande → Footer". Elementos especiais (detalhes, thumbnails, status, badges) estão sempre dentro do container grande.

---

### 5. **Filtros**

**✅ PADRONIZADO:**
- ✅ **Hospital**: Usa `FilterPanel` com filtro de texto por nome
- ✅ **Tenant**: Usa `FilterPanel` com filtro de texto por nome
- ✅ **Member**: Usa `FilterPanel` e `useEntityFilters` (Status + Role)
- ✅ **Demand**: Usa `FilterPanel` com filtro de texto por procedimento
- ✅ **File**: Usa `FilterPanel` e `useEntityFilters` para status + filtros customizados (hospital + data)

**Status:** ✅ **Implementado** - Todos os painéis agora têm filtros padronizados usando `FilterPanel`

---

### 6. **Botões do ActionBar**

**✅ PADRONIZADO:**
- ✅ **Hospital**: Via `useEntityPage` (indireto)
- ✅ **Tenant**: Via `useEntityPage` (indireto)
- ✅ **Member**: Via `useActionBarButtons` (direto)
- ✅ **Demand**: Via `useActionBarButtons` (direto)
- ✅ **File**: Via `useActionBarButtons` (direto, com extensões para ações customizadas)

**Status:** ✅ **Implementado** - File agora usa `useActionBarButtons` com extensões para suportar `selectedFilesForReading` e ação customizada "Ler conteúdo"

---

### 7. **Carregamento de Dados**

**✅ PADRONIZADO:**
- ✅ **Hospital**: Via `useEntityPage`
- ✅ **Tenant**: Via `useEntityPage`
- ✅ **Member**: Via `useEntityPage` (migrado, com `additionalListParams` reativo para filtros)
- ✅ **Demand**: Via `useEntityPage` (migrado)
- ✅ **File**: Via `useEntityPage` (migrado, com `additionalListParams` reativo para filtros)

**Status:** ✅ **Implementado** - Todos os painéis agora usam `useEntityPage` para carregamento de dados. Member e File usam `additionalListParams` reativo para suportar filtros dinâmicos.

---

## 📋 Resumo de Padronização

### ✅ Implementado

1. ✅ **Member**: Migrado `editContent` para `EditForm` separado
2. ✅ **Member, Demand, File**: Migrados para usar `useEntityPage` (hook completo de gerenciamento)
3. ✅ **Hospital, Demand**: Adicionada borda padronizada (`border-blue-200`) nos containers
4. ✅ **File**: Migrado para usar `EntityCard` e `CardFooter` (conteúdo customizado mantido via props)
5. ✅ **Hospital, Tenant, Demand**: Adicionados filtros de texto (nome/procedimento) usando `FilterPanel`
6. ✅ **File**: Migrado para usar `useActionBarButtons` (com extensões para ações customizadas)
7. ✅ **Member, Demand, File**: Padronizado uso de `paginationHandlers` via `useEntityPage`
8. ✅ **Member, Tenant**: Removido gradiente, substituído por cor sólida `bg-blue-50`
9. ✅ **File**: Migrado para container padronizado `h-40 sm:h-48` com `border-blue-200` (thumbnail dentro do container)
10. ✅ **getCardContainerClasses**: Padronizado para retornar `border-blue-200` (aplica a todos os painéis via `EntityCard`)

### ✅ Concluído Recentemente

4. ✅ **Member, Demand, File**: Migrados para `useEntityPage`
   - ✅ **Member**: Migrado com suporte a `additionalListParams` reativo para filtros dinâmicos (Status + Role)
   - ✅ **Demand**: Migrado com filtro de texto no frontend
   - ✅ **File**: Migrado com suporte a `additionalListParams` reativo para filtros dinâmicos (Hospital + Data + Status)

5. ✅ **File**: Usa `useActionBarButtons` com extensões para `selectedFilesForReading`
   - **Nota**: File tem seleção dupla (exclusão + leitura), implementado via extensões no hook

### ✅ Mantido (Justificado)

6. ✅ **File**: Estrutura customizada mantida (thumbnail, status complexo, múltiplas seleções)
7. ✅ **Hospital, Demand**: Cor dinâmica mantida (funcionalidade específica)

---

## ✅ Aspectos Padronizados

- ✅ **Todos usam `EntityCard`** (File migrado - conteúdo customizado)
- ✅ **Todos usam `CardFooter`** (File migrado - com props `secondaryText` e `beforeActions` para checkbox de leitura)
- ✅ Todos usam `CardActionButtons` (ordem padronizada)
- ✅ **Todos usam `EditForm` separado** (Member migrado)
- ✅ **Todos usam `FilterPanel`** (Hospital, Tenant, Demand, Member, File - todos têm filtros)
- ✅ **Filtros vs Edição mutuamente exclusivos** (todos os painéis)
- ✅ Todos usam `useEntityFilters` quando têm filtros de seleção (Member, File)
- ✅ **Todos usam `useActionBarButtons`** (File migrado - com extensões para ações customizadas)
- ✅ **Todos usam `paginationHandlers` via `useEntityPage`** (padronizado em todos os painéis)
- ✅ Todos usam `getActionBarErrorProps` (via `useEntityPage` ou diretamente quando necessário)
- ✅ Ordem dos botões padronizada (Cancelar → Excluir → Salvar → Ações customizadas)
- ✅ **Estrutura visual padronizada** (Container grande → Footer, com detalhes/thumbnails/status dentro do container)
- ✅ **Containers padronizados** (Cor dinâmica OU Cor sólida azul `bg-blue-50`, ambos com `border-blue-200`)
- ✅ **Altura padronizada** (`h-40 sm:h-48` em todos os painéis, incluindo File)
- ✅ **Borda padronizada** (`border-blue-200` via `getCardContainerClasses` aplicado a todos via `EntityCard`)

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
8. **Visual**: Estrutura padronizada (Container grande → Footer)
9. **Container**: Altura `h-40 sm:h-48`, borda `border-blue-200`, cor dinâmica ou sólida
10. **Conteúdo do Container**: Detalhes, thumbnails, status e badges sempre dentro do container grande

### Exceções Justificadas

- **File**: Thumbnail dentro do container padronizado (mantém funcionalidade visual específica)
- **Hospital/Demand/File**: Cor dinâmica (funcionalidade específica)
- **File**: Botões customizados (suporta `selectedFilesForReading`)

### Próximos Passos

1. ✅ ~~Migrar Member para `EditForm` separado~~ **CONCLUÍDO**
2. ✅ ~~Migrar Member/Demand/File para usar `useEntityPage`~~ **CONCLUÍDO**
3. ✅ ~~Adicionar borda sutil nos containers de Hospital/Demand~~ **CONCLUÍDO**
4. ✅ ~~Migrar File para usar `EntityCard`~~ **CONCLUÍDO**
5. ✅ ~~Migrar File para usar `CardFooter`~~ **CONCLUÍDO**
6. ✅ ~~Adicionar filtros de texto em Hospital, Tenant e Demand~~ **CONCLUÍDO**
7. ✅ ~~Estender `useActionBarButtons` e migrar File para usá-lo~~ **CONCLUÍDO**
8. ✅ ~~Padronizar `paginationHandlers` via `useEntityPage` em todos os painéis~~ **CONCLUÍDO**
9. ✅ ~~Padronizar containers dos cards (gradiente removido, substituído por cor sólida)~~ **CONCLUÍDO**
10. ✅ ~~Padronizar borda dos containers em `border-blue-200` (via `getCardContainerClasses`)~~ **CONCLUÍDO**
11. ✅ ~~Padronizar File para usar container `h-40 sm:h-48` com `border-blue-200`~~ **CONCLUÍDO**
12. ✅ ~~Migrar Member/Demand/File para `useEntityPage`~~ **CONCLUÍDO**
13. ✅ Documentar padrões e exceções (já documentado neste arquivo)
