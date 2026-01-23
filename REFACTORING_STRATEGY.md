# Estratégia de Refatoração dos Painéis

## 📊 Análise dos Padrões Identificados

### 1. **Código Repetido Identificado**

#### A. Lógica de Botões do ActionBar
**Problema:** Cada painel implementa a mesma lógica de botões manualmente:
- Member: `buttons.push()` com lógica condicional (linhas 747-777)
- Demand: `buttons.push()` com lógica condicional (linhas 735-767)
- File: `buttons.push()` com lógica condicional (linhas 1768-1791)
- Hospital: ✅ Já usa `useActionBarButtons` (exemplo correto)

**Solução:** Todos devem usar `useActionBarButtons` (já existe, mas não está sendo usado em Member/Demand/File)

#### B. Estrutura de Filtros
**Problema:** Cada painel cria sua própria estrutura de filtros:
- Member: Wrapper manual com `filterContent` (linhas 611-633)
- Demand: Não usa CardPanel, estrutura manual
- File: Estrutura manual com condicional `!showEditArea` (linhas 1349-1415)
- Hospital: Não tem filtros

**Solução:** Criar componente `FilterPanel` que encapsula a estrutura

#### C. Lógica de Erro do ActionBar
**Problema:** Lógica repetida para determinar quando mostrar erro:
- Member: Lógica complexa com emailMessage (linhas 714-746)
- Demand: Lógica similar (linhas 680-710)
- File: Lógica similar (linhas 1747-1767)
- Hospital: ✅ Já usa `getActionBarErrorProps` (exemplo correto)

**Solução:** Todos devem usar `getActionBarErrorProps` (já existe)

#### D. Estrutura de Cards
**Problema:** Cada painel renderiza cards de forma diferente:
- Member: Card customizado com ícone SVG inline (linhas 635-694)
- Demand: Card customizado
- File: Card customizado com thumbnail
- Hospital: Card customizado com cor de fundo

**Solução:** Criar componente `EntityCard` genérico com slots para customização

#### E. Paginação
**Problema:** Lógica de paginação repetida:
- Member: Implementação manual (linhas 700-712)
- Demand: Implementação manual
- File: Implementação manual (linhas 1733-1745)
- Hospital: ✅ Já usa `paginationHandlers` do hook (exemplo correto)

**Solução:** Todos devem usar `paginationHandlers` do `useEntityPage`

---

## 🎯 Componentes Reutilizáveis Propostos

### 1. **EntityPage** (Componente de Alto Nível)
Componente que orquestra todo o painel, encapsulando:
- CardPanel
- ActionBar
- ActionBarSpacer
- Lógica de filtros vs edição
- Paginação

**Interface:**
```typescript
interface EntityPageProps<TEntity, TFormData> {
  // Configuração
  title: string
  description: string
  entityName: string
  
  // Dados
  items: TEntity[]
  total: number
  loading: boolean
  error: string | null
  
  // Estados
  isEditing: boolean
  selectedCount: number
  
  // Filtros
  filterContent?: ReactNode
  
  // Edição
  editContent?: ReactNode
  
  // Cards
  createCard?: ReactNode
  renderCard: (item: TEntity) => ReactNode
  
  // ActionBar
  actionBarButtons: ActionButton[]
  actionBarErrorProps: ActionBarErrorProps
  pagination?: ReactNode
}
```

### 2. **FilterPanel** (Wrapper de Filtros)
Componente que encapsula a estrutura padrão de filtros:
- Container branco com borda
- Espaçamento consistente
- Suporte a múltiplos FilterButtons
- Validação de filtros (ex: datas)

**Interface:**
```typescript
interface FilterPanelProps {
  children: ReactNode
  validationErrors?: ReactNode
  className?: string
}
```

### 3. **EntityCard** (Card Genérico)
Componente base para cards de entidades com slots para customização:
- Container com classes de seleção
- Slot para conteúdo principal (corpo do card)
- Slot para rodapé (usa CardFooter por padrão)
- Suporte a onClick para seleção

**Interface:**
```typescript
interface EntityCardProps {
  id: number
  isSelected: boolean
  onClick?: () => void
  children: ReactNode
  footer?: ReactNode
  className?: string
}
```

### 4. **useEntityFilters** (Hook para Filtros)
Hook que gerencia estado e lógica de filtros:
- Estado de filtros selecionados
- Funções de toggle
- Funções de toggle all
- Validação de filtros

**Interface:**
```typescript
interface UseEntityFiltersOptions<T> {
  initialFilters: Set<T>
  onFilterChange?: (filters: Set<T>) => void
}

interface UseEntityFiltersReturn<T> {
  selectedFilters: Set<T>
  toggleFilter: (value: T) => void
  toggleAll: () => void
  clearFilters: () => void
  isAllSelected: boolean
}
```

---

## 🔄 Estratégia de Migração Segura

### Fase 1: Preparação (Sem Breaking Changes)

#### 1.1 Criar Componentes Novos (Paralelos)
- ✅ Criar `FilterPanel.tsx` (novo componente)
- ✅ Criar `EntityCard.tsx` (novo componente)
- ✅ Criar `useEntityFilters.ts` (novo hook)
- ✅ Criar `EntityPage.tsx` (novo componente)

