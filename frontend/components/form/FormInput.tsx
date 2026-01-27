'use client'

import { FormField } from '../FormField'
import { FORM_INPUT_CLASS, FORM_INPUT_DISABLED_CLASS, FORM_INPUT_ERROR_CLASS } from './formStyles'

interface FormInputProps {
  /** Label do campo */
  label: string
  /** Valor atual */
  value: string
  /** Callback quando o valor muda */
  onChange: (value: string) => void
  /** Campo obrigatório */
  required?: boolean
  /** Se o campo está desabilitado */
  disabled?: boolean
  /** Placeholder opcional */
  placeholder?: string
  /** Tipo do input (text, number, email, etc.) */
  type?: 'text' | 'number' | 'email' | 'tel'
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
 * Componente de input para formulários de edição.
 * Padroniza aparência e comportamento de campos de texto.
 * 
 * @example
 * ```tsx
 * <FormInput
 *   label="Nome"
 *   value={formData.name}
 *   onChange={(value) => setFormData({ ...formData, name: value })}
 *   required
 *   disabled={submitting}
 * />
 * ```
 */
export function FormInput({
  label,
  value,
  onChange,
  required = false,
  disabled = false,
  placeholder,
  type = 'text',
  id,
  error,
  helperText,
  className = '',
}: FormInputProps) {
  // Determina a classe CSS baseada no estado
  const getInputClass = () => {
    if (disabled) return FORM_INPUT_DISABLED_CLASS
    if (error) return FORM_INPUT_ERROR_CLASS
    return FORM_INPUT_CLASS
  }

  return (
    <FormField label={label} required={required} helperText={helperText} className={className}>
      <input
        type={type}
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={getInputClass()}
      />
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </FormField>
  )
}
