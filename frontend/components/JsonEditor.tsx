'use client'

import { useEffect, useRef, useState } from 'react'
import JsonView from '@uiw/react-json-view'

interface JsonEditorProps {
    /** Valor atual (objeto JSON) */
    value: unknown
    /** Callback quando o valor muda */
    on_change: (value: unknown) => void
    /** Se o editor está desabilitado */
    is_disabled?: boolean
    /** Altura do editor (número em px ou string CSS) */
    height?: number | string
    /** ID do campo para acessibilidade */
    id?: string
}

/**
 * Componente de edição de JSON em formato árvore.
 * Permite edição inline com expansão/colapso de nós.
 */
export function JsonEditor({
    value,
    on_change,
    is_disabled = false,
    height = 400,
    id,
}: JsonEditorProps) {
    const [internalValue, setInternalValue] = useState<unknown>(value)
    const initialValueRef = useRef<unknown>(value)
    // Estado para rastrear qual valor está sendo editado (usando path como chave)
    const [editingPath, setEditingPath] = useState<string | null>(null)
    const [editingValue, setEditingValue] = useState<string>('')

    // Sincronizar com valor externo quando mudar
    useEffect(() => {
        setInternalValue(value)
        initialValueRef.current = value
    }, [value])

    // Converter altura para string CSS
    const heightStyle = typeof height === 'number' ? `${height}px` : height

    // Handler para mudanças no editor
    const handleChange = (newValue: unknown) => {
        setInternalValue(newValue)
        on_change(newValue)
    }

    // Voltar ao valor inicial
    const handleReset = () => {
        const initial = initialValueRef.current
        setInternalValue(initial)
        on_change(initial)
    }

    // Limpar (definir objeto vazio)
    const handleClear = () => {
        const empty: Record<string, unknown> = {}
        setInternalValue(empty)
        on_change(empty)
    }

    // Verificar se há mudanças em relação ao valor inicial
    const hasChanges = JSON.stringify(internalValue) !== JSON.stringify(initialValueRef.current)

    // Converter valor para objeto válido para o JsonView
    // JsonView espera object | undefined, então garantimos que seja um objeto ou undefined
    const jsonViewValue: object | undefined = 
        internalValue === null || internalValue === undefined
            ? undefined
            : typeof internalValue === 'object'
            ? internalValue as object
            : { value: internalValue }

    // Função auxiliar para atualizar um valor específico no objeto
    const updateValueInObject = (obj: Record<string, unknown>, path: (string | number)[], newValue: unknown): Record<string, unknown> => {
        const result = JSON.parse(JSON.stringify(obj)) as Record<string, unknown>
        let current: Record<string, unknown> = result
        
        for (let i = 0; i < path.length - 1; i++) {
            const key = String(path[i])
            if (typeof current[key] === 'object' && current[key] !== null && !Array.isArray(current[key])) {
                current = current[key] as Record<string, unknown>
            } else {
                return result // Caminho inválido
            }
        }
        
        const finalKey = String(path[path.length - 1])
        current[finalKey] = newValue
        return result
    }

    return (
        <div className="space-y-2">
            {/* Botões de ação */}
            <div className="flex gap-2">
                <button
                    type="button"
                    onClick={handleReset}
                    disabled={is_disabled || !hasChanges}
                    className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Voltar
                </button>
                <button
                    type="button"
                    onClick={handleClear}
                    disabled={is_disabled}
                    className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Limpar
                </button>
            </div>

            {/* Editor JSON */}
            <div
                id={id}
                className={`border rounded-md overflow-auto ${is_disabled ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'border-gray-300 bg-white'}`}
                style={{ height: heightStyle }}
            >
                <JsonView
                    value={jsonViewValue}
                    displayDataTypes={true}
                    displayObjectSize={true}
                    enableClipboard={true}
                    collapsed={2}
                    style={{
                        backgroundColor: 'transparent',
                        fontSize: '14px',
                    }}
                >
                    {/* Componente customizado para editar valores string */}
                    <JsonView.String
                        render={(props, { value, keys }) => {
                            const pathKey = JSON.stringify(keys || [])
                            const isEditing = editingPath === pathKey && !is_disabled
                            
                            if (isEditing) {
                                return (
                                    <input
                                        type="text"
                                        value={editingValue}
                                        onChange={(e) => setEditingValue(e.target.value)}
                                        onBlur={() => {
                                            setEditingPath(null)
                                            if (jsonViewValue && typeof jsonViewValue === 'object') {
                                                const updated = updateValueInObject(
                                                    jsonViewValue as Record<string, unknown>,
                                                    keys || [],
                                                    editingValue
                                                )
                                                handleChange(updated)
                                            }
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.currentTarget.blur()
                                            } else if (e.key === 'Escape') {
                                                setEditingPath(null)
                                                setEditingValue(String(value || ''))
                                            }
                                        }}
                                        autoFocus
                                        className="px-1 border border-blue-500 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        style={{ minWidth: '100px' }}
                                    />
                                )
                            }
                            
                            return (
                                <span
                                    {...props}
                                    onClick={() => {
                                        if (!is_disabled) {
                                            setEditingPath(pathKey)
                                            setEditingValue(String(value || ''))
                                        }
                                    }}
                                    style={{ cursor: is_disabled ? 'default' : 'pointer' }}
                                    className={is_disabled ? '' : 'hover:bg-blue-50 px-1 rounded'}
                                    title={is_disabled ? undefined : 'Clique para editar'}
                                >
                                    {props.children}
                                </span>
                            )
                        }}
                    />
                    
                    {/* Componente customizado para editar valores numéricos */}
                    <JsonView.Int
                        render={(props, { value, keys }) => {
                            const pathKey = JSON.stringify(keys || [])
                            const isEditing = editingPath === pathKey && !is_disabled
                            
                            if (isEditing) {
                                return (
                                    <input
                                        type="number"
                                        value={editingValue}
                                        onChange={(e) => setEditingValue(e.target.value)}
                                        onBlur={() => {
                                            setEditingPath(null)
                                            const numValue = Number(editingValue)
                                            if (!isNaN(numValue) && jsonViewValue && typeof jsonViewValue === 'object') {
                                                const updated = updateValueInObject(
                                                    jsonViewValue as Record<string, unknown>,
                                                    keys || [],
                                                    numValue
                                                )
                                                handleChange(updated)
                                            }
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.currentTarget.blur()
                                            } else if (e.key === 'Escape') {
                                                setEditingPath(null)
                                                setEditingValue(String(value || 0))
                                            }
                                        }}
                                        autoFocus
                                        className="px-1 border border-blue-500 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        style={{ minWidth: '80px' }}
                                    />
                                )
                            }
                            
                            return (
                                <span
                                    {...props}
                                    onClick={() => {
                                        if (!is_disabled) {
                                            setEditingPath(pathKey)
                                            setEditingValue(String(value || 0))
                                        }
                                    }}
                                    style={{ cursor: is_disabled ? 'default' : 'pointer' }}
                                    className={is_disabled ? '' : 'hover:bg-blue-50 px-1 rounded'}
                                    title={is_disabled ? undefined : 'Clique para editar'}
                                >
                                    {props.children}
                                </span>
                            )
                        }}
                    />
                    
                    {/* Componente customizado para editar valores float */}
                    <JsonView.Float
                        render={(props, { value, keys }) => {
                            const pathKey = JSON.stringify(keys || [])
                            const isEditing = editingPath === pathKey && !is_disabled
                            
                            if (isEditing) {
                                return (
                                    <input
                                        type="number"
                                        step="any"
                                        value={editingValue}
                                        onChange={(e) => setEditingValue(e.target.value)}
                                        onBlur={() => {
                                            setEditingPath(null)
                                            const numValue = Number(editingValue)
                                            if (!isNaN(numValue) && jsonViewValue && typeof jsonViewValue === 'object') {
                                                const updated = updateValueInObject(
                                                    jsonViewValue as Record<string, unknown>,
                                                    keys || [],
                                                    numValue
                                                )
                                                handleChange(updated)
                                            }
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.currentTarget.blur()
                                            } else if (e.key === 'Escape') {
                                                setEditingPath(null)
                                                setEditingValue(String(value || 0))
                                            }
                                        }}
                                        autoFocus
                                        className="px-1 border border-blue-500 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        style={{ minWidth: '80px' }}
                                    />
                                )
                            }
                            
                            return (
                                <span
                                    {...props}
                                    onClick={() => {
                                        if (!is_disabled) {
                                            setEditingPath(pathKey)
                                            setEditingValue(String(value || 0))
                                        }
                                    }}
                                    style={{ cursor: is_disabled ? 'default' : 'pointer' }}
                                    className={is_disabled ? '' : 'hover:bg-blue-50 px-1 rounded'}
                                    title={is_disabled ? undefined : 'Clique para editar'}
                                >
                                    {props.children}
                                </span>
                            )
                        }}
                    />
                </JsonView>
            </div>

            {/* Indicador de mudanças não salvas */}
            {hasChanges && (
                <p className="text-xs text-yellow-600">
                    Alterações não salvas
                </p>
            )}
        </div>
    )
}
