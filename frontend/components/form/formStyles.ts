/**
 * Constantes de estilo para componentes de formulário.
 * Centraliza estilos para garantir consistência visual em todos os painéis.
 * 
 * Nota: Estilos são os mesmos dos filtros para manter consistência visual.
 */

// Classes CSS para inputs de formulário (text, number, etc.)
export const FORM_INPUT_CLASS = 
  'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'

// Classes CSS para selects de formulário
export const FORM_SELECT_CLASS = FORM_INPUT_CLASS

// Classes CSS para textareas de formulário
export const FORM_TEXTAREA_CLASS = FORM_INPUT_CLASS

// Classes CSS para inputs desabilitados
export const FORM_INPUT_DISABLED_CLASS = 
  'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-gray-100 cursor-not-allowed opacity-50'

// Classes CSS para inputs com erro
export const FORM_INPUT_ERROR_CLASS = 
  'w-full px-3 py-2 border border-red-500 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500'
