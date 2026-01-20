import { useState, useCallback } from 'react'
import { toggleSelection } from '@/lib/entityUtils'

interface UseEntitySelectionReturn {
    selectedItems: Set<number>
    setSelectedItems: React.Dispatch<React.SetStateAction<Set<number>>>
    toggleSelection: (id: number) => void
    clearSelection: () => void
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

    return {
        selectedItems,
        setSelectedItems,
        toggleSelection: handleToggle,
        clearSelection,
        selectedCount: selectedItems.size,
    }
}
