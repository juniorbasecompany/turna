'use client'

import { FormField } from '../FormField'
import { FORM_TEXTAREA_CLASS, FORM_INPUT_DISABLED_CLASS, FORM_INPUT_ERROR_CLASS } from './formStyles'

interface FormTextareaProps {
  /** Label do campo */
  label: string
  /** Valor atual */
  value: string
  /** Callback quando o valor muda */
  onChange: (value: string) => void
  /** Número de linhas visíveis */
  rows?: number
  /** Campo obrigatório */
  required?: boolean
  /** Se o campo está desabilitado */
  disabled?: boolean
  /** Placeholder opcional */
  placeholder?: string
  /** ID do elemento (acessibilidade) */
  id?: string
  /** Mensagem de erro */
  error?: string
  /** Texto de ajuda abaixo do campo */
  helperText?: string
  /** Usar fonte monospace */
  monospace?: boolean
  /** Classe CSS adicional */
  className?: string
}

/**
 * Componente de textarea para formulários de edição.
 * Padroniza aparência e comportamento de campos de texto longo.
 * 
 * @example
 * ```tsx
 * <FormTextarea
 *   label="Instruções"
 *   value={formData.prompt}
 *   onChange={(value) => setFormData({ ...formData, prompt: value })}
 *   rows={10}
 *   helperText="Descreva como os arquivos devem ser processados."
 *   monospace
 *   disabled={submitting}
 * />
 * ```
 */
export function FormTextarea({
  label,
  value,
  onChange,
  rows = 5,
  required = false,
  disabled = false,
  placeholder,
  id,
  error,
  helperText,
  monospace = false,
  className = '',
}: FormTextareaProps) {
  // Determina a classe CSS baseada no estado
  const getTextareaClass = () => {
    let baseClass: string
    if (disabled) {
      baseClass = FORM_INPUT_DISABLED_CLASS
    } else if (error) {
      baseClass = FORM_INPUT_ERROR_CLASS
    } else {
      baseClass = FORM_TEXTAREA_CLASS
    }
    
    // Adiciona fonte monospace se necessário
    if (monospace) {
      baseClass += ' font-mono text-sm'
    }
    
    return baseClass
  }

  return (
    <FormField label={label} required={required} helperText={helperText} className={className}>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={getTextareaClass()}
      />
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </FormField>
  )
}
