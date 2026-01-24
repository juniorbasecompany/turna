'use client'

import { Calendar } from '@/components/Calendar'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { formatDateTime } from '@/lib/tenantFormat'
import { useEffect, useRef, useState } from 'react'

export interface TenantDateTimePickerProps {
    value: Date | null // Data/hora selecionada (ou null se vazio)
    onChange: (value: Date | null) => void // Callback quando data/hora muda
    label?: string
    placeholder?: string
    disabled?: boolean
    minDate?: Date
    maxDate?: Date
    id?: string
    name?: string
}

/**
 * Componente DateTimePicker reutilizável que formata datas/horas conforme configurações do tenant.
 *
 * - Exibe data/hora no formato do locale do tenant (ex: DD/MM/YYYY HH:mm para pt-BR)
 * - Calendário popover para seleção visual de data
 * - Seletor de hora com 4 colunas: hora (0-11), dezenas de minutos, unidades de minutos, AM/PM
 * - Botão OK para confirmar seleção
 * - Botão para limpar seleção
 * - Acessibilidade básica (teclado, aria-labels)
 */
export function TenantDateTimePicker({
    value,
    onChange,
    label,
    placeholder,
    disabled = false,
    minDate,
    maxDate,
    id,
    name,
}: TenantDateTimePickerProps) {
    const { settings } = useTenantSettings()
    const [isOpen, setIsOpen] = useState(false)
    const [displayMonth, setDisplayMonth] = useState(() => value || new Date())
    const [tempDate, setTempDate] = useState<Date | null>(value)

    // Converter hora 24h para 0-11 + AM/PM
    const get12Hour = (hour24: number): number => {
        if (hour24 === 0 || hour24 === 12) return 0
        if (hour24 > 12) return hour24 - 12
        return hour24
    }

    const getAmPm = (hour24: number): 'AM' | 'PM' => {
        return hour24 >= 12 ? 'PM' : 'AM'
    }

    // Estados para seleção de hora (0-11 format)
    const [tempHour12, setTempHour12] = useState(() => {
        if (value) return get12Hour(value.getHours())
        return get12Hour(new Date().getHours())
    })
    const [tempMinuteTens, setTempMinuteTens] = useState(() => {
        if (value) return Math.floor(value.getMinutes() / 10) * 10
        return Math.floor(new Date().getMinutes() / 10) * 10
    })
    const [tempMinuteUnits, setTempMinuteUnits] = useState(() => {
        if (value) return value.getMinutes() % 10
        return new Date().getMinutes() % 10
    })
    const [tempAmPm, setTempAmPm] = useState<'AM' | 'PM'>(() => {
        if (value) return getAmPm(value.getHours())
        return getAmPm(new Date().getHours())
    })

    const containerRef = useRef<HTMLDivElement>(null)

    // Atualizar valores temporários quando o popover abre
    useEffect(() => {
        if (isOpen) {
            if (value) {
                setTempDate(new Date(value))
                setTempHour12(get12Hour(value.getHours()))
                setTempMinuteTens(Math.floor(value.getMinutes() / 10) * 10)
                setTempMinuteUnits(value.getMinutes() % 10)
                setTempAmPm(getAmPm(value.getHours()))
            } else {
                const now = new Date()
                setTempDate(now)
                const hour24 = now.getHours()
                setTempHour12(get12Hour(hour24))
                setTempMinuteTens(Math.floor(now.getMinutes() / 10) * 10)
                setTempMinuteUnits(now.getMinutes() % 10)
                setTempAmPm(getAmPm(hour24))
            }
        }
    }, [isOpen, value])

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

    // Gerar placeholder
    const displayPlaceholder = placeholder || (settings?.locale.startsWith('pt') ? 'dd/mm/aaaa hh:mm' : 'mm/dd/yyyy hh:mm')

    // Formatar valor exibido
    const displayValue = value && settings ? formatDateTime(value.toISOString(), settings, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }) : ''

    // Selecionar data (temporária, não confirma ainda)
    const handleDateSelect = (day: number) => {
        if (!tempDate) {
            setTempDate(new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day))
        } else {
            const newDate = new Date(tempDate)
            newDate.setFullYear(displayMonth.getFullYear())
            newDate.setMonth(displayMonth.getMonth())
            newDate.setDate(day)
            setTempDate(newDate)
        }
    }

    // Confirmar seleção (botão OK)
    const handleConfirm = () => {
        if (tempDate) {
            const finalDate = new Date(tempDate)

            // Converter hora 0-11 + AM/PM para 24h
            let hour24 = tempHour12
            if (tempAmPm === 'PM') {
                if (tempHour12 === 0) {
                    hour24 = 12
                } else {
                    hour24 = tempHour12 + 12
                }
            } else {
                // AM: 0 = 0h, 1-11 = 1h-11h
                hour24 = tempHour12
            }

            // Calcular minutos totais (dezenas + unidades)
            const totalMinutes = tempMinuteTens + tempMinuteUnits

            finalDate.setHours(hour24)
            finalDate.setMinutes(totalMinutes)
            finalDate.setSeconds(0)
            finalDate.setMilliseconds(0)
            onChange(finalDate)
            setIsOpen(false)
        }
    }

    // Limpar seleção
    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation()
        onChange(null)
        setIsOpen(false)
    }

    // Handler para botão Limpar do calendário
    const handleCalendarClear = () => {
        setTempDate(null)
    }

    // Handler para botão Hoje do calendário
    const handleCalendarToday = () => {
        const today = new Date()
        setTempDate(today)
        setDisplayMonth(today)
    }

    // Gerar arrays para seleção
    const hours12 = Array.from({ length: 12 }, (_, i) => i) // 0 a 11
    const minuteTens = [0, 10, 20, 30, 40, 50] // Dezenas de minutos
    const minuteUnits = Array.from({ length: 10 }, (_, i) => i) // 0 a 9
    const amPmOptions: ('AM' | 'PM')[] = ['AM', 'PM']

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
                    aria-label={label || 'Selecionar data e hora'}
                    aria-haspopup="dialog"
                    aria-expanded={isOpen}
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    {value && (
                        <button
                            type="button"
                            onClick={handleClear}
                            className="p-1 text-gray-400 hover:text-gray-600 focus:outline-none"
                            aria-label="Limpar data e hora"
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

            {/* Calendário e Time Picker Popover */}
            {isOpen && (
                <div className="absolute z-50 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4 flex flex-col md:flex-row gap-6">
                    {/* Região do Calendário - Tamanho fixo */}
                    <Calendar
                        selectedDate={value}
                        tempDate={tempDate}
                        displayMonth={displayMonth}
                        onDisplayMonthChange={setDisplayMonth}
                        onDateSelect={handleDateSelect}
                        onClear={handleCalendarClear}
                        onToday={handleCalendarToday}
                        minDate={minDate}
                        maxDate={maxDate}
                        width="w-[380px]"
                        showActionButtons={true}
                        headerContent={
                            tempDate && (
                                <div className="text-base font-medium text-blue-600">
                                    {(() => {
                                        const finalDate = new Date(tempDate)
                                        let hour24 = tempHour12
                                        if (tempAmPm === 'PM') {
                                            if (tempHour12 === 0) {
                                                hour24 = 12
                                            } else {
                                                hour24 = tempHour12 + 12
                                            }
                                        } else {
                                            hour24 = tempHour12
                                        }
                                        const totalMinutes = tempMinuteTens + tempMinuteUnits
                                        finalDate.setHours(hour24)
                                        finalDate.setMinutes(totalMinutes)
                                        finalDate.setSeconds(0)
                                        finalDate.setMilliseconds(0)

                                        if (settings) {
                                            return formatDateTime(finalDate.toISOString(), settings, {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })
                                        }
                                        return finalDate.toLocaleString('pt-BR', {
                                            day: '2-digit',
                                            month: '2-digit',
                                            year: 'numeric',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        })
                                    })()}
                                </div>
                            )
                        }
                    />

                    {/* Região das Horas - Tamanho fixo */}
                    <div className="w-[270px] flex-shrink-0 pt-6 md:pt-0 md:pl-6 flex flex-col relative">
                        {/* Seletores de hora, minutos e AM/PM */}
                        <div className="flex gap-3 items-start justify-center">
                            {/* Hora (0-11) */}
                            <div className="flex flex-col items-center relative">
                                <div className="text-xs text-gray-500 absolute -top-2 left-1/2 -translate-x-1/2 bg-white px-1">hora</div>
                                <div className="border border-gray-300 rounded w-14 pt-2 px-1 pb-1">
                                    {hours12.map((hour) => (
                                        <button
                                            key={hour}
                                            type="button"
                                            onClick={() => setTempHour12(hour)}
                                            className={`w-full py-2 text-sm rounded-md ${tempHour12 === hour
                                                ? 'bg-gray-200 text-gray-800'
                                                : 'text-gray-700 hover:bg-gray-100'
                                                }`}
                                        >
                                            {String(hour).padStart(2, '0')}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Minutos - Dezenas e Unidades envolvidas */}
                            <div className="flex flex-col items-center relative">
                                <div className="text-xs text-gray-500 absolute -top-2 left-1/2 -translate-x-1/2 bg-white px-1">minuto</div>
                                <div className="border border-gray-300 rounded p-1 pt-2 flex gap-1">
                                    {/* Dezenas de minutos (00, 10, 20, 30, 40, 50) */}
                                    <div className="flex flex-col items-center">
                                        <div className="rounded w-12">
                                            {minuteTens.map((tens) => (
                                                <button
                                                    key={tens}
                                                    type="button"
                                                    onClick={() => setTempMinuteTens(tens)}
                                                    className={`w-full py-2 text-sm rounded-md ${tempMinuteTens === tens
                                                        ? 'bg-gray-200 text-gray-800'
                                                        : 'text-gray-700 hover:bg-gray-100'
                                                        }`}
                                                >
                                                    {String(tens).padStart(2, '0')}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Unidades de minutos (0-9) */}
                                    <div className="flex flex-col items-center">
                                        <div className="rounded w-12">
                                            {minuteUnits.map((unit) => (
                                                <button
                                                    key={unit}
                                                    type="button"
                                                    onClick={() => setTempMinuteUnits(unit)}
                                                    className={`w-full py-2 text-sm rounded-md ${tempMinuteUnits === unit
                                                        ? 'bg-gray-200 text-gray-800'
                                                        : 'text-gray-700 hover:bg-gray-100'
                                                        }`}
                                                >
                                                    {String(unit)}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* AM/PM */}
                            <div className="flex flex-col items-center">
                                <div className="rounded w-12 pt-[9px]">
                                    {amPmOptions.map((ampm) => (
                                        <button
                                            key={ampm}
                                            type="button"
                                            onClick={() => setTempAmPm(ampm)}
                                            className={`w-full py-2 text-sm rounded-md ${tempAmPm === ampm
                                                ? 'bg-gray-200 text-gray-800'
                                                : 'text-gray-700 hover:bg-gray-100'
                                                }`}
                                        >
                                            {ampm}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Botão OK - Fixo no canto inferior direito */}
                        {tempDate && (
                            <div className="absolute bottom-0 right-0">
                                <button
                                    type="button"
                                    onClick={handleConfirm}
                                    disabled={!tempDate}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                >
                                    Ok
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
