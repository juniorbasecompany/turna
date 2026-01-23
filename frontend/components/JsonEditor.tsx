'use client'

import JsonView from '@uiw/react-json-view'
import { useEffect, useRef, useState } from 'react'

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
        // Criar uma cópia profunda do objeto
        const result = JSON.parse(JSON.stringify(obj)) as Record<string, unknown>

        // Se o path estiver vazio, retornar o objeto sem alterações
        if (path.length === 0) {
            return result
        }

        // Se o path tiver apenas um elemento, atualizar diretamente na raiz
        if (path.length === 1) {
            const key = String(path[0])
            result[key] = newValue
            return result
        }

        let current: Record<string, unknown> = result

        // Navegar até o objeto pai do valor final
        for (let i = 0; i < path.length - 1; i++) {
            const key = String(path[i])
            if (typeof current[key] === 'object' && current[key] !== null && !Array.isArray(current[key])) {
                current = current[key] as Record<string, unknown>
            } else {
                // Se o caminho não existir, criar o objeto necessário
                current[key] = {}
                current = current[key] as Record<string, unknown>
            }
        }

        // Atualizar o valor final
        const finalKey = String(path[path.length - 1])
        current[finalKey] = newValue
        return result
    }

    return (
        <div className="space-y-2">
            {/* Editor JSON */}
            <div
                id={id}
                className={`border rounded-md overflow-auto ${is_disabled ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'border-gray-300 bg-white'}`}
                style={{ height: heightStyle, width: '100%' }}
            >
                <JsonView
                    value={jsonViewValue}
                    displayDataTypes={false}
                    displayObjectSize={true}
                    enableClipboard={false}
                    collapsed={false}
                    indentWidth={50}
                    style={{
                        backgroundColor: 'transparent',
                        fontSize: '16px',
                        lineHeight: '2.5',
                        width: '100%',
                        minWidth: 'fit-content',
                    }}
                >
                    {/* Remover aspas dos valores */}
                    <JsonView.ValueQuote render={() => <></>} />
                    <JsonView.Quote render={() => <></>} />

                    {/* Remover apenas chaves e colchetes, mantendo nomes das chaves */}
                    <JsonView.BraceLeft render={() => <></>} />
                    <JsonView.BraceRight render={() => <></>} />
                    <JsonView.BracketsLeft render={() => <></>} />
                    <JsonView.BracketsRight render={() => <></>} />

                    {/* Remover dois pontos */}
                    <JsonView.Colon render={() => <></>} />

                    {/* Nomes das chaves normais (sem negrito) com caixa colorida */}
                    <JsonView.KeyName
                        render={(props) => (
                            <span
                                {...props}
                                style={{
                                    display: 'inline-block',
                                    marginBottom: '12px',
                                    whiteSpace: 'nowrap'
                                }}
                                className="border border-gray-300 rounded px-2 py-0.5 bg-blue-50"
                            >
                                {props.children}
                            </span>
                        )}
                    />

                    {/* Componente customizado para editar valores string */}
                    <JsonView.String
                        render={(props, { value, keys }) => {
                            const pathKey = JSON.stringify(keys || [])
                            const isEditing = editingPath === pathKey && !is_disabled
                            // Verificar se está vazio - incluindo string vazia
                            const isEmpty = value === '' || (typeof value === 'string' && value.trim().length === 0)

                            if (isEditing) {
                                return (
                                    <input
                                        type="text"
                                        value={editingValue}
                                        onChange={(e) => setEditingValue(e.target.value)}
                                        onBlur={() => {
                                            setEditingPath(null)
                                            if (jsonViewValue && typeof jsonViewValue === 'object' && keys && keys.length > 0) {
                                                const updated = updateValueInObject(
                                                    jsonViewValue as Record<string, unknown>,
                                                    keys,
                                                    editingValue || ''
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
                                        style={{ minWidth: '200px', width: 'auto' }}
                                    />
                                )
                            }

                            if (isEmpty) {
                                return (
                                    <span
                                        {...props}
                                        onClick={() => {
                                            if (!is_disabled) {
                                                setEditingPath(pathKey)
                                                setEditingValue('')
                                            }
                                        }}
                                        style={{
                                            cursor: is_disabled ? 'default' : 'pointer',
                                            minWidth: '200px',
                                            display: 'inline-block',
                                            textAlign: 'left',
                                            marginBottom: '12px',
                                            whiteSpace: 'nowrap'
                                        }}
                                        className={is_disabled ? 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400' : 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400 hover:bg-blue-50'}
                                        title={is_disabled ? undefined : 'Clique para adicionar conteúdo'}
                                    >
                                        Clique para editar
                                    </span>
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
                                    style={{
                                        cursor: is_disabled ? 'default' : 'pointer',
                                        minWidth: '200px',
                                        display: 'inline-block',
                                        textAlign: 'left',
                                        marginBottom: '12px',
                                        whiteSpace: 'nowrap'
                                    }}
                                    className={is_disabled ? 'border border-gray-300 rounded px-2 py-0.5' : 'border border-gray-300 rounded px-2 py-0.5 hover:bg-blue-50'}
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
                            const isEmpty = value === null || value === undefined || value === ''

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
                                        style={{ minWidth: '200px', width: 'auto' }}
                                    />
                                )
                            }

                            if (isEmpty) {
                                return (
                                    <span
                                        {...props}
                                        onClick={() => {
                                            if (!is_disabled) {
                                                setEditingPath(pathKey)
                                                setEditingValue('')
                                            }
                                        }}
                                        style={{
                                            cursor: is_disabled ? 'default' : 'pointer',
                                            minWidth: '200px',
                                            display: 'inline-block',
                                            textAlign: 'left',
                                            marginBottom: '12px',
                                            whiteSpace: 'nowrap'
                                        }}
                                        className={is_disabled ? 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400' : 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400 hover:bg-blue-50'}
                                        title={is_disabled ? undefined : 'Clique para adicionar conteúdo'}
                                    >
                                        Clique para editar
                                    </span>
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
                                    style={{
                                        cursor: is_disabled ? 'default' : 'pointer',
                                        minWidth: '200px',
                                        display: 'inline-block',
                                        textAlign: 'left',
                                        marginBottom: '12px',
                                        whiteSpace: 'nowrap'
                                    }}
                                    className={is_disabled ? 'border border-gray-300 rounded px-2 py-0.5' : 'border border-gray-300 rounded px-2 py-0.5 hover:bg-blue-50'}
                                    title={is_disabled ? undefined : 'Clique para editar'}
                                >
                                    {props.children}
                                </span>
                            )
                        }}
                    />

                    {/* Componente customizado para valores null */}
                    <JsonView.Null
                        render={(props, { keys }) => {
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
                                            if (jsonViewValue && typeof jsonViewValue === 'object' && keys && keys.length > 0) {
                                                const updated = updateValueInObject(
                                                    jsonViewValue as Record<string, unknown>,
                                                    keys,
                                                    editingValue || ''
                                                )
                                                handleChange(updated)
                                            }
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.currentTarget.blur()
                                            } else if (e.key === 'Escape') {
                                                setEditingPath(null)
                                                setEditingValue('')
                                            }
                                        }}
                                        autoFocus
                                        className="px-1 border border-blue-500 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        style={{ minWidth: '200px', width: 'auto' }}
                                    />
                                )
                            }

                            return (
                                <span
                                    {...props}
                                    onClick={() => {
                                        if (!is_disabled) {
                                            setEditingPath(pathKey)
                                            setEditingValue('')
                                        }
                                    }}
                                    style={{
                                        cursor: is_disabled ? 'default' : 'pointer',
                                        minWidth: '200px',
                                        display: 'inline-block',
                                        textAlign: 'left',
                                        marginBottom: '12px',
                                        whiteSpace: 'nowrap'
                                    }}
                                    className={is_disabled ? 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400' : 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400 hover:bg-blue-50'}
                                    title={is_disabled ? undefined : 'Clique para adicionar conteúdo'}
                                >
                                    Clique para editar
                                </span>
                            )
                        }}
                    />

                    {/* Componente customizado para valores undefined */}
                    <JsonView.Undefined
                        render={(props, { keys }) => {
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
                                            if (jsonViewValue && typeof jsonViewValue === 'object' && keys && keys.length > 0) {
                                                const updated = updateValueInObject(
                                                    jsonViewValue as Record<string, unknown>,
                                                    keys,
                                                    editingValue || ''
                                                )
                                                handleChange(updated)
                                            }
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.currentTarget.blur()
                                            } else if (e.key === 'Escape') {
                                                setEditingPath(null)
                                                setEditingValue('')
                                            }
                                        }}
                                        autoFocus
                                        className="px-1 border border-blue-500 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        style={{ minWidth: '200px', width: 'auto' }}
                                    />
                                )
                            }

                            return (
                                <span
                                    {...props}
                                    onClick={() => {
                                        if (!is_disabled) {
                                            setEditingPath(pathKey)
                                            setEditingValue('')
                                        }
                                    }}
                                    style={{
                                        cursor: is_disabled ? 'default' : 'pointer',
                                        minWidth: '200px',
                                        display: 'inline-block',
                                        textAlign: 'left',
                                        marginBottom: '12px',
                                        whiteSpace: 'nowrap'
                                    }}
                                    className={is_disabled ? 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400' : 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400 hover:bg-blue-50'}
                                    title={is_disabled ? undefined : 'Clique para adicionar conteúdo'}
                                >
                                    Clique para editar
                                </span>
                            )
                        }}
                    />

                    {/* Componente customizado para editar valores float */}
                    <JsonView.Float
                        render={(props, { value, keys }) => {
                            const pathKey = JSON.stringify(keys || [])
                            const isEditing = editingPath === pathKey && !is_disabled
                            const isEmpty = value === null || value === undefined || value === ''

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
                                        style={{ minWidth: '200px', width: 'auto' }}
                                    />
                                )
                            }

                            if (isEmpty) {
                                return (
                                    <span
                                        {...props}
                                        onClick={() => {
                                            if (!is_disabled) {
                                                setEditingPath(pathKey)
                                                setEditingValue('')
                                            }
                                        }}
                                        style={{
                                            cursor: is_disabled ? 'default' : 'pointer',
                                            minWidth: '200px',
                                            display: 'inline-block',
                                            textAlign: 'left',
                                            marginBottom: '12px',
                                            whiteSpace: 'nowrap'
                                        }}
                                        className={is_disabled ? 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400' : 'border border-dashed border-gray-400 rounded px-2 py-0.5 text-gray-400 hover:bg-blue-50'}
                                        title={is_disabled ? undefined : 'Clique para adicionar conteúdo'}
                                    >
                                        Clique para editar
                                    </span>
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
                                    style={{
                                        cursor: is_disabled ? 'default' : 'pointer',
                                        minWidth: '200px',
                                        display: 'inline-block',
                                        textAlign: 'left',
                                        marginBottom: '12px',
                                        whiteSpace: 'nowrap'
                                    }}
                                    className={is_disabled ? 'border border-gray-300 rounded px-2 py-0.5' : 'border border-gray-300 rounded px-2 py-0.5 hover:bg-blue-50'}
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
