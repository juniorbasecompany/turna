'use client'

import { FormField } from '../FormField'
import { FILTER_SELECT_CLASS, FILTER_INPUT_DISABLED_CLASS } from './filterStyles'

export interface FilterSelectOption<T extends string | number = string | number> {
  /** Valor da opção */
  value: T
  /** Label exibido */
  label: string
}

interface FilterSelectProps<T extends string | number = string | number> {
  /** Label do campo de filtro */
  label: string
  /** Valor atual do filtro (pode ser null para "todos") */
  value: T | null
  /** Callback quando o valor muda */
  onChange: (value: T | null) => void
  /** Lista de opções disponíveis */
  options: FilterSelectOption<T>[]
  /** Label para a opção vazia (ex: "Todos", "Selecione...") */
  emptyLabel?: string
  /** Se o campo está desabilitado */
  disabled?: boolean
  /** Classe CSS adicional */
  className?: string
}

/**
 * Componente de select para filtros.
 * Padroniza aparência e comportamento de dropdowns em filtros.
 * 
 * @example
 * ```tsx
 * <FilterSelect
 *   label="Hospital"
 *   value={filterHospitalId}
 *   onChange={setFilterHospitalId}
 *   options={hospitals.map(h => ({ value: h.id, label: h.name }))}
 *   emptyLabel="Todos os hospitais"
 * />
 * ```
 */
export function FilterSelect<T extends string | number = string | number>({
  label,
  value,
  onChange,
  options,
  emptyLabel = '',
  disabled = false,
  className = '',
}: FilterSelectProps<T>) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newValue = e.target.value
    if (newValue === '') {
      onChange(null)
    } else {
      // Determina se deve converter para número baseado no tipo das opções
      const firstOption = options[0]
      if (firstOption && typeof firstOption.value === 'number') {
        onChange(parseInt(newValue, 10) as T)
      } else {
        onChange(newValue as T)
      }
    }
  }

  return (
    <FormField label={label} className={className}>
      <select
        value={value ?? ''}
        onChange={handleChange}
        disabled={disabled}
        className={disabled ? FILTER_INPUT_DISABLED_CLASS : FILTER_SELECT_CLASS}
      >
        <option value="">{emptyLabel}</option>
        {options.map((option) => (
          <option key={String(option.value)} value={String(option.value)}>
            {option.label}
          </option>
        ))}
      </select>
    </FormField>
  )
}