**Regra:** Não modificar componentes existentes ainda.

#### 1.2 Testar Componentes em Isolamento
- Criar página de teste (`/test-entity-page`)
- Validar que os novos componentes funcionam corretamente
- Garantir que seguem os padrões visuais existentes

### Fase 2: Migração Gradual (Um Painel por Vez)

#### 2.1 Migrar Hospital (Mais Simples)
**Por quê:** Já usa `useEntityPage`, é o mais simples.

**Passos:**
1. Substituir estrutura manual por `EntityPage`
2. Testar todas as funcionalidades
3. Validar visualmente
4. Commit: `refactor: migrate hospital page to EntityPage`

#### 2.2 Migrar Member
**Passos:**
1. Substituir lógica de botões por `useActionBarButtons`
2. Substituir lógica de erro por `getActionBarErrorProps`
3. Substituir estrutura de filtros por `FilterPanel`
4. Substituir cards por `EntityCard`
5. Substituir paginação manual por `paginationHandlers`
6. Testar todas as funcionalidades
7. Validar visualmente
8. Commit: `refactor: migrate member page to useEntityPage pattern`

#### 2.3 Migrar Demand
**Passos:** Similar ao Member, mas manter estrutura de edição fora do CardPanel (já está assim)

#### 2.4 Migrar File (Mais Complexo)
**Passos:**
1. Primeiro: migrar lógica de botões e erro
2. Depois: migrar estrutura de filtros
3. Por último: considerar migração completa para EntityPage (pode manter estrutura customizada se necessário)

### Fase 3: Limpeza

#### 3.1 Remover Código Duplicado
- Remover implementações manuais de botões
- Remover implementações manuais de erro
- Remover estruturas de filtros manuais

#### 3.2 Documentação
- Atualizar documentação dos componentes
- Criar exemplos de uso
- Documentar padrões para novos painéis

---

## 📝 Implementação dos Componentes

### 1. FilterPanel Component

```typescript
// frontend/components/FilterPanel.tsx
'use client'

import { ReactNode } from 'react'

interface FilterPanelProps {
  children: ReactNode
  validationErrors?: ReactNode
  className?: string
}

export function FilterPanel({ children, validationErrors, className = '' }: FilterPanelProps) {
  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 sm:p-6 mb-4 sm:mb-6 ${className}`}>
      <div className="space-y-4">
        {children}
      </div>
      {validationErrors}
    </div>
  )
}
```

### 2. EntityCard Component

```typescript
// frontend/components/EntityCard.tsx
'use client'

import { ReactNode } from 'react'
import { getCardContainerClasses } from '@/lib/cardStyles'

interface EntityCardProps {
  id: number
  isSelected: boolean
  onClick?: () => void
  children: ReactNode
  footer?: ReactNode
  className?: string
}

