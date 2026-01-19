'use client'

import { useTenantSettings } from '@/contexts/TenantSettingsContext'

export interface CalendarProps {
    /** Data selecionada (para destacar no calendário) */
    selectedDate: Date | null
    /** Data temporária (para DateTimePicker que não fecha imediatamente) */
    tempDate: Date | null
    /** Mês/ano sendo exibido */
    displayMonth: Date
    /** Callback para mudar o mês exibido */
    onDisplayMonthChange: (date: Date) => void
    /** Callback quando um dia é selecionado */
    onDateSelect: (day: number) => void
    /** Callback para limpar seleção */
    onClear?: () => void
    /** Callback para selecionar hoje */
    onToday?: () => void
    /** Data mínima permitida */
    minDate?: Date
    /** Data máxima permitida */
    maxDate?: Date
    /** Largura fixa do calendário */
    width?: string
    /** Mostrar botões de ação (Limpar e Hoje) */
    showActionButtons?: boolean
    /** Conteúdo customizado para o rodapé (ex: exibição de data/hora) */
    footerContent?: React.ReactNode
}

/**
 * Componente Calendar reutilizável com layout otimizado.
 *
 * - Header com navegação de mês
 * - Grid de dias da semana
 * - Grid de dias do mês com botões
 * - Botões de ação (Limpar e Hoje) opcionais
 * - Suporte a datas mínimas/máximas
 * - Localização baseada no tenant
 */
export function Calendar({
    selectedDate,
    tempDate,
    displayMonth,
    onDisplayMonthChange,
    onDateSelect,
    onClear,
    onToday,
    minDate,
    maxDate,
    width = 'w-[380px]',
    showActionButtons = true,
    footerContent,
}: CalendarProps) {
    const { settings } = useTenantSettings()

    // Navegação do calendário
    const goToPreviousMonth = () => {
        onDisplayMonthChange(new Date(displayMonth.getFullYear(), displayMonth.getMonth() - 1, 1))
    }

    const goToNextMonth = () => {
        onDisplayMonthChange(new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 1))
    }

    // Gerar dias do mês
    const getDaysInMonth = (date: Date) => {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
    }

    const getFirstDayOfMonth = (date: Date) => {
        const firstDay = new Date(date.getFullYear(), date.getMonth(), 1)
        return firstDay.getDay()
    }

    // Verificar se data está selecionada (usa tempDate se disponível, senão selectedDate)
    const isSelected = (day: number) => {
        const dateToCheck = tempDate || selectedDate
        if (!dateToCheck) return false
        return (
            day === dateToCheck.getDate() &&
            displayMonth.getMonth() === dateToCheck.getMonth() &&
            displayMonth.getFullYear() === dateToCheck.getFullYear()
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

    // Nomes dos meses e dias da semana em português (padrão)
    const monthNames = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    const dayNames = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

    return (
        <div className={`${width} flex-shrink-0 flex flex-col relative`}>
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
            <div className="grid grid-cols-7 mb-4">
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
                            onClick={() => !disabled && onDateSelect(day)}
                            disabled={disabled}
                            className={`w-full py-2 px-1 text-sm rounded-md min-w-[48px] ${selected
                                ? 'bg-blue-600 text-white font-medium'
                                : disabled
                                    ? 'text-gray-300 cursor-not-allowed'
                                    : 'text-gray-700 hover:bg-gray-100'
                                }`}
                            aria-label={`Selecionar dia ${day}`}
                        >
                            {day}
                        </button>
                    )
                })}
            </div>

            {/* Botões de ação do calendário */}
            {showActionButtons && (
                <div className="flex justify-between items-center mb-3">
                    {onClear && (
                        <button
                            type="button"
                            onClick={onClear}
                            className="text-sm text-gray-600 hover:text-gray-900 focus:outline-none pb-4"
                        >
                            Limpar
                        </button>
                    )}
                    {onToday && (
                        <button
                            type="button"
                            onClick={onToday}
                            className="text-sm text-gray-600 hover:text-gray-900 focus:outline-none pb-4"
                        >
                            Hoje
                        </button>
                    )}
                </div>
            )}

            {/* Conteúdo customizado do rodapé (ex: exibição de data/hora) */}
            {footerContent && (
                <div className="absolute bottom-0 left-0">
                    {footerContent}
                </div>
            )}
        </div>
    )
}
