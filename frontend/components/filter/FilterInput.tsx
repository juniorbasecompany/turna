'use client'

import { FormField } from '../FormField'
import { FILTER_INPUT_CLASS, FILTER_INPUT_DISABLED_CLASS } from './filterStyles'

interface FilterInputProps {
  /** Label do campo de filtro */
  label: string
  /** Valor atual do filtro */
  value: string
  /** Callback quando o valor muda */
  onChange: (value: string) => void
  /** Placeholder opcional */
  placeholder?: string
  /** Se o campo está desabilitado */
  disabled?: boolean
  /** Tipo do input (text, number, etc.) */
  type?: 'text' | 'number'
  /** Classe CSS adicional */
  className?: string
}

/**
 * Componente de input para filtros.
 * Padroniza aparência e comportamento de campos de texto em filtros.
 * 
 * @example
 * ```tsx
 * <FilterInput
 *   label="Nome"
 *   value={filterName}
 *   onChange={setFilterName}
 *   placeholder="Filtrar por nome..."
 * />
 * ```
 */
export function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  type = 'text',
  className = '',
}: FilterInputProps) {
  return (
    <FormField label={label} className={className}>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={disabled ? FILTER_INPUT_DISABLED_CLASS : FILTER_INPUT_CLASS}
      />
    </FormField>
  )
}
