import { useState, useCallback } from 'react'
import { toggleSelection } from '@/lib/entityUtils'

interface UseEntitySelectionReturn {
    selectedItems: Set<number>
    setSelectedItems: React.Dispatch<React.SetStateAction<Set<number>>>
    toggleSelection: (id: number) => void
    clearSelection: () => void
    selectAll: (ids: number[]) => void
    toggleAll: (ids: number[]) => void
    selectedCount: number
    /**
     * Indica se o usuário está no modo "selecionar todos".
     * Quando true, as ações devem considerar TODOS os registros (não apenas os visíveis).
     * É desativado automaticamente quando o usuário desmarca um item individual.
     */
    selectAllMode: boolean
    /**
     * Define manualmente o modo "selecionar todos".
     */
    setSelectAllMode: React.Dispatch<React.SetStateAction<boolean>>
    /**
     * Retorna os IDs para uma ação.
     * - Se selectAllMode é true, retorna null (indica que o backend deve processar todos com filtros)
     * - Se selectAllMode é false, retorna o array de IDs selecionados
     */
    getSelectedIdsForAction: () => number[] | null
}

export function useEntitySelection(): UseEntitySelectionReturn {
    const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set())
    const [selectAllMode, setSelectAllMode] = useState(false)

    // Ao alternar um item individual, desativa o modo "selecionar todos"
    const handleToggle = useCallback((id: number) => {
        setSelectedItems((prev) => toggleSelection(prev, id))
        // Desativa o selectAllMode quando o usuário interage individualmente
        setSelectAllMode(false)
    }, [])

    const clearSelection = useCallback(() => {
        setSelectedItems(new Set())
        setSelectAllMode(false)
    }, [])

    const selectAll = useCallback((ids: number[]) => {
        setSelectedItems(new Set(ids))
    }, [])

    // Se todos estão selecionados, desseleciona todos e desativa selectAllMode.
    // Senão, seleciona todos e ativa selectAllMode.
    const toggleAll = useCallback((ids: number[]) => {
        setSelectedItems((prev) => {
            const allSelected = ids.length > 0 && ids.every((id) => prev.has(id))
            if (allSelected) {
                setSelectAllMode(false)
                return new Set()
            } else {
                setSelectAllMode(true)
                return new Set(ids)
            }
        })
    }, [])

    // Retorna os IDs para ação ou null se estiver em modo "todos"
    const getSelectedIdsForAction = useCallback((): number[] | null => {
        if (selectAllMode) {
            return null // Indica que deve processar todos (usando filtros no backend)
        }
        return Array.from(selectedItems)
    }, [selectAllMode, selectedItems])

    return {
        selectedItems,
        setSelectedItems,
        toggleSelection: handleToggle,
        clearSelection,
        selectAll,
        toggleAll,
        selectedCount: selectedItems.size,
        selectAllMode,
        setSelectAllMode,
        getSelectedIdsForAction,
    }
}
