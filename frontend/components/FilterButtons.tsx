'use client'

import { useMemo } from 'react'

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
                            ${allSelected
                                ? 'bg-gray-100 border-gray-300'
                                : 'bg-white border-gray-300 hover:bg-gray-50'
                            }
                            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        `}
                    >
                        <input
                            type="checkbox"
                            checked={allSelected}
                            onChange={() => {}} // Controlado pelo onClick do button
                            className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500 cursor-pointer"
                            disabled={disabled}
                            readOnly
                        />
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
                                ${isSelected
                                    ? 'bg-gray-100 border-gray-300'
                                    : 'bg-white border-gray-300 hover:bg-gray-50'
                                }
                                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            `}
                        >
                            <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => {}} // Controlado pelo onClick do button
                                className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500 cursor-pointer"
                                disabled={disabled}
                                readOnly
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
