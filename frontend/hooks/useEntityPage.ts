import { useState, useCallback } from 'react'
import { protectedFetch } from '@/lib/api'
import { usePagination } from './usePagination'
import { useEntitySelection } from './useEntitySelection'
import { useEntityForm } from './useEntityForm'
import { useEntityList } from './useEntityList'
import { useActionBarButtons } from './useActionBarButtons'
import { getActionBarErrorProps } from '@/lib/entityUtils'

interface UseEntityPageOptions<TFormData, TEntity extends { id: number }, TCreateRequest, TUpdateRequest> {
    // Configuração básica
    endpoint: string
    entityName: string
    initialFormData: TFormData
    isEmptyCheck?: (data: TFormData) => boolean

    // Mapeamento de dados
    mapEntityToFormData: (entity: TEntity) => TFormData
    mapFormDataToCreateRequest: (formData: TFormData) => TCreateRequest
    mapFormDataToUpdateRequest: (formData: TFormData) => TUpdateRequest

    // Validação
    validateFormData?: (formData: TFormData) => string | null

    // Callbacks opcionais
    onSaveSuccess?: () => void
    onDeleteSuccess?: () => void
    additionalListParams?: Record<string, string | number | boolean | null>
    listEnabled?: boolean

    // Labels customizados
    saveLabel?: string
    deleteLabel?: string
    cancelLabel?: string
}

interface UseEntityPageReturn<TFormData, TEntity extends { id: number }> {
    // Estados
    items: TEntity[]
    loading: boolean
    error: string | null
    setError: React.Dispatch<React.SetStateAction<string | null>>
    submitting: boolean
    deleting: boolean

    // Formulário
    formData: TFormData
    setFormData: React.Dispatch<React.SetStateAction<TFormData>>
    editingItem: TEntity | null
    isEditing: boolean
    hasChanges: () => boolean
    handleCreateClick: () => void
    handleEditClick: (item: TEntity) => void
    handleCancel: () => void

    // Seleção
    selectedItems: Set<number>
    toggleSelection: (id: number) => void
    clearSelection: () => void
    selectedCount: number

    // Paginação
    pagination: ReturnType<typeof usePagination>['pagination']
    total: number
    paginationHandlers: {
        onFirst: () => void
        onPrevious: () => void
        onNext: () => void
        onLast: () => void
    }

    // Handlers
    handleSave: () => Promise<void>
    handleDeleteSelected: () => Promise<void>
    loadItems: () => Promise<void>

    // ActionBar
    actionBarButtons: ReturnType<typeof useActionBarButtons>
    actionBarErrorProps: ReturnType<typeof getActionBarErrorProps>
}

export function useEntityPage<
    TFormData extends Record<string, unknown>,
    TEntity extends { id: number },
    TCreateRequest,
    TUpdateRequest
>(options: UseEntityPageOptions<TFormData, TEntity, TCreateRequest, TUpdateRequest>): UseEntityPageReturn<TFormData, TEntity> {
    const {
        endpoint,
        entityName,
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
        onSaveSuccess,
        onDeleteSuccess,
        additionalListParams,
        listEnabled = true,
        saveLabel,
        deleteLabel,
        cancelLabel,
    } = options

    // Paginação
    const pagination = usePagination()
    const { pagination: paginationState, total, setTotal, onFirst, onPrevious, onNext, onLast } = pagination

    // Seleção
    const selection = useEntitySelection()

    // Formulário
    const form = useEntityForm<TFormData, TEntity>({
        initialFormData,
        isEmptyCheck,
    })

    // Sobrescrever handleEditClick para mapear corretamente
    const handleEditClick = useCallback(
        (item: TEntity) => {
            const formData = mapEntityToFormData(item)
            form.setFormData(formData)
            form.setOriginalFormData(formData)
            form.setEditingItem(item)
            form.setShowEditArea(true)
        },
        [mapEntityToFormData, form]
    )

    // Lista de itens
    const { items, loading, error, setError, loadItems } = useEntityList<TEntity>({
        endpoint: `${endpoint}/list`,
        pagination: paginationState,
        setTotal,
        additionalParams: additionalListParams,
        enabled: listEnabled,
    })

    // Estados de operação
    const [submitting, setSubmitting] = useState(false)
    const [deleting, setDeleting] = useState(false)

    // Handler de salvar
    const handleSave = useCallback(async () => {
        // Validação
        if (validateFormData) {
            const validationError = validateFormData(form.formData)
            if (validationError) {
                setError(validationError)
                return
            }
        }

        try {
            setSubmitting(true)
            setError(null)

            if (form.editingItem) {
                // Editar
                const updateData = mapFormDataToUpdateRequest(form.formData)
                await protectedFetch(`${endpoint}/${form.editingItem.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                })
            } else {
                // Criar
                const createData = mapFormDataToCreateRequest(form.formData)
                await protectedFetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(createData),
                })
            }

            // Recarregar lista e limpar formulário
            await loadItems()
            form.resetForm()

            if (onSaveSuccess) {
                onSaveSuccess()
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : `Erro ao salvar ${entityName}`
            setError(message)
            console.error(`Erro ao salvar ${entityName}:`, err)
        } finally {
            setSubmitting(false)
        }
    }, [
        form,
        validateFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        endpoint,
        entityName,
        loadItems,
        onSaveSuccess,
        setError,
    ])

    // Handler de excluir
    const handleDeleteSelected = useCallback(async () => {
        if (selection.selectedItems.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            const deletePromises = Array.from(selection.selectedItems).map(async (id) => {
                await protectedFetch(`${endpoint}/${id}`, {
                    method: 'DELETE',
                })
                return id
            })

            await Promise.all(deletePromises)

            // Recarregar lista
            await loadItems()
            selection.clearSelection()

            if (onDeleteSuccess) {
                onDeleteSuccess()
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : `Erro ao excluir ${entityName}`
            setError(message)
        } finally {
            setDeleting(false)
        }
    }, [selection, endpoint, entityName, loadItems, onDeleteSuccess, setError])

    // Handler de cancelar (combinado)
    const handleCancel = useCallback(() => {
        form.handleCancel()
        selection.clearSelection()
        setError(null)
    }, [form, selection, setError])

    // Botões do ActionBar
    const actionBarButtons = useActionBarButtons({
        isEditing: form.isEditing,
        selectedCount: selection.selectedCount,
        hasChanges: form.hasChanges(),
        submitting,
        deleting,
        onCancel: handleCancel,
        onDelete: handleDeleteSelected,
        onSave: handleSave,
        saveLabel,
        deleteLabel,
        cancelLabel,
    })

    // Props de erro do ActionBar
    const actionBarErrorProps = getActionBarErrorProps(error, form.isEditing, selection.selectedCount)

    return {
        // Estados
        items,
        loading,
        error,
        setError,
        submitting,
        deleting,

        // Formulário
        formData: form.formData,
        setFormData: form.setFormData,
        editingItem: form.editingItem,
        isEditing: form.isEditing,
        hasChanges: form.hasChanges,
        handleCreateClick: form.handleCreateClick,
        handleEditClick,
        handleCancel,

        // Seleção
        selectedItems: selection.selectedItems,
        toggleSelection: selection.toggleSelection,
        clearSelection: selection.clearSelection,
        selectedCount: selection.selectedCount,

        // Paginação
        pagination: paginationState,
        total,
        paginationHandlers: {
            onFirst,
            onPrevious,
            onNext,
            onLast,
        },

        // Handlers
        handleSave,
        handleDeleteSelected,
        loadItems,

        // ActionBar
        actionBarButtons,
        actionBarErrorProps,
    }
}
