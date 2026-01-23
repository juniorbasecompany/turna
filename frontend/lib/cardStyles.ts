/**
 * Helpers para estilos de cards selecionáveis.
 *
 * Centraliza a lógica de classes CSS condicionais baseadas no estado de seleção.
 */

/**
 * Retorna as classes CSS para o container do card baseado no estado de seleção.
 *
 * @param isSelected - Se o card está selecionado
 * @returns Classes CSS para o container do card
 */
export function getCardContainerClasses(isSelected: boolean): string {
    return `group rounded-xl border p-4 min-w-0 transition-all duration-200 ${isSelected
            ? 'border-red-300 ring-2 ring-red-200 bg-red-50'
            : 'border-blue-200 bg-white'
        }`
}

/**
 * Retorna as classes CSS para texto principal do card baseado no estado de seleção.
 *
 * @param isSelected - Se o card está selecionado
 * @returns Classes CSS para texto principal (títulos, nomes)
 */
export function getCardTextClasses(isSelected: boolean): string {
    return isSelected ? 'text-red-900' : 'text-gray-900'
}

/**
 * Retorna as classes CSS para texto secundário do card baseado no estado de seleção.
 *
 * @param isSelected - Se o card está selecionado
 * @returns Classes CSS para texto secundário (datas, metadados)
 */
export function getCardSecondaryTextClasses(isSelected: boolean): string {
    return isSelected ? 'text-red-900' : 'text-slate-500'
}

/**
 * Retorna as classes CSS para texto terciário do card baseado no estado de seleção.
 *
 * @param isSelected - Se o card está selecionado
 * @returns Classes CSS para texto terciário (informações adicionais menores)
 */
export function getCardTertiaryTextClasses(isSelected: boolean): string {
    return isSelected ? 'text-red-700' : 'text-gray-500'
}
