/**
 * Componentes de formulário reutilizáveis para áreas de edição.
 * 
 * Este módulo exporta componentes padronizados para formulários:
 * - FormInput: Campo de texto para formulário
 * - FormSelect: Dropdown para formulário
 * - FormTextarea: Área de texto para formulário
 * 
 * Nota: Use estes componentes dentro de <EditForm> para edição de entidades.
 * Para filtros, use os componentes de '@/components/filter'.
 */

// Componentes
export { FormInput } from './FormInput'
export { FormSelect } from './FormSelect'
export type { FormSelectOption } from './FormSelect'
export { FormTextarea } from './FormTextarea'

// Constantes de estilo (para uso direto quando necessário)
export {
  FORM_INPUT_CLASS,
  FORM_SELECT_CLASS,
  FORM_TEXTAREA_CLASS,
  FORM_INPUT_DISABLED_CLASS,
  FORM_INPUT_ERROR_CLASS,
} from './formStyles'
