'use client'

interface PaginationProps {
    /**
     * Offset atual (número de itens pulados)
     */
    offset: number
    /**
     * Limite de itens por página
     */
    limit: number
    /**
     * Total de itens disponíveis
     */
    total: number
    /**
     * Função chamada ao clicar em "Primeira página"
     */
    onFirst: () => void
    /**
     * Função chamada ao clicar em "Anterior"
     */
    onPrevious: () => void
    /**
     * Função chamada ao clicar em "Próxima"
     */
    onNext: () => void
    /**
     * Função chamada ao clicar em "Última página"
     */
    onLast: () => void
    /**
     * Se true, desabilita os botões (útil durante loading)
     */
    disabled?: boolean
}

/**
 * Componente de paginação para ser usado dentro da ActionBar.
 *
 * Exibe informações de paginação e botões de navegação.
 *
 * @example
 * ```tsx
 * <ActionBar
 *   leftContent={
 *     <Pagination
 *       offset={0}
 *       limit={10}
 *       total={25}
 *       onFirst={() => setOffset(0)}
 *       onPrevious={() => setOffset(prev => Math.max(0, prev - 10))}
 *       onNext={() => setOffset(prev => prev + 10)}
 *       onLast={() => setOffset(Math.floor((25 - 1) / 10) * 10)}
 *       disabled={loading}
 *     />
 *   }
 * />
 * ```
 */
export function Pagination({
    offset,
    limit,
    total,
    onFirst,
    onPrevious,
    onNext,
    onLast,
    disabled = false,
}: PaginationProps) {
    // Calcular valores de exibição
    const start = offset + 1
    const end = Math.min(offset + limit, total)
    const canGoFirst = offset > 0 && !disabled
    const canGoPrevious = offset > 0 && !disabled
    const canGoNext = offset + limit < total && !disabled
    const canGoLast = offset + limit < total && !disabled

    // Não renderizar se não houver itens
    if (total === 0) {
        return null
    }

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={onFirst}
                disabled={!canGoFirst}
                className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center justify-center"
                title="Primeira página"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
            </button>
            <button
                onClick={onPrevious}
                disabled={!canGoPrevious}
                className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center justify-center"
                title="Página anterior"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
            </button>
            <div className="text-sm text-gray-700 px-2 whitespace-nowrap">
                {start} a {end} de {total}
            </div>
            <button
                onClick={onNext}
                disabled={!canGoNext}
                className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center justify-center"
                title="Próxima página"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
            </button>
            <button
                onClick={onLast}
                disabled={!canGoLast}
                className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center justify-center"
                title="Última página"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
            </button>
        </div>
    )
}
