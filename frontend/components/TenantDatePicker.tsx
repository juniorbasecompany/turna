'use client'

import { Calendar } from '@/components/Calendar'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { formatLocalDateOnly } from '@/lib/tenantFormat'
import { useEffect, useRef, useState } from 'react'

export interface TenantDatePickerProps {
    value: Date | null // Data selecionada (ou null se vazio)
    onChange: (value: Date | null) => void // Callback quando data muda
    label?: string
    placeholder?: string // Se não fornecido, será gerado do locale do tenant
    disabled?: boolean
    minDate?: Date
    maxDate?: Date
    id?: string
    name?: string
    showFlash?: boolean
}

/**
 * Componente DatePicker reutilizável que formata datas conforme configurações do tenant.
 *
 * - Exibe data no formato do locale do tenant (ex: DD/MM/YYYY para pt-BR)
 * - Calendário popover para seleção visual
 * - Botão para limpar seleção
 * - Acessibilidade básica (teclado, aria-labels)
 */
export function TenantDatePicker({
    value,
    onChange,
    label,
    placeholder,
    disabled = false,
    minDate,
    maxDate,
    id,
    name,
    showFlash = false,
}: TenantDatePickerProps) {
    const { settings } = useTenantSettings()
    const [isOpen, setIsOpen] = useState(false)
    const [displayMonth, setDisplayMonth] = useState(() => value || new Date())
    const containerRef = useRef<HTMLDivElement>(null)

    // Fechar popover ao clicar fora
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside)
            return () => document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [isOpen])

    // Gerar placeholder do locale se não fornecido
    // pt-BR: dd/mm/aaaa, en-US: mm/dd/yyyy
    const displayPlaceholder = placeholder || (settings?.locale.startsWith('pt') ? 'dd/mm/aaaa' : 'mm/dd/yyyy')

    // Formatar valor exibido
    const displayValue = value && settings ? formatLocalDateOnly(value, settings) : ''

    // Selecionar data
    const handleDateSelect = (day: number) => {
        const selectedDate = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day)
        onChange(selectedDate)
        setIsOpen(false)
    }

    // Limpar seleção
    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation()
        onChange(null)
        setIsOpen(false)
    }

    // Handler para botão Limpar do calendário
    const handleCalendarClear = () => {
        onChange(null)
        setIsOpen(false)
    }

    // Handler para botão Hoje do calendário
    const handleCalendarToday = () => {
        const today = new Date()
        onChange(today)
        setDisplayMonth(today)
        setIsOpen(false)
    }

    if (!settings) {
        // Fallback se settings não estiver carregado
        return (
            <div className="w-full">
                {label && (
                    <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
                )}
                <input
                    type="text"
                    readOnly
                    disabled={disabled}
                    placeholder={displayPlaceholder}
                    className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-[0.5px] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${showFlash
                        ? 'border-red-500 bg-red-50 focus:ring-red-500 focus:border-red-500'
                        : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
                        }`}
                    id={id}
                    name={name}
                />
            </div>
        )
    }

    return (
        <div ref={containerRef} className="relative w-full">
            {label && (
                <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-2">
                    {label}
                </label>
            )}
            <div className="relative">
                <input
                    type="text"
                    readOnly
                    value={displayValue}
                    placeholder={displayPlaceholder}
                    disabled={disabled}
                    onClick={() => !disabled && setIsOpen(!isOpen)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            if (!disabled) setIsOpen(!isOpen)
                        }
                        if (e.key === 'Escape') {
                            setIsOpen(false)
                        }
                    }}
                    className={`w-full px-3 py-2 pr-20 border rounded-md shadow-sm focus:outline-none focus:ring-[0.5px] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${showFlash
                        ? 'border-red-500 bg-red-50 focus:ring-red-500 focus:border-red-500'
                        : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
                        }`}
                    id={id}
                    name={name}
                    aria-label={label || 'Selecionar data'}
                    aria-haspopup="dialog"
                    aria-expanded={isOpen}
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    {value && (
                        <button
                            type="button"
                            onClick={handleClear}
                            className="p-1 text-gray-400 hover:text-gray-600 focus:outline-none"
                            aria-label="Limpar data"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={() => !disabled && setIsOpen(!isOpen)}
                        disabled={disabled}
                        className="p-1 text-gray-400 hover:text-gray-600 focus:outline-none disabled:opacity-50"
                        aria-label="Abrir calendário"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Calendário Popover */}
            {isOpen && (
                <div className="absolute z-50 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
                    <Calendar
                        selectedDate={value}
                        tempDate={null}
                        displayMonth={displayMonth}
                        onDisplayMonthChange={setDisplayMonth}
                        onDateSelect={handleDateSelect}
                        onClear={handleCalendarClear}
                        onToday={handleCalendarToday}
                        minDate={minDate}
                        maxDate={maxDate}
                        width="min-w-[280px]"
                        showActionButtons={true}
                    />
                </div>
            )}
        </div>
    )
}
