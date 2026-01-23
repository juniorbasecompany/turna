import { useMemo } from 'react'

interface ActionButton {
    label: string
    onClick: () => void
    variant: 'primary' | 'secondary'
    disabled?: boolean
    loading?: boolean
}

interface UseActionBarButtonsOptions {
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
}

/**
 * Hook para gerar botões padronizados do ActionBar.
 *
 * Ordem padronizada dos botões (sempre nesta ordem):
 * 1. Cancelar (secondary) - aparece quando há edição OU seleção
 * 2. Excluir (primary) - aparece quando há seleção
 * 3. Salvar (primary) - aparece quando há edição com mudanças
 *
 * Esta ordem garante consistência visual em todos os painéis.
 */

export function useActionBarButtons(options: UseActionBarButtonsOptions): ActionButton[] {
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
    } = options

    return useMemo(() => {
        const buttons: ActionButton[] = []

        // Ordem padronizada dos botões:
        // 1. Cancelar (secondary) - sempre primeiro quando aparece
        // 2. Excluir (primary) - quando há seleção
        // 3. Salvar (primary) - quando há edição com mudanças

        // Botão Cancelar (aparece se houver edição OU seleção)
        if (isEditing || selectedCount > 0) {
            buttons.push({
                label: cancelLabel,
                onClick: onCancel,
                variant: 'secondary',
                disabled: submitting || deleting,
            })
        }

        // Botão Excluir (aparece se houver seleção)
        if (selectedCount > 0) {
            buttons.push({
                label: deleteLabel,
                onClick: onDelete,
                variant: 'primary',
                disabled: deleting || submitting,
                loading: deleting,
            })
        }

        // Botão Salvar (aparece se houver edição com mudanças)
        if (isEditing && hasChanges) {
            buttons.push({
                label: submitting ? 'Salvando...' : saveLabel,
                onClick: onSave,
                variant: 'primary',
                disabled: submitting,
                loading: submitting,
            })
        }

        return buttons
    }, [
        isEditing,
        selectedCount,
        hasChanges,
        submitting,
        deleting,
        onCancel,
        onDelete,
        onSave,
        saveLabel,
        deleteLabel,
        cancelLabel,
    ])
}