export function EntityCard({ 
  id, 
  isSelected, 
  onClick, 
  children, 
  footer,
  className = '' 
}: EntityCardProps) {
  return (
    <div
      key={id}
      className={`${getCardContainerClasses(isSelected)} ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
      {footer}
    </div>
  )
}
```

### 3. useEntityFilters Hook

```typescript
// frontend/hooks/useEntityFilters.ts
import { useState, useCallback, useMemo } from 'react'

interface UseEntityFiltersOptions<T> {
  initialFilters?: Set<T>
  allFilters: T[]
  onFilterChange?: (filters: Set<T>) => void
}

interface UseEntityFiltersReturn<T> {
  selectedFilters: Set<T>
  toggleFilter: (value: T) => void
  toggleAll: () => void
  clearFilters: () => void
  isAllSelected: boolean
}

export function useEntityFilters<T>({
  initialFilters = new Set(),
  allFilters,
  onFilterChange,
}: UseEntityFiltersOptions<T>): UseEntityFiltersReturn<T> {
  const [selectedFilters, setSelectedFilters] = useState<Set<T>>(initialFilters)

  const toggleFilter = useCallback((value: T) => {
    setSelectedFilters((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(value)) {
        newSet.delete(value)
      } else {
        newSet.add(value)
      }
      
      if (onFilterChange) {
        onFilterChange(newSet)
      }
      
      return newSet
    })
  }, [onFilterChange])

  const isAllSelected = useMemo(() => {
    return allFilters.every((filter) => selectedFilters.has(filter))
  }, [allFilters, selectedFilters])

  const toggleAll = useCallback(() => {
    setSelectedFilters((prev) => {
      const newSet = isAllSelected ? new Set<T>() : new Set(allFilters)
      
      if (onFilterChange) {
        onFilterChange(newSet)
      }
      
      return newSet
    })
  }, [allFilters, isAllSelected, onFilterChange])

  const clearFilters = useCallback(() => {
    setSelectedFilters(new Set())
    if (onFilterChange) {
      onFilterChange(new Set())
    }
  }, [onFilterChange])

  return {
    selectedFilters,
    toggleFilter,
    toggleAll,
    clearFilters,
    isAllSelected,
  }
}
```

### 4. EntityPage Component (Opcional - Para Casos Simples)

```typescript
// frontend/components/EntityPage.tsx
'use client'

import { ReactNode } from 'react'
import { CardPanel } from './CardPanel'
import { ActionBar, ActionBarSpacer } from './ActionBar'
import { ActionButton } from './ActionBar'

interface ActionBarErrorProps {
  error?: string | null
  message?: string | null
  messageType?: 'info' | 'success' | 'warning' | 'error'
}

interface EntityPageProps<TEntity> {
  // Configuração
  title: string
  description: string
  
  // Dados
  items: TEntity[]
  total: number
  loading: boolean
  error: string | null
  
  // Estados
  isEditing: boolean
  selectedCount: number
  
  // Filtros
  filterContent?: ReactNode
  
  // Edição
  editContent?: ReactNode
  
  // Cards
  createCard?: ReactNode
  renderCard: (item: TEntity) => ReactNode
  
  // ActionBar
  actionBarButtons: ActionButton[]
  actionBarErrorProps: ActionBarErrorProps
  pagination?: ReactNode
  
  // Opcional
  emptyMessage?: string
  loadingMessage?: string
}

export function EntityPage<TEntity extends { id: number }>({
  title,
  description,
  items,
  total,
  loading,
  error,
  isEditing,
  selectedCount,
  filterContent,
  editContent,
  createCard,
  renderCard,
  actionBarButtons,
  actionBarErrorProps,
  pagination,
  emptyMessage = 'Nenhum item cadastrado ainda.',
  loadingMessage = 'Carregando...',
}: EntityPageProps<TEntity>) {
  return (
    <>
      <CardPanel
        title={title}
        description={description}
        totalCount={items.length}
        selectedCount={selectedCount}
        loading={loading}
        loadingMessage={loadingMessage}
        emptyMessage={emptyMessage}
        error={error}
        filterContent={filterContent}
        editContent={editContent}
        createCard={createCard}
      >
        {items.map(renderCard)}
      </CardPanel>

      <ActionBarSpacer />

      <ActionBar
        pagination={pagination}
        error={actionBarErrorProps.error}
        message={actionBarErrorProps.message}
        messageType={actionBarErrorProps.messageType}
        buttons={actionBarButtons}
      />
    </>
  )
}
```

---

## ✅ Checklist de Migração por Painel

### Para cada painel:

- [ ] Substituir lógica de botões por `useActionBarButtons`
- [ ] Substituir lógica de erro por `getActionBarErrorProps`
- [ ] Substituir estrutura de filtros por `FilterPanel`
- [ ] Substituir cards por `EntityCard` (ou manter customizado se necessário)
- [ ] Substituir paginação manual por `paginationHandlers`
- [ ] Testar todas as funcionalidades:
  - [ ] Criar item
  - [ ] Editar item
  - [ ] Excluir item(s)
  - [ ] Filtrar itens
  - [ ] Paginar
  - [ ] Selecionar itens
- [ ] Validar visualmente
- [ ] Commit com mensagem descritiva

---

## 🎓 Padrão para Novos Painéis

### Template Básico:

```typescript
export default function NewEntityPage() {
  const {
    items,
    loading,
    error,
    isEditing,
    selectedCount,
    formData,
    setFormData,
    actionBarButtons,
    actionBarErrorProps,
    paginationHandlers,
    // ... outros
  } = useEntityPage({ /* config */ })

  return (
    <>
      <CardPanel
        title="Nova Entidade"
        description="..."
        filterContent={!isEditing ? (
          <FilterPanel>
            <FilterButtons {...filterProps} />
          </FilterPanel>
        ) : undefined}
        editContent={isEditing ? <EditForm>...</EditForm> : undefined}
        createCard={<CreateCard />}
      >
        {items.map(item => (
          <EntityCard
            key={item.id}
            id={item.id}
            isSelected={selectedItems.has(item.id)}
            footer={<CardFooter {...footerProps} />}
          >
            {/* Conteúdo do card */}
          </EntityCard>
        ))}
      </CardPanel>

      <ActionBarSpacer />
      <ActionBar
        buttons={actionBarButtons}
        {...actionBarErrorProps}
        pagination={<Pagination {...paginationHandlers} />}
      />
    </>
  )
}
```

---

## 🚨 Regras de Segurança

1. **Nunca modificar componentes existentes sem migrar primeiro**
2. **Sempre testar em isolamento antes de integrar**
3. **Migrar um painel por vez**
4. **Manter funcionalidades existentes intactas**
5. **Validar visualmente após cada migração**
6. **Commits pequenos e descritivos**
7. **Documentar mudanças significativas**

---

## 📈 Benefícios Esperados

1. **Redução de código duplicado:** ~40-60% menos código por painel
2. **Consistência:** Todos os painéis seguem o mesmo padrão
3. **Manutenibilidade:** Mudanças em um lugar afetam todos
4. **Novos painéis:** Criação mais rápida seguindo o template
5. **Testabilidade:** Componentes isolados são mais fáceis de testar
6. **Onboarding:** Novos desenvolvedores entendem o padrão rapidamente
