/**
 * Constantes de estilo para componentes de filtro.
 * Centraliza estilos para garantir consistência visual em todos os painéis.
 */

// Classes CSS para inputs de filtro (text, number, etc.)
export const FILTER_INPUT_CLASS = 
  'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 transition-all duration-200'

// Classes CSS para selects de filtro
export const FILTER_SELECT_CLASS = FILTER_INPUT_CLASS

// Classes CSS para inputs desabilitados
export const FILTER_INPUT_DISABLED_CLASS = 
  'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-gray-100 cursor-not-allowed'

// Classes CSS para efeito flash (destaque vermelho temporário)
export const FILTER_INPUT_FLASH_CLASS = 
  'w-full px-3 py-2 border border-red-500 bg-red-50 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500 transition-all duration-200'

// Classes CSS para labels de filtro
export const FILTER_LABEL_CLASS = 'block text-sm font-medium text-gray-700 mb-2'
