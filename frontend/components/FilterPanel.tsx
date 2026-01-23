'use client'

import { ReactNode } from 'react'

interface FilterPanelProps {
  children: ReactNode
  validationErrors?: ReactNode
  className?: string
}

/**
 * Componente wrapper para painéis de filtros.
 * 
 * Encapsula a estrutura padrão de filtros:
 * - Container branco com borda
 * - Espaçamento consistente
 * - Suporte a validação de filtros
 * 
 * @example
 * ```tsx
 * <FilterPanel validationErrors={dateError}>
 *   <FilterButtons title="Status" {...props} />
 *   <FilterButtons title="Função" {...props} />
 * </FilterPanel>
 * ```
 */
export function FilterPanel({ children, validationErrors, className = '' }: FilterPanelProps) {
  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 sm:p-6 mb-4 sm:mb-6 ${className}`}>
      <div className="space-y-4">
        {children}
      </div>
      {validationErrors}
    </div>
  )
}
