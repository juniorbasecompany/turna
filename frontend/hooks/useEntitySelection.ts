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
}

export function useEntitySelection(): UseEntitySelectionReturn {
    const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set())

    const handleToggle = useCallback((id: number) => {
        setSelectedItems((prev) => toggleSelection(prev, id))
    }, [])

    const clearSelection = useCallback(() => {
        setSelectedItems(new Set())
    }, [])

    const selectAll = useCallback((ids: number[]) => {
        setSelectedItems(new Set(ids))
    }, [])

    // Se todos estão selecionados, desseleciona todos. Senão, seleciona todos.
    const toggleAll = useCallback((ids: number[]) => {
        setSelectedItems((prev) => {
            const allSelected = ids.length > 0 && ids.every((id) => prev.has(id))
            return allSelected ? new Set() : new Set(ids)
        })
    }, [])

    return {
        selectedItems,
        setSelectedItems,
        toggleSelection: handleToggle,
        clearSelection,
        selectAll,
        toggleAll,
        selectedCount: selectedItems.size,
    }
}
