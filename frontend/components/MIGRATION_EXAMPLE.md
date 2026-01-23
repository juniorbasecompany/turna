# Exemplo de Migração: Painel Member

Este documento mostra como migrar o painel Member para usar os novos componentes reutilizáveis.

## Antes (Código Atual)

```typescript
// Lógica de botões manual (linhas 747-777)
buttons={(() => {
    const buttons = []
    if (isEditing || selectedMembers.size > 0) {
        buttons.push({
            label: 'Cancelar',
            onClick: handleCancel,
            variant: 'secondary' as const,
            disabled: submitting || deleting,
        })
    }
    if (selectedMembers.size > 0) {
        buttons.push({
            label: 'Remover',
            onClick: handleDeleteSelected,
            variant: 'primary' as const,
            disabled: deleting || submitting,
            loading: deleting,
        })
    }
    if (isEditing && (hasChanges() || sendInvite)) {
        buttons.push({
            label: submitting ? (editingMember ? 'Salvando...' : 'Criando...') : (editingMember ? 'Salvar' : 'Criar'),
            onClick: editingMember ? handleSave : handleCreate,
            variant: 'primary' as const,
            disabled: submitting,
            loading: submitting,
        })
    }
    return buttons
})()}

// Lógica de erro manual (linhas 714-746)
error={(() => {
    if (emailMessage) {
        return undefined
    }
    const hasButtons = isEditing || selectedMembers.size > 0
    return hasButtons ? error : undefined
})()}
message={(() => {
    if (emailMessage) {
        return emailMessage
    }
    const hasButtons = isEditing || selectedMembers.size > 0
    if (!hasButtons && error) {
        return error
    }
    return undefined
})()}
messageType={(() => {
    if (emailMessage) {
        return emailMessageType
    }
    const hasButtons = isEditing || selectedMembers.size > 0
    if (!hasButtons && error) {
        return 'error' as const
    }
    return undefined
})()}

// Estrutura de filtros manual (linhas 611-633)
filterContent={
    !isEditing ? (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="space-y-4">
                <FilterButtons
                    title="Situação"
                    options={statusOptions}
                    selectedValues={selectedStatuses}
                    onToggle={toggleStatus}
                    onToggleAll={toggleAllStatuses}
                />
                <FilterButtons
                    title="Função"
                    options={roleOptions}
                    selectedValues={selectedRoles}
                    onToggle={toggleRole}
                    onToggleAll={toggleAllRoles}
                    allOptionLabel="Todas"
                />
            </div>
        </div>
    ) : undefined
}
```

## Depois (Código Migrado)

### Passo 1: Adicionar Imports

```typescript
import { FilterPanel } from '@/components/FilterPanel'
import { EntityCard } from '@/components/EntityCard'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { getActionBarErrorProps } from '@/lib/entityUtils'
import { useEntityFilters } from '@/hooks/useEntityFilters'
```

### Passo 2: Substituir Lógica de Filtros

```typescript
// Antes: Estado manual
const [selectedStatuses, setSelectedStatuses] = useState<Set<string>>(new Set(['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED']))
const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set(['account', 'admin']))

// Depois: Usar hook
const statusFilters = useEntityFilters({
  allFilters: ['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED'],
  initialFilters: new Set(['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED']),
})

const roleFilters = useEntityFilters({
  allFilters: ['account', 'admin'],
  initialFilters: new Set(['account', 'admin']),
})
```

### Passo 3: Substituir Estrutura de Filtros

```typescript
// Antes: Estrutura manual
filterContent={
    !isEditing ? (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="space-y-4">
                <FilterButtons ... />
                <FilterButtons ... />
            </div>
        </div>
    ) : undefined
}

// Depois: Usar FilterPanel
filterContent={
    !isEditing ? (
        <FilterPanel>
            <FilterButtons
                title="Situação"
                options={statusOptions}
                selectedValues={statusFilters.selectedFilters}
                onToggle={statusFilters.toggleFilter}
                onToggleAll={statusFilters.toggleAll}
            />
            <FilterButtons
                title="Função"
                options={roleOptions}
                selectedValues={roleFilters.selectedFilters}
                onToggle={roleFilters.toggleFilter}
                onToggleAll={roleFilters.toggleAll}
                allOptionLabel="Todas"
            />
        </FilterPanel>
    ) : undefined
}
```

