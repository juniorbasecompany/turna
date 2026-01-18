'use client'

import { useEffect, useState } from 'react'

export interface ColorPickerProps {
    value: string | null // Cor atual em formato hexadecimal (#RRGGBB)
    onChange: (color: string | null) => void // Callback quando cor muda
    label?: string
    disabled?: boolean
}

/**
 * Componente de seletor de cores para backgrounds de cards.
 *
 * Oferece uma paleta de cores pastéis/suaves adequadas para background,
 * com controle de intensidade (mais claro/mais escuro) mantendo dentro
 * de um range aceitável para boa legibilidade.
 */
export function ColorPicker({ value, onChange, label, disabled }: ColorPickerProps) {
    // Cores base pastéis (em RGB) - 9 cores
    const baseColors = [
        { r: 147, g: 197, b: 253 }, // blue-300
        { r: 134, g: 239, b: 172 }, // green-300
        { r: 253, g: 224, b: 71 }, // yellow-300
        { r: 253, g: 186, b: 116 }, // orange-300
        { r: 251, g: 146, b: 60 }, // rose-300
        { r: 196, g: 181, b: 253 }, // purple-300
        { r: 103, g: 232, b: 249 }, // cyan-300
        { r: 94, g: 234, b: 212 }, // teal-300
        { r: 251, g: 113, b: 133 }, // pink-300
    ]

    // Intensidade: valor entre 0.5 (mais claro) e 1.2 (mais escuro, mas ainda suave)
    // Valor padrão: 1.0 (cor base)
    const MIN_INTENSITY = 0.5
    const MAX_INTENSITY = 1.2
    const INTENSITY_STEP = 0.1

    const [selectedBaseIndex, setSelectedBaseIndex] = useState<number | null>(null)
    const [intensity, setIntensity] = useState<number>(1.0) // Padrão: cor base

    // Converter RGB para hexadecimal
    const rgbToHex = (r: number, g: number, b: number): string => {
        const toHex = (n: number) => {
            const hex = Math.round(Math.max(0, Math.min(255, n))).toString(16)
            return hex.length === 1 ? '0' + hex : hex
        }
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`
    }

    // Converter hexadecimal para RGB
    const hexToRgb = (hex: string): { r: number; g: number; b: number } | null => {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
        return result
            ? {
                r: parseInt(result[1], 16),
                g: parseInt(result[2], 16),
                b: parseInt(result[3], 16),
            }
            : null
    }

    // Calcular cor com intensidade aplicada
    const getColorWithIntensity = (baseColor: { r: number; g: number; b: number }, intensityValue: number): string => {
        const r = Math.round(baseColor.r * intensityValue)
        const g = Math.round(baseColor.g * intensityValue)
        const b = Math.round(baseColor.b * intensityValue)
        return rgbToHex(r, g, b)
    }

    // Inicializar estado baseado no valor atual
    useEffect(() => {
        if (!value) {
            setSelectedBaseIndex(null)
            setIntensity(1.0)
        }
        // Se value existe mas não temos seleção, tentar encontrar match aproximado
        else if (value && selectedBaseIndex === null) {
            const rgb = hexToRgb(value)
            if (rgb) {
                // Tentar encontrar a cor base e intensidade mais próximas
                let bestMatch = { index: 0, intensity: 1.0, diff: Infinity }
                baseColors.forEach((base, index) => {
                    // Testar diferentes valores de intensidade
                    for (let testIntensity = MIN_INTENSITY; testIntensity <= MAX_INTENSITY; testIntensity += INTENSITY_STEP) {
                        const testColor = getColorWithIntensity(base, testIntensity)
                        const testRgb = hexToRgb(testColor)
                        if (testRgb) {
                            const diff =
                                Math.abs(testRgb.r - rgb.r) +
                                Math.abs(testRgb.g - rgb.g) +
                                Math.abs(testRgb.b - rgb.b)
                            if (diff < bestMatch.diff) {
                                bestMatch = { index, intensity: testIntensity, diff }
                            }
                        }
                    }
                })
                setSelectedBaseIndex(bestMatch.index)
                setIntensity(bestMatch.intensity)
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [value])

    const handleColorSelect = (baseIndex: number) => {
        setSelectedBaseIndex(baseIndex)
        const color = getColorWithIntensity(baseColors[baseIndex], intensity)
        onChange(color)
    }

    const handleIntensityChange = (delta: number) => {
        const newIntensity = Math.max(
            MIN_INTENSITY,
            Math.min(MAX_INTENSITY, intensity + delta)
        )
        setIntensity(newIntensity)

        // Se há uma cor selecionada, atualizar a cor com a nova intensidade
        if (selectedBaseIndex !== null) {
            const color = getColorWithIntensity(baseColors[selectedBaseIndex], newIntensity)
            onChange(color)
        }
    }

    const handleNoColor = () => {
        setSelectedBaseIndex(null)
        setIntensity(1.0)
        onChange(null)
    }

    return (
        <div className="space-y-2">
            {label && (
                <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
            )}

            {/* Grid com 12 botões: 9 cores + 1 sem cor + 2 intensidade - sempre 3x4 fixo */}
            <div className="grid grid-cols-3 gap-2 w-fit">
                {/* 7 cores */}
                {baseColors.map((baseColor, baseIndex) => (
                    <button
                        key={baseIndex}
                        type="button"
                        onClick={() => handleColorSelect(baseIndex)}
                        disabled={disabled}
                        className={`aspect-square w-12 h-12 rounded-md border-2 transition-all ${selectedBaseIndex === baseIndex
                            ? 'border-blue-500 ring-2 ring-blue-200'
                            : 'border-gray-200 hover:border-gray-300'
                            } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        style={{
                            backgroundColor: getColorWithIntensity(baseColor, intensity),
                        }}
                    />
                ))}

                {/* Botão Sem cor */}
                <button
                    type="button"
                    onClick={handleNoColor}
                    disabled={disabled}
                    className={`aspect-square w-12 h-12 rounded-md border-2 transition-all ${!value
                        ? 'border-blue-500 ring-2 ring-blue-200'
                        : 'border-gray-200 hover:border-gray-300'
                        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} bg-white flex items-center justify-center`}
                    title="Sem cor"
                >
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>

                {/* Botão diminuir intensidade */}
                <button
                    type="button"
                    onClick={() => handleIntensityChange(-INTENSITY_STEP)}
                    disabled={disabled || intensity <= MIN_INTENSITY}
                    className="aspect-square w-12 h-12 rounded-md border-2 border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                    title="Diminuir intensidade"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                    </svg>
                </button>

                {/* Botão aumentar intensidade */}
                <button
                    type="button"
                    onClick={() => handleIntensityChange(INTENSITY_STEP)}
                    disabled={disabled || intensity >= MAX_INTENSITY}
                    className="aspect-square w-12 h-12 rounded-md border-2 border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                    title="Aumentar intensidade"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                </button>
            </div>
        </div>
    )
}
