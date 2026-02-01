import { useState, useCallback, useMemo } from 'react'

interface UseEntityFiltersOptions<T> {
  /** Lista de todos os filtros disponíveis (todos selecionados inicialmente) */
  allFilters: T[]
}

interface UseEntityFiltersReturn<T> {
  /** Valores selecionados. Usar selectedValues.includes(valor) para filtrar. */
  selectedValues: T[]
  toggleFilter: (value: T) => void
  toggleAll: () => void
  /** true quando nem todos estão selecionados (filtro ativo) */
  isFilterActive: boolean
  /** Retorna parâmetro para API quando filtro ativo: { [paramName]: 'val1,val2' } ou {} */
  toListParam: (paramName: string) => Record<string, string>
}

/**
 * Hook para gerenciar estado e lógica de filtros.
 * Array vazio = nenhum selecionado = zero resultados.
 */
export function useEntityFilters<T>({
  allFilters,
}: UseEntityFiltersOptions<T>): UseEntityFiltersReturn<T> {
  const [selectedValues, setSelectedValues] = useState<T[]>(() => [...allFilters])

  const isFilterActive = selectedValues.length < allFilters.length

  const toggleFilter = useCallback((value: T) => {
    setSelectedValues((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    )
  }, [])

  const toggleAll = useCallback(() => {
    setSelectedValues(() => (isFilterActive ? [...allFilters] : []))
  }, [allFilters, isFilterActive])

  const toListParam = useCallback(
    (paramName: string): Record<string, string> => {
      if (!isFilterActive) return {}
      return { [paramName]: selectedValues.join(',') }
    },
    [isFilterActive, selectedValues]
  )

  return {
    selectedValues,
    toggleFilter,
    toggleAll,
    isFilterActive,
    toListParam,
  }
}
