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
