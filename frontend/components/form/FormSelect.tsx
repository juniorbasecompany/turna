'use client'

import { FormField } from '../FormField'
import { LoadingSpinner } from '../LoadingSpinner'
import { FORM_SELECT_CLASS, FORM_INPUT_DISABLED_CLASS, FORM_INPUT_ERROR_CLASS } from './formStyles'

export interface FormSelectOption<T extends string | number = string | number> {
  /** Valor da opção */
  value: T
  /** Label exibido */
  label: string
}

interface FormSelectProps<T extends string | number = string | number> {
  /** Label do campo */
  label: string
  /** Valor atual (pode ser null para "vazio") */
  value: T | null
  /** Callback quando o valor muda */
  onChange: (value: T | null) => void
  /** Lista de opções disponíveis */
  options: FormSelectOption<T>[]
  /** Label para a opção vazia (ex: "Selecione...", "") */
  emptyLabel?: string
  /** Campo obrigatório */
  required?: boolean
  /** Se o campo está desabilitado */
  disabled?: boolean
  /** Se está carregando opções (mostra spinner) */
  loading?: boolean
  /** ID do elemento (acessibilidade) */
  id?: string
  /** Mensagem de erro */
  error?: string
  /** Texto de ajuda abaixo do campo */
  helperText?: string
  /** Classe CSS adicional */
  className?: string
}

/**
 * Componente de select para formulários de edição.
 * Padroniza aparência e comportamento de dropdowns.
 * 
 * @example
 * ```tsx
 * <FormSelect
 *   label="Hospital"
 *   value={formData.hospital_id}
 *   onChange={(value) => setFormData({ ...formData, hospital_id: value })}
 *   options={hospitals.map(h => ({ value: h.id, label: h.name }))}
 *   required
 *   disabled={submitting}
 *   loading={loadingHospitals}
 * />
 * ```
 */
export function FormSelect<T extends string | number = string | number>({
  label,
  value,
  onChange,
  options,
  emptyLabel = '',
  required = false,
  disabled = false,
  loading = false,
  id,
  error,
  helperText,
  className = '',
}: FormSelectProps<T>) {
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

  // Determina a classe CSS baseada no estado
  const getSelectClass = () => {
    if (disabled) return FORM_INPUT_DISABLED_CLASS
    if (error) return FORM_INPUT_ERROR_CLASS
    return FORM_SELECT_CLASS
  }

  return (
    <FormField label={label} required={required} helperText={helperText} className={className}>
      {loading ? (
        <div className="flex justify-center py-2">
          <LoadingSpinner />
        </div>
      ) : (
        <>
          <select
            id={id}
            value={value ?? ''}
            onChange={handleChange}
            required={required}
            disabled={disabled}
            className={getSelectClass()}
          >
            <option value="">{emptyLabel}</option>
            {options.map((option) => (
              <option key={String(option.value)} value={String(option.value)}>
                {option.label}
              </option>
            ))}
          </select>
          {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
        </>
      )}
    </FormField>
  )
}
