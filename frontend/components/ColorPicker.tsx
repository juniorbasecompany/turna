'use client'

import { useEffect, useState, useRef } from 'react'

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
    // Cores base claras (em RGB) - 9 cores distintas (nível 200 do Tailwind para garantir legibilidade com texto preto)
    const baseColors = [
        { r: 219, g: 234, b: 254 }, // blue-200 - Azul
        { r: 187, g: 247, b: 208 }, // green-200 - Verde
        { r: 254, g: 249, b: 195 }, // yellow-200 - Amarelo
        { r: 254, g: 215, b: 170 }, // orange-200 - Laranja
        { r: 254, g: 202, b: 202 }, // red-200 - Vermelho
        { r: 233, g: 213, b: 255 }, // purple-200 - Roxo
        { r: 199, g: 210, b: 254 }, // indigo-200 - Índigo
        { r: 251, g: 207, b: 232 }, // pink-200 - Rosa
        { r: 165, g: 243, b: 252 }, // cyan-200 - Ciano
    ]

    // Intensidade: valor entre 0.7 (mais claro) e 1.0 (cor base, máximo permitido)
    // Valor padrão: 1.0 (intensidade máxima)
    const MIN_INTENSITY = 0.7
    const MAX_INTENSITY = 1.0
    const INTENSITY_STEP = 0.02 // Passo menor para mudanças mais suaves

    const [selectedBaseIndex, setSelectedBaseIndex] = useState<number | null>(null)
    const [intensity, setIntensity] = useState<number>(1.0) // Padrão: intensidade máxima
    const intensityIntervalRef = useRef<NodeJS.Timeout | null>(null)

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
        setIntensity((prevIntensity) => {
            const newIntensity = Math.max(
                MIN_INTENSITY,
                Math.min(MAX_INTENSITY, prevIntensity + delta)
            )

            // Se há uma cor selecionada, atualizar a cor com a nova intensidade
            if (selectedBaseIndex !== null) {
                const color = getColorWithIntensity(baseColors[selectedBaseIndex], newIntensity)
                onChange(color)
            }

            return newIntensity
        })
    }

    // Iniciar mudança contínua de intensidade
    const startIntensityChange = (delta: number) => {
        // Primeira mudança imediata
        handleIntensityChange(delta)

        // Limpar intervalo anterior se existir
        if (intensityIntervalRef.current) {
            clearInterval(intensityIntervalRef.current)
        }

        // Configurar intervalo para mudanças contínuas
        intensityIntervalRef.current = setInterval(() => {
            handleIntensityChange(delta)
        }, 50) // Atualiza a cada 50ms para mudanças mais suaves
    }

    // Parar mudança contínua de intensidade
    const stopIntensityChange = () => {
        if (intensityIntervalRef.current) {
            clearInterval(intensityIntervalRef.current)
            intensityIntervalRef.current = null
        }
    }

    // Limpar intervalo ao desmontar componente
    useEffect(() => {
        return () => {
            if (intensityIntervalRef.current) {
                clearInterval(intensityIntervalRef.current)
            }
        }
    }, [])

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

                {/* Botão - (deixar mais escuro) */}
                <button
                    type="button"
                    onMouseDown={() => !disabled && intensity < MAX_INTENSITY && startIntensityChange(INTENSITY_STEP)}
                    onMouseUp={stopIntensityChange}
                    onMouseLeave={stopIntensityChange}
                    onTouchStart={() => !disabled && intensity < MAX_INTENSITY && startIntensityChange(INTENSITY_STEP)}
                    onTouchEnd={stopIntensityChange}
                    disabled={disabled || intensity >= MAX_INTENSITY}
                    className="aspect-square w-12 h-12 rounded-md border-2 border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center select-none"
                    title="Deixar mais escuro (mantenha pressionado)"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                    </svg>
                </button>

                {/* Botão + (deixar mais claro) */}
                <button
                    type="button"
                    onMouseDown={() => !disabled && intensity > MIN_INTENSITY && startIntensityChange(-INTENSITY_STEP)}
                    onMouseUp={stopIntensityChange}
                    onMouseLeave={stopIntensityChange}
                    onTouchStart={() => !disabled && intensity > MIN_INTENSITY && startIntensityChange(-INTENSITY_STEP)}
                    onTouchEnd={stopIntensityChange}
                    disabled={disabled || intensity <= MIN_INTENSITY}
                    className="aspect-square w-12 h-12 rounded-md border-2 border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center select-none"
                    title="Deixar mais claro (mantenha pressionado)"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                </button>
            </div>
        </div>
    )
}
