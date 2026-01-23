import { useState, useCallback, useMemo } from 'react'

interface UseEntityFiltersOptions<T> {
  /** Filtros iniciais selecionados */
  initialFilters?: Set<T>
  /** Lista de todos os filtros disponíveis */
  allFilters: T[]
  /** Callback quando os filtros mudam */
  onFilterChange?: (filters: Set<T>) => void
}

interface UseEntityFiltersReturn<T> {
  /** Filtros atualmente selecionados */
  selectedFilters: Set<T>
  /** Alterna um filtro específico */
  toggleFilter: (value: T) => void
  /** Seleciona/deseleciona todos os filtros */
  toggleAll: () => void
  /** Limpa todos os filtros */
  clearFilters: () => void
  /** Se todos os filtros estão selecionados */
  isAllSelected: boolean
}

/**
 * Hook para gerenciar estado e lógica de filtros.
 * 
 * Gerencia seleção de filtros, toggle individual e toggle all,
 * com callback opcional para notificar mudanças.
 * 
 * @example
 * ```tsx
 * const statusFilters = useEntityFilters({
 *   allFilters: ['ACTIVE', 'PENDING', 'INACTIVE'],
 *   initialFilters: new Set(['ACTIVE', 'PENDING']),
 *   onFilterChange: (filters) => {
 *     // Atualizar lista filtrada
 *   }
 * })
 * 
 * <FilterButtons
 *   selectedValues={statusFilters.selectedFilters}
 *   onToggle={statusFilters.toggleFilter}
 *   onToggleAll={statusFilters.toggleAll}
 * />
 * ```
 */
export function useEntityFilters<T>({
  initialFilters = new Set(),
  allFilters,
  onFilterChange,
}: UseEntityFiltersOptions<T>): UseEntityFiltersReturn<T> {
  const [selectedFilters, setSelectedFilters] = useState<Set<T>>(initialFilters)

  const toggleFilter = useCallback((value: T) => {
    setSelectedFilters((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(value)) {
        newSet.delete(value)
      } else {
        newSet.add(value)
      }
      
      if (onFilterChange) {
        onFilterChange(newSet)
      }
      
      return newSet
    })
  }, [onFilterChange])

  const isAllSelected = useMemo(() => {
    return allFilters.length > 0 && allFilters.every((filter) => selectedFilters.has(filter))
  }, [allFilters, selectedFilters])

  const toggleAll = useCallback(() => {
    setSelectedFilters((prev) => {
      const newSet = isAllSelected ? new Set<T>() : new Set(allFilters)
      
      if (onFilterChange) {
        onFilterChange(newSet)
      }
      
      return newSet
    })
  }, [allFilters, isAllSelected, onFilterChange])

  const clearFilters = useCallback(() => {
    setSelectedFilters(new Set())
    if (onFilterChange) {
      onFilterChange(new Set())
    }
  }, [onFilterChange])

  return {
    selectedFilters,
    toggleFilter,
    toggleAll,
    clearFilters,
    isAllSelected,
  }
}
