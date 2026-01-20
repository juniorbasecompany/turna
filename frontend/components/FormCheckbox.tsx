'use client'

interface FormCheckboxProps {
    /** ID do checkbox */
    id: string
    /** Label do checkbox */
    label: string
    /** Se o checkbox está marcado */
    checked: boolean
    /** Callback quando o estado muda */
    onChange: (checked: boolean) => void
    /** Se o checkbox está desabilitado */
    disabled?: boolean
    /** Classe CSS adicional para o container */
    className?: string
}

/**
 * Componente reutilizável para checkbox com label.
 * Padroniza o estilo e comportamento dos checkboxes nos formulários.
 */
export function FormCheckbox({
    id,
    label,
    checked,
    onChange,
    disabled = false,
    className = '',
}: FormCheckboxProps) {
    return (
        <div className={`flex items-center ${className}`}>
            <input
                type="checkbox"
                id={id}
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={disabled}
            />
            <label htmlFor={id} className="ml-2 block text-sm text-gray-700">
                {label}
            </label>
        </div>
    )
}
