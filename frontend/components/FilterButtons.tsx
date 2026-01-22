'use client'

import { useMemo } from 'react'

// Helper para converter classes Tailwind de cor em valores hex
function getColorFromClass(colorClass: string): string {
    const colorMap: Record<string, string> = {
        'text-green-600': '#16a34a',
        'text-yellow-600': '#ca8a04',
        'text-red-600': '#dc2626',
        'text-gray-600': '#4b5563',
        'text-blue-600': '#2563eb',
        'text-purple-600': '#9333ea',
    }
    return colorMap[colorClass] || '#1f2937' // fallback para gray-800
}

export interface FilterOption<T = string> {
    value: T
    label: string
    color?: string // Cor do texto (ex: 'text-blue-600')
}

interface FilterButtonsProps<T = string> {
    title: string
    options: FilterOption<T>[]
    selectedValues: Set<T>
    onToggle: (value: T) => void
    onToggleAll?: () => void
    showAllOption?: boolean
    allOptionLabel?: string
    disabled?: boolean
}

export function FilterButtons<T = string>({
    title,
    options,
    selectedValues,
    onToggle,
    onToggleAll,
    showAllOption = true,
    allOptionLabel = 'Todos',
    disabled = false,
}: FilterButtonsProps<T>) {
    // Ordenar opções alfabeticamente por label
    const sortedOptions = useMemo(() => {
        return [...options].sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'))
    }, [options])

    // Verificar se todos estão selecionados
    const allSelected = useMemo(() => {
        return sortedOptions.every((option) => selectedValues.has(option.value))
    }, [sortedOptions, selectedValues])

    // Componente interno para checkbox customizado
    const CustomCheckbox = ({ checked, color }: { checked: boolean; color?: string }) => {
        const backgroundColor = checked
            ? (color ? getColorFromClass(color) : '#1f2937')
            : undefined
        const borderColor = checked
            ? (color ? getColorFromClass(color) : '#1f2937')
            : undefined

        return (
            <div className="relative w-4 h-4 flex items-center justify-center">
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => { }} // Controlado pelo onClick do button
                    className="w-4 h-4 appearance-none border rounded focus:ring-purple-500 cursor-pointer bg-white border-gray-300"
                    style={checked
                        ? {
                            backgroundColor,
                            borderColor,
                        }
                        : undefined
                    }
                    disabled={disabled}
                    readOnly
                />
                {checked && (
                    <svg
                        className="absolute w-3.5 h-3.5 pointer-events-none"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={3}
                            d="M5 13l4 4L19 7"
                            style={{ stroke: 'white' }}
                        />
                    </svg>
                )}
            </div>
        )
    }

    // Handler para toggle all
    const handleToggleAll = () => {
        if (onToggleAll) {
            onToggleAll()
        } else {
            // Se não há handler customizado, usar lógica padrão
            if (allSelected) {
                // Deselecionar todos
                sortedOptions.forEach((option) => {
                    if (selectedValues.has(option.value)) {
                        onToggle(option.value)
                    }
                })
            } else {
                // Selecionar todos
                sortedOptions.forEach((option) => {
                    if (!selectedValues.has(option.value)) {
                        onToggle(option.value)
                    }
                })
            }
        }
    }

    return (
        <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
                {title}
            </label>
            <div className="flex flex-wrap gap-3">
                {showAllOption && (
                    <button
                        type="button"
                        onClick={handleToggleAll}
                        disabled={disabled}
                        className={`
                            flex items-center gap-2 px-3 py-2 text-sm rounded-md border transition-colors
                            bg-white border-gray-300 hover:bg-gray-50
                            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        `}
                    >
                        <CustomCheckbox checked={allSelected} />
                        <span className={allSelected ? 'text-gray-900' : 'text-gray-700'}>
                            {allOptionLabel}
                        </span>
                    </button>
                )}

                {sortedOptions.map((option, index) => {
                    const isSelected = selectedValues.has(option.value)
                    // Usar index como fallback para key quando value é null ou undefined
                    const key = option.value !== null && option.value !== undefined
                        ? String(option.value)
                        : `null-${index}`
                    return (
                        <button
                            key={key}
                            type="button"
                            onClick={() => onToggle(option.value)}
                            disabled={disabled}
                            className={`
                                flex items-center gap-2 px-3 py-2 text-sm rounded-md border transition-colors
                                bg-white border-gray-300 hover:bg-gray-50
                                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            `}
                        >
                            <CustomCheckbox checked={isSelected} color={option.color} />
                            <span className={option.color || (isSelected ? 'text-gray-900' : 'text-gray-700')}>
                                {option.label}
                            </span>
                        </button>
                    )
                })}
            </div>
        </div>
    )
}
