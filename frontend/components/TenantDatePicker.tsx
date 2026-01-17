'use client'

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

    // Navegação do calendário
    const goToPreviousMonth = () => {
        setDisplayMonth(new Date(displayMonth.getFullYear(), displayMonth.getMonth() - 1, 1))
    }

    const goToNextMonth = () => {
        setDisplayMonth(new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 1))
    }

    // Gerar dias do mês
    const getDaysInMonth = (date: Date) => {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
    }

    const getFirstDayOfMonth = (date: Date) => {
        const firstDay = new Date(date.getFullYear(), date.getMonth(), 1)
        return firstDay.getDay()
    }

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

    // Verificar se data está selecionada
    const isSelected = (day: number) => {
        if (!value) return false
        const date = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day)
        return (
            date.getFullYear() === value.getFullYear() &&
            date.getMonth() === value.getMonth() &&
            date.getDate() === value.getDate()
        )
    }

    // Verificar se data está desabilitada
    const isDisabled = (day: number) => {
        const date = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day)
        if (minDate && date < minDate) return true
        if (maxDate && date > maxDate) return true
        return false
    }

    // Gerar array de dias para o calendário
    const daysInMonth = getDaysInMonth(displayMonth)
    const firstDay = getFirstDayOfMonth(displayMonth)
    const days: (number | null)[] = []

    // Preencher com nulls até o primeiro dia do mês
    for (let i = 0; i < firstDay; i++) {
        days.push(null)
    }

    // Adicionar dias do mês
    for (let day = 1; day <= daysInMonth; day++) {
        days.push(day)
    }

    // Nomes dos meses e dias da semana conforme locale do tenant
    const monthNames = settings
        ? Array.from({ length: 12 }, (_, i) => {
            const date = new Date(2024, i, 1)
            return new Intl.DateTimeFormat(settings.locale, { month: 'long' }).format(date)
        })
        : ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    // Gerar nomes dos dias da semana - começar em domingo (0)
    const dayNames = settings
        ? Array.from({ length: 7 }, (_, i) => {
            // Usar uma data fixa em domingo (2024-01-07 foi um domingo) e adicionar i dias
            const date = new Date(2024, 0, 7 + i)
            return new Intl.DateTimeFormat(settings.locale, { weekday: 'short' }).format(date)
        })
        : ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
                    className="w-full px-3 py-2 pr-20 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
                <div className="absolute z-50 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px]">
                    {/* Header do calendário */}
                    <div className="flex items-center justify-between mb-4">
                        <button
                            type="button"
                            onClick={goToPreviousMonth}
                            className="p-1 text-gray-600 hover:text-gray-900 focus:outline-none"
                            aria-label="Mês anterior"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                        <div className="font-medium text-gray-900">
                            {monthNames[displayMonth.getMonth()]} {displayMonth.getFullYear()}
                        </div>
                        <button
                            type="button"
                            onClick={goToNextMonth}
                            className="p-1 text-gray-600 hover:text-gray-900 focus:outline-none"
                            aria-label="Próximo mês"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        </button>
                    </div>

                    {/* Dias da semana */}
                    <div className="grid grid-cols-7 gap-1 mb-2">
                        {dayNames.map((day, index) => (
                            <div key={index} className="text-center text-xs font-medium text-gray-500 py-1">
                                {day}
                            </div>
                        ))}
                    </div>

                    {/* Dias do mês */}
                    <div className="grid grid-cols-7 gap-1">
                        {days.map((day, index) => {
                            if (day === null) {
                                return <div key={index} className="py-2" />
                            }

                            const disabled = isDisabled(day)
                            const selected = isSelected(day)

                            return (
                                <button
                                    key={index}
                                    type="button"
                                    onClick={() => !disabled && handleDateSelect(day)}
                                    disabled={disabled}
                                    className={`
                    py-2 text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500
                    ${selected
                                            ? 'bg-blue-600 text-white font-medium'
                                            : disabled
                                                ? 'text-gray-300 cursor-not-allowed'
                                                : 'text-gray-700 hover:bg-gray-100'}
                  `}
                                    aria-label={`Selecionar dia ${day}`}
                                >
                                    {day}
                                </button>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}
