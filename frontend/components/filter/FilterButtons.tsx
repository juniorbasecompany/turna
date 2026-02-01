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
    /** Array de valores selecionados. Usar selectedValues.includes(valor) para filtrar. */
    selectedValues: T[]
    onToggle: (value: T) => void
    onToggleAll: () => void
    allOptionLabel?: string
}

export function FilterButtons<T = string>({
    title,
    options,
    selectedValues,
    onToggle,
    onToggleAll,
    allOptionLabel = 'Todos',
}: FilterButtonsProps<T>) {
    // Ordenar opções alfabeticamente por label
    const sortedOptions = useMemo(() => {
        return [...options].sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'))
    }, [options])

    // Verificar se todos estão selecionados
    const allSelected = useMemo(() => {
        return sortedOptions.every((option) => selectedValues.includes(option.value))
    }, [sortedOptions, selectedValues])

    // Componente interno para checkbox customizado
    const CustomCheckbox = ({
        checked,
        color,
        onClick
    }: {
        checked: boolean
        color?: string
        onClick?: (e: React.MouseEvent) => void
    }) => {
        const backgroundColor = checked
            ? (color ? getColorFromClass(color) : '#1f2937')
            : undefined
        const borderColor = checked
            ? (color ? getColorFromClass(color) : '#1f2937')
            : undefined

        const handleClick = (e: React.MouseEvent) => {
            e.stopPropagation()
            if (onClick) {
                onClick(e)
            }
        }

        return (
            <div
                className="relative w-4 h-4 flex items-center justify-center cursor-pointer"
                onClick={handleClick}
            >
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => { }} // Controlado pelo onClick
                    onClick={handleClick}
                    className="w-4 h-4 appearance-none border rounded focus:ring-purple-500 cursor-pointer bg-white border-gray-300"
                    style={checked
                        ? {
                            backgroundColor,
                            borderColor,
                        }
                        : undefined
                    }
                    readOnly
                    tabIndex={-1}
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

    return (
        <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
                {title}
            </label>
            <div className="flex flex-wrap gap-3">
                <button
                    type="button"
                    onClick={onToggleAll}
                    className="flex items-center gap-2 px-3 py-2 text-sm rounded-md border transition-colors bg-white border-gray-300 hover:bg-gray-50 cursor-pointer"
                >
                    <CustomCheckbox
                        checked={allSelected}
                        onClick={(e) => {
                            e.stopPropagation()
                            onToggleAll()
                        }}
                    />
                    <span className={allSelected ? 'text-gray-900' : 'text-gray-700'}>
                        {allOptionLabel}
                    </span>
                </button>
                {sortedOptions.map((option, index) => {
                    const isSelected = selectedValues.includes(option.value)
                    const key = option.value !== null && option.value !== undefined
                        ? String(option.value)
                        : `null-${index}`
                    return (
                        <button
                            key={key}
                            type="button"
                            onClick={() => onToggle(option.value)}
                            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md border transition-colors bg-white border-gray-300 hover:bg-gray-50 cursor-pointer"
                        >
                            <CustomCheckbox
                                checked={isSelected}
                                color={option.color}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onToggle(option.value)
                                }}
                            />
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
