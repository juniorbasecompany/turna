import { useMemo } from 'react'

interface ActionButton {
    label: string
    onClick: () => void
    variant: 'primary' | 'secondary' | 'danger'
    disabled?: boolean
    loading?: boolean
}

interface CustomAction {
    label: string
    onClick: () => void
    disabled?: boolean
    loading?: boolean
}

interface UseActionBarRightButtonsOptions {
    isEditing: boolean
    selectedCount: number
    hasChanges: boolean
    submitting: boolean
    deleting: boolean
    onCancel: () => void
    onDelete: () => void
    onSave: () => void
    saveLabel?: string
    deleteLabel?: string
    cancelLabel?: string
    // Extensões opcionais para casos específicos (ex: File)
    showEditArea?: boolean // Alternativa a isEditing (para File)
    additionalSelectedCount?: number // Seleção adicional (ex: selectedFilesForReading)
    additionalStates?: {
        reading?: boolean
        [key: string]: boolean | undefined
    }
    customActions?: CustomAction[] // Ações customizadas (ex: "Ler conteúdo")
    hideDefaultDelete?: boolean // Se true, oculta o botão "Excluir" padrão (útil quando usando customActions)
}

/**
 * Hook para gerar botões padronizados do ActionBar (lado direito).
 *
 * Ordem padronizada dos botões (sempre nesta ordem):
 * 1. Cancelar (secondary) - aparece quando há edição OU seleção
 * 2. Excluir (primary) - aparece quando há seleção
 * 3. Salvar (primary) - aparece quando há edição com mudanças
 * 4. Ações customizadas (primary) - aparecem conforme definido
 *
 * Esta ordem garante consistência visual em todos os painéis.
 *
 * @example
 * ```tsx
 * // Uso básico (Hospital, Tenant, Member, Demand)
 * const actionBarButtons = useActionBarRightButtons({
 *   isEditing,
 *   selectedCount: selectedItems.size,
 *   hasChanges: hasChanges(),
 *   submitting,
 *   deleting,
 *   onCancel: handleCancel,
 *   onDelete: handleDeleteSelected,
 *   onSave: handleSave,
 * })
 *
 * // Uso com extensões (File)
 * const actionBarButtons = useActionBarRightButtons({
 *   isEditing: showEditArea, // ou usar showEditArea diretamente
 *   selectedCount: selectedFiles.size,
 *   hasChanges: hasChanges(),
 *   submitting,
 *   deleting,
 *   showEditArea, // flag alternativa
 *   additionalSelectedCount: selectedFilesForReading.size,
 *   additionalStates: { reading },
 *   customActions: [
 *     {
 *       label: 'Ler conteúdo',
 *       onClick: handleReadSelected,
 *       disabled: reading || submitting,
 *       loading: reading,
 *     },
 *   ],
 *   onCancel: handleCancel,
 *   onDelete: handleDeleteSelected,
 *   onSave: handleSave,
 * })
 * ```
 */

export function useActionBarRightButtons(options: UseActionBarRightButtonsOptions): ActionButton[] {
    const {
        isEditing,
        selectedCount,
        hasChanges,
        submitting,
        deleting,
        onCancel,
        onDelete,
        onSave,
        saveLabel = 'Salvar',
        deleteLabel = 'Excluir',
        cancelLabel = 'Cancelar',
        showEditArea,
        additionalSelectedCount = 0,
        additionalStates = {},
        customActions = [],
        hideDefaultDelete = false,
    } = options

    // Usar showEditArea se fornecido, caso contrário usar isEditing
    const editing = showEditArea !== undefined ? showEditArea : isEditing

    // Contar todas as seleções (principal + adicional)
    const totalSelectedCount = selectedCount + additionalSelectedCount

    // Verificar estados adicionais para desabilitar botões
    const additionalDisabled = Object.values(additionalStates).some((state) => state === true)

    return useMemo(() => {
        const buttons: ActionButton[] = []

        // Ordem padronizada dos botões:
        // 1. Cancelar (secondary) - sempre primeiro quando aparece
        // 2. Excluir (primary) - quando há seleção principal
        // 3. Salvar (primary) - quando há edição com mudanças
        // 4. Ações customizadas (primary) - quando há seleção adicional ou condições específicas

        // Botão Cancelar (aparece se houver edição OU qualquer seleção)
        if (editing || totalSelectedCount > 0) {
            buttons.push({
                label: cancelLabel,
                onClick: onCancel,
                variant: 'secondary',
                disabled: submitting || deleting || additionalDisabled,
            })
        }

        // Botão Excluir (aparece se houver seleção principal, a menos que hideDefaultDelete seja true)
        if (selectedCount > 0 && !hideDefaultDelete) {
            buttons.push({
                label: deleteLabel,
                onClick: onDelete,
                variant: 'danger',
                disabled: deleting || submitting,
                loading: deleting,
            })
        }

        // Botão Salvar (aparece se houver edição com mudanças)
        if (editing && hasChanges) {
            buttons.push({
                label: submitting ? 'Salvando...' : saveLabel,
                onClick: onSave,
                variant: 'primary',
                disabled: submitting,
                loading: submitting,
            })
        }

        // Ações customizadas (ex: "Ler conteúdo" para File)
        customActions.forEach((action) => {
            buttons.push({
                label: action.label,
                onClick: action.onClick,
                variant: 'primary',
                disabled: action.disabled,
                loading: action.loading,
            })
        })

        return buttons
    }, [
        editing,
        selectedCount,
        totalSelectedCount,
        hasChanges,
        submitting,
        deleting,
        additionalDisabled,
        onCancel,
        onDelete,
        onSave,
        saveLabel,
        deleteLabel,
        cancelLabel,
        customActions,
    ])
}
