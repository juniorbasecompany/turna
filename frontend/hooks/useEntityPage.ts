import { protectedFetch } from '@/lib/api'
import { getActionBarErrorProps } from '@/lib/entityUtils'
import { useCallback, useState } from 'react'
import { useActionBarButtons } from './useActionBarButtons'
import { useEntityForm } from './useEntityForm'
import { useEntityList } from './useEntityList'
import { useEntitySelection } from './useEntitySelection'
import { usePagination } from './usePagination'

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
    /** Callback chamado após salvar com sucesso, recebe a entidade salva e se foi criação ou edição */
    onAfterSave?: (savedEntity: TEntity, isCreate: boolean) => void | Promise<void>
    /** Campos aplicados sobre initialFormData ao abrir criação */
    formDataOnCreate?: Partial<TFormData>
    /** Callback chamado após abrir formulário de criação */
    onOpenCreate?: () => void
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
    selectAll: (ids: number[]) => void
    toggleAll: (ids: number[]) => void
    selectedCount: number
    /**
     * Indica se o usuário está no modo "selecionar todos".
     * Quando true, as ações devem considerar TODOS os registros (não apenas os visíveis).
     */
    selectAllMode: boolean
    /**
     * Retorna os IDs para uma ação.
     * - Se selectAllMode é true, retorna null (indica que o backend deve processar todos com filtros)
     * - Se selectAllMode é false, retorna o array de IDs selecionados
     */
    getSelectedIdsForAction: () => number[] | null

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
        onAfterSave,
        formDataOnCreate,
        onOpenCreate,
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
        formDataOnCreate,
        onOpenCreate,
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

            let savedEntity: TEntity
            const isCreate = !form.editingItem

            if (form.editingItem) {
                // Editar
                const updateData = mapFormDataToUpdateRequest(form.formData)
                savedEntity = await protectedFetch<TEntity>(`${endpoint}/${form.editingItem.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                })
            } else {
                // Criar
                const createData = mapFormDataToCreateRequest(form.formData)
                savedEntity = await protectedFetch<TEntity>(endpoint, {
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

            // Chamar onAfterSave se fornecido (permite ações pós-salvar como enviar convite)
            if (onAfterSave) {
                await onAfterSave(savedEntity, isCreate)
            }

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
        onAfterSave,
        onSaveSuccess,
        setError,
    ])

    // Handler de excluir
    const handleDeleteSelected = useCallback(async () => {
        if (selection.selectedItems.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            // Verificar diretamente o selectAllMode para evitar stale closure
            const isSelectAllMode = selection.selectAllMode
            let idsToDelete: number[]

            if (isSelectAllMode) {
                // Modo "todos": buscar todos os IDs que atendem aos filtros atuais
                // Buscar em batches de 100 (limite máximo da API)
                const BATCH_SIZE = 100
                idsToDelete = []
                let offset = 0
                let hasMore = true

                while (hasMore) {
                    const params = new URLSearchParams()
                    params.set('limit', String(BATCH_SIZE))
                    params.set('offset', String(offset))

                    // Adicionar filtros atuais
                    if (additionalListParams) {
                        Object.entries(additionalListParams).forEach(([key, value]) => {
                            if (value !== null && value !== undefined) {
                                params.set(key, String(value))
                            }
                        })
                    }

                    const response = await protectedFetch<{ items: TEntity[]; total: number }>(
                        `${endpoint}/list?${params.toString()}`
                    )

                    const batchIds = response.items.map((item) => item.id)
                    idsToDelete.push(...batchIds)

                    // Verificar se há mais páginas
                    offset += BATCH_SIZE
                    hasMore = offset < response.total
                }
            } else {
                // Modo parcial: usar apenas os IDs selecionados
                idsToDelete = Array.from(selection.selectedItems)
            }

            if (idsToDelete.length === 0) {
                setError('Nenhum item para excluir')
                return
            }

            // Deletar todos os IDs em batches para não sobrecarregar
            const DELETE_BATCH_SIZE = 10
            for (let i = 0; i < idsToDelete.length; i += DELETE_BATCH_SIZE) {
                const batch = idsToDelete.slice(i, i + DELETE_BATCH_SIZE)
                const deletePromises = batch.map(async (id) => {
                    await protectedFetch(`${endpoint}/${id}`, {
                        method: 'DELETE',
                    })
                    return id
                })
                await Promise.all(deletePromises)
            }

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
    }, [selection.selectedItems, selection.selectAllMode, selection.clearSelection, endpoint, entityName, loadItems, onDeleteSuccess, setError, additionalListParams])

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
        selectAll: selection.selectAll,
        toggleAll: selection.toggleAll,
        selectedCount: selection.selectedCount,
        selectAllMode: selection.selectAllMode,
        getSelectedIdsForAction: selection.getSelectedIdsForAction,

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
