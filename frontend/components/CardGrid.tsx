'use client'

import { ReactNode } from 'react'

interface CardGridProps {
    children: ReactNode
    className?: string
}

/**
 * Grid padronizado para cards responsivos.
 *
 * Características:
 * - 1 coluna em telas pequenas
 * - 2 colunas em telas médias
 * - auto-fill em telas grandes com largura mínima de 300px por card
 */
export function CardGrid({ children, className = '' }: CardGridProps) {
    return (
        <div
            className={`grid grid-cols-1 md:grid-cols-2 lg:[grid-template-columns:repeat(auto-fill,minmax(300px,1fr))] gap-4 lg:gap-6 ${className}`}
        >
            {children}
        </div>
    )
}
