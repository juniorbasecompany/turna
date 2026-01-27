/**
 * Componentes de filtro reutilizáveis.
 * 
 * Este módulo exporta componentes padronizados para filtros em painéis:
 * - FilterPanel: Container para grupo de filtros
 * - FilterInput: Campo de texto para filtro
 * - FilterSelect: Dropdown para filtro
 * - FilterDateRange: Intervalo de datas para filtro
 * - FilterButtons: Botões multi-select para filtro
 * 
 * Uso de constantes de estilo para consistência visual.
 */

// Componentes
export { FilterPanel } from './FilterPanel'
export { FilterInput } from './FilterInput'
export { FilterSelect } from './FilterSelect'
export type { FilterSelectOption } from './FilterSelect'
export { FilterDateRange } from './FilterDateRange'
export { FilterButtons } from './FilterButtons'
export type { FilterOption } from './FilterButtons'

// Constantes de estilo (para uso direto quando necessário)
export {
  FILTER_INPUT_CLASS,
  FILTER_SELECT_CLASS,
  FILTER_INPUT_DISABLED_CLASS,
  FILTER_LABEL_CLASS,
} from './filterStyles'
