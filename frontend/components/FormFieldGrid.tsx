'use client'

import { ReactNode } from 'react'

interface FormFieldGridProps {
    /** Campos filhos que serão dispostos em grid */
    children: ReactNode
    /** Número de colunas em telas pequenas (padrão: 1) */
    cols?: 1 | 2 | 3
    /** Número de colunas em telas médias/grandes (padrão: 2) */
    smCols?: 1 | 2 | 3
    /** Espaçamento entre campos (padrão: 4) */
    gap?: 2 | 3 | 4 | 6
    /** Classe CSS adicional */
    className?: string
}

/**
 * Container para campos de formulário em grid horizontal responsivo.
 * Por padrão, cria um grid de 1 coluna em mobile e 2 colunas em telas maiores.
 */
export function FormFieldGrid({
    children,
    cols = 1,
    smCols = 2,
    gap = 4,
    className = '',
}: FormFieldGridProps) {
    // Mapear valores para classes Tailwind fixas (necessário para o Tailwind funcionar)
    const gridColsClasses: Record<1 | 2 | 3, string> = {
        1: 'grid-cols-1',
        2: 'grid-cols-2',
        3: 'grid-cols-3',
    }
    const smGridColsClasses: Record<1 | 2 | 3, string> = {
        1: 'sm:grid-cols-1',
        2: 'sm:grid-cols-2',
        3: 'sm:grid-cols-3',
    }
    const gapClasses: Record<2 | 3 | 4 | 6, string> = {
        2: 'gap-2',
        3: 'gap-3',
        4: 'gap-4',
        6: 'gap-6',
    }

    const gridColsClass = gridColsClasses[cols]
    const smGridColsClass = smGridColsClasses[smCols]
    const gapClass = gapClasses[gap]

    return (
        <div className={`grid ${gridColsClass} ${smGridColsClass} ${gapClass} ${className}`}>
            {children}
        </div>
    )
}
