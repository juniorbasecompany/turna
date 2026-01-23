'use client'

import { ReactNode } from 'react'
import { getCardContainerClasses } from '@/lib/cardStyles'

interface EntityCardProps {
  id: number
  isSelected: boolean
  onClick?: () => void
  children: ReactNode
  footer?: ReactNode
  className?: string
}

/**
 * Componente base para cards de entidades.
 * 
 * Encapsula a estrutura padrão de cards:
 * - Container com classes de seleção
 * - Suporte a onClick para seleção
 * - Slot para conteúdo principal
 * - Slot para rodapé (opcional)
 * 
 * @example
 * ```tsx
 * <EntityCard
 *   id={item.id}
 *   isSelected={selectedItems.has(item.id)}
 *   onClick={() => toggleSelection(item.id)}
 *   footer={<CardFooter {...props} />}
 * >
 *   <div className="mb-3">
 *     {/* Conteúdo do card */}
 *   </div>
 * </EntityCard>
 * ```
 */
export function EntityCard({ 
  id, 
  isSelected, 
  onClick, 
  children, 
  footer,
  className = '' 
}: EntityCardProps) {
  return (
    <div
      key={id}
      className={`${getCardContainerClasses(isSelected)} ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
      {footer}
    </div>
  )
}
