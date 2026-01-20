'use client'

import { ReactNode } from 'react'

interface FormFieldProps {
    /** Label do campo */
    label: string
    /** Se o campo é obrigatório */
    required?: boolean
    /** Texto informativo abaixo do campo */
    helperText?: string
    /** Mensagem de erro abaixo do campo */
    error?: string
    /** Conteúdo do campo (input, select, textarea, etc) */
    children: ReactNode
    /** Classe CSS adicional para o container */
    className?: string
}

/**
 * Componente reutilizável para campos de formulário.
 * Padroniza label, texto informativo e mensagens de erro.
 */
export function FormField({
    label,
    required = false,
    helperText,
    error,
    children,
    className = '',
}: FormFieldProps) {
    return (
        <div className={className}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
                {label} {required && <span className="text-red-500">*</span>}
            </label>
            {children}
            {helperText && !error && (
                <p className="mt-1 text-xs text-gray-500">{helperText}</p>
            )}
            {error && (
                <p className="mt-1 text-xs text-red-600">{error}</p>
            )}
        </div>
    )
}
