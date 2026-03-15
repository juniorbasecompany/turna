'use client'

import { createContext, ReactNode, useContext } from 'react'
import { getCardContainerClasses } from '@/lib/cardStyles'

/** Contexto de seleção do card: filhos (ex.: CardFooter) podem obter isSelected e onToggle sem props */
export const CardSelectionContext = createContext<{
  isSelected: boolean
  onToggle: () => void
} | null>(null)

export function useCardSelection() {
  return useContext(CardSelectionContext)
}

/** Wrapper para a área de preview do card: ao clicar, alterna seleção (marca/desmarca). */
export function CardPreviewArea({
  children,
  className = '',
  style,
}: {
  children: ReactNode
  className?: string
  style?: React.CSSProperties
}) {
  const ctx = useCardSelection()
  return (
    <div
      className={`cursor-pointer ${className}`}
      style={style}
      onClick={(e) => {
        e.stopPropagation()
        ctx?.onToggle()
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          e.stopPropagation()
          ctx?.onToggle()
        }
      }}
    >
      {children}
    </div>
  )
}

interface EntityCardProps {
  id: number
  /** Define o estado de seleção e o toggle compartilhados com preview e rodapé via contexto */
  selection: { isSelected: boolean; onToggle: () => void }
  children: ReactNode
  footer?: ReactNode
  className?: string
}

/**
 * Componente base para cards de entidades.
 *
 * Encapsula a estrutura padrão de cards:
 * - Container com classes de seleção
 * - Slot para conteúdo principal
 * - Slot para rodapé (opcional); CardFooter obtém isSelected e onToggle do contexto
 * - A seleção acontece apenas nas áreas que usam CardPreviewArea e no checkbox do rodapé
 *
 * @example
 * ```tsx
 * <EntityCard
 *   id={item.id}
 *   selection={{ isSelected: selectedItems.has(item.id), onToggle: () => toggleSelection(item.id) }}
 *   footer={<CardFooter date={...} onEdit={...} />}
 * >
 *   <div className="mb-3">Conteúdo</div>
 * </EntityCard>
 * ```
 */
export function EntityCard({
  id,
  selection,
  children,
  footer,
  className = '',
}: EntityCardProps) {
  const { isSelected, onToggle } = selection

  return (
    <CardSelectionContext.Provider value={{ isSelected, onToggle }}>
      <div
        key={id}
        className={`${getCardContainerClasses(isSelected)} ${className}`}
      >
        {children}
        {footer}
      </div>
    </CardSelectionContext.Provider>
  )
}
