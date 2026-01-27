'use client'

export interface SelectionCounterProps {
    /**
     * Quantidade de itens selecionados (visíveis na página)
     */
    selectedCount: number
    /**
     * Quantidade total de itens visíveis na página
     */
    totalCount?: number
    /**
     * Total geral de registros que atendem aos filtros (usado quando selectAllMode está ativo)
     */
    grandTotal?: number
    /**
     * Indica se está no modo "selecionar todos".
     * Quando true, o checkbox fica azul (indicando que as ações afetarão TODOS os registros).
     * Quando false, o checkbox fica cinza (indicando que apenas os itens selecionados serão afetados).
     */
    selectAllMode?: boolean
    /**
     * Callback chamado ao clicar no checkbox (para selecionar/desselecionar todos)
     */
    onToggleAll?: () => void
}

/**
 * Componente de checkbox com contador de seleção.
 *
 * Exibe um checkbox customizado que indica o estado de seleção:
 * - Vazio: nenhum item selecionado
 * - Check cinza: alguns itens selecionados (ações afetam apenas os selecionados)
 * - Check azul: modo "todos" ativo (ações afetam TODOS os registros com filtros)
 *
 * O contador mostra:
 * - Quantidade de itens selecionados quando em modo parcial
 * - Total geral (grandTotal) quando em modo "todos"
 */
export function SelectionCounter({
    selectedCount,
    grandTotal,
    selectAllMode,
    onToggleAll,
}: SelectionCounterProps) {
    // Não renderizar quando não há seleção
    if (selectedCount === 0) {
        return null
    }

    // Azul apenas quando selectAllMode está ativo (indica que ações afetarão TODOS os registros)
    const isAllMode = selectAllMode === true

    return (
        <button
            type="button"
            onClick={onToggleAll}
            className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none"
        >
            <span
                className={`w-4 h-4 flex items-center justify-center rounded border transition-colors ${
                    isAllMode
                        ? 'bg-blue-600 border-blue-600'
                        : 'bg-white border-gray-300'
                }`}
            >
                <svg
                    className={`w-3 h-3 ${isAllMode ? 'text-white' : 'text-gray-400'}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    strokeWidth={3}
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                    />
                </svg>
            </span>
            <span>
                {isAllMode && grandTotal !== undefined
                    ? grandTotal
                    : selectedCount}
            </span>
        </button>
    )
}
