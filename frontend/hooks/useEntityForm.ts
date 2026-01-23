import { useState, useCallback } from 'react'
import { hasFormChanges } from '@/lib/entityUtils'

interface UseEntityFormOptions<TFormData, TEntity extends { id: number }> {
    initialFormData: TFormData
    isEmptyCheck?: (data: TFormData) => boolean
}

interface UseEntityFormReturn<TFormData, TEntity extends { id: number }> {
    formData: TFormData
    setFormData: React.Dispatch<React.SetStateAction<TFormData>>
    originalFormData: TFormData
    setOriginalFormData: React.Dispatch<React.SetStateAction<TFormData>>
    editingItem: TEntity | null
    setEditingItem: React.Dispatch<React.SetStateAction<TEntity | null>>
    showEditArea: boolean
    setShowEditArea: React.Dispatch<React.SetStateAction<boolean>>
    isEditing: boolean
    hasChanges: () => boolean
    handleCreateClick: () => void
    handleEditClick: (item: TEntity) => void
    handleCancel: () => void
    resetForm: () => void
}

export function useEntityForm<TFormData extends Record<string, unknown>, TEntity extends { id: number }>(
    options: UseEntityFormOptions<TFormData, TEntity>
): UseEntityFormReturn<TFormData, TEntity> {
    const { initialFormData, isEmptyCheck } = options

    const [formData, setFormData] = useState<TFormData>(initialFormData)
    const [originalFormData, setOriginalFormData] = useState<TFormData>(initialFormData)
    const [editingItem, setEditingItem] = useState<TEntity | null>(null)
    const [showEditArea, setShowEditArea] = useState(false)

    const isEditing = showEditArea

    const checkHasChanges = useCallback(() => {
        // hasFormChanges espera TFormData | null, mas editingItem é TEntity | null
        // A função só verifica se editingItem é null para determinar se está criando ou editando
        // Passamos null quando não há item (modo criação) e formData quando há item (modo edição)
        return hasFormChanges(editingItem ? formData : null, formData, originalFormData, isEmptyCheck)
    }, [editingItem, formData, originalFormData, isEmptyCheck])

    const handleCreateClick = useCallback(() => {
        setFormData(initialFormData)
        setOriginalFormData(initialFormData)
        setEditingItem(null)
        setShowEditArea(true)
    }, [initialFormData])

    const handleEditClick = useCallback(
        (item: TEntity) => {
            // Esta função deve ser sobrescrita nas páginas específicas
            // pois cada entidade tem uma forma diferente de mapear item -> formData
            setEditingItem(item)
            setShowEditArea(true)
        },
        []
    )

    const handleCancel = useCallback(() => {
        setFormData(initialFormData)
        setOriginalFormData(initialFormData)
        setEditingItem(null)
        setShowEditArea(false)
    }, [initialFormData])

    const resetForm = useCallback(() => {
        setFormData(initialFormData)
        setOriginalFormData(initialFormData)
        setEditingItem(null)
        setShowEditArea(false)
    }, [initialFormData])

    return {
        formData,
        setFormData,
        originalFormData,
        setOriginalFormData,
        editingItem,
        setEditingItem,
        showEditArea,
        setShowEditArea,
        isEditing,
        hasChanges: checkHasChanges,
        handleCreateClick,
        handleEditClick,
        resetForm,
        handleCancel,
    }
}