### Passo 4: Substituir Lógica de Botões

```typescript
// Antes: Lógica manual inline
buttons={(() => {
    const buttons = []
    // ... lógica complexa
    return buttons
})()}

// Depois: Usar hook (com customização para sendInvite)
const actionBarButtons = useActionBarButtons({
    isEditing,
    selectedCount: selectedMembers.size,
    hasChanges: hasChanges() || sendInvite, // Customização para sendInvite
    submitting,
    deleting,
    onCancel: handleCancel,
    onDelete: handleDeleteSelected,
    onSave: editingMember ? handleSave : handleCreate,
    saveLabel: editingMember ? 'Salvar' : 'Criar',
    deleteLabel: 'Remover',
})

// No ActionBar:
buttons={actionBarButtons}
```

### Passo 5: Substituir Lógica de Erro

```typescript
// Antes: Lógica manual complexa
error={(() => { /* ... */ })()}
message={(() => { /* ... */ })()}
messageType={(() => { /* ... */ })()}

// Depois: Usar função utilitária (com suporte a emailMessage)
const actionBarErrorProps = getActionBarErrorProps(
    error,
    isEditing,
    selectedMembers.size,
    emailMessage,
    emailMessageType
)

// No ActionBar:
error={actionBarErrorProps.error}
message={actionBarErrorProps.message}
messageType={actionBarErrorProps.messageType}
```

### Passo 6: Substituir Cards (Opcional)

```typescript
// Antes: Card manual
{paginatedMembers.map((member) => {
    const isSelected = selectedMembers.has(member.id)
    return (
        <div
            key={member.id}
            className={getCardContainerClasses(isSelected)}
        >
            <div className="mb-3">
                {/* Conteúdo do card */}
            </div>
            <CardFooter ... />
        </div>
    )
})}

// Depois: Usar EntityCard
{paginatedMembers.map((member) => {
    const isSelected = selectedMembers.has(member.id)
    return (
        <EntityCard
            key={member.id}
            id={member.id}
            isSelected={isSelected}
            footer={
                <CardFooter
                    isSelected={isSelected}
                    date={member.created_at}
                    settings={settings}
                    onToggleSelection={(e) => {
                        e.stopPropagation()
                        toggleMemberSelection(member.id)
                    }}
                    onEdit={() => handleEditClick(member)}
                    disabled={deleting}
                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                    editTitle="Editar associação"
                />
            }
        >
            <div className="mb-3">
                {/* Conteúdo do card (mantém customização) */}
                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-blue-50">
                    {/* ... */}
                </div>
            </div>
        </EntityCard>
    )
})}
```

## Resultado Final

### Redução de Código:
- **Antes:** ~150 linhas de lógica repetitiva
- **Depois:** ~30 linhas usando componentes reutilizáveis
- **Redução:** ~80% menos código

### Benefícios:
1. ✅ Código mais limpo e legível
2. ✅ Lógica centralizada e testável
3. ✅ Consistência garantida entre painéis
4. ✅ Manutenção mais fácil
5. ✅ Novos painéis seguem o padrão automaticamente

## Checklist de Migração

- [ ] Adicionar imports dos novos componentes
- [ ] Substituir lógica de filtros por `useEntityFilters`
- [ ] Substituir estrutura de filtros por `FilterPanel`
- [ ] Substituir lógica de botões por `useActionBarButtons`
- [ ] Substituir lógica de erro por `getActionBarErrorProps`
- [ ] Substituir cards por `EntityCard` (opcional)
- [ ] Testar todas as funcionalidades
- [ ] Validar visualmente
- [ ] Commit: `refactor: migrate member page to use reusable components`
