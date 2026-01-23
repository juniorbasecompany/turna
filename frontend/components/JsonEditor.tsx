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

    // Função auxiliar para atualizar um valor específico no objeto/array
    // Suporta tanto objetos quanto arrays, tratando corretamente índices numéricos
    const updateValueInObject = (obj: unknown, path: (string | number)[], newValue: unknown): unknown => {
        // Criar uma cópia profunda do objeto/array
        const result = JSON.parse(JSON.stringify(obj))

        // Se o path estiver vazio, retornar sem alterações
        if (path.length === 0) {
            return result
        }

        // Função auxiliar para acessar um valor no objeto/array atual
        const getValue = (container: unknown, key: string | number): unknown => {
            if (typeof key === 'number') {
                if (Array.isArray(container)) {
                    return container[key]
                }
                return undefined
            } else {
                if (typeof container === 'object' && container !== null && !Array.isArray(container)) {
                    return (container as Record<string, unknown>)[key]
                }
                return undefined
            }
        }

        // Função auxiliar para definir um valor no objeto/array atual
        const setValue = (container: unknown, key: string | number, value: unknown): void => {
            if (typeof key === 'number') {
                if (Array.isArray(container)) {
                    container[key] = value
                }
            } else {
                if (typeof container === 'object' && container !== null && !Array.isArray(container)) {
                    ;(container as Record<string, unknown>)[key] = value
                }
            }
        }

        // Navegar até o objeto/array pai do valor final
        let current: unknown = result

        for (let i = 0; i < path.length - 1; i++) {
            const key = path[i]
            const nextKey = path[i + 1]

            // Determinar se o próximo elemento é índice de array ou chave de objeto
            const nextIsArrayIndex = typeof nextKey === 'number'

            // Obter o elemento atual
            let currentElement = getValue(current, key)

            // Se o elemento não existir ou tiver tipo errado, criar a estrutura correta
            if (currentElement === undefined || currentElement === null) {
                currentElement = nextIsArrayIndex ? [] : {}
                setValue(current, key, currentElement)
            } else if (nextIsArrayIndex && !Array.isArray(currentElement)) {
                // Próximo é índice de array mas elemento atual não é array, converter
                currentElement = []
                setValue(current, key, currentElement)
            } else if (!nextIsArrayIndex && (typeof currentElement !== 'object' || currentElement === null || Array.isArray(currentElement))) {
                // Próximo é chave de objeto mas elemento atual não é objeto, converter
                currentElement = {}
                setValue(current, key, currentElement)
            }

            // Avançar para o próximo nível
            current = currentElement
        }

        // Atualizar o valor final
        const finalKey = path[path.length - 1]
        
        // Garantir que o container final tenha o tipo correto
        if (typeof finalKey === 'number') {
            // Acessar array por índice
            if (!Array.isArray(current)) {
                // Se não for array, criar array
                current = []
                // Atualizar no pai anterior
                if (path.length > 1) {
                    const parentKey = path[path.length - 2]
                    // Navegar de volta até o pai
                    let parent: unknown = result
                    for (let i = 0; i < path.length - 2; i++) {
                        parent = getValue(parent, path[i])
                    }
                    setValue(parent, parentKey, current)
                } else {
                    // É a raiz
                    ;(current as unknown[])[finalKey] = newValue
                    return current
                }
            }
            ;(current as unknown[])[finalKey] = newValue
        } else {
            // Acessar objeto por chave string
            if (typeof current !== 'object' || current === null || Array.isArray(current)) {
                // Se não for objeto, criar objeto
                current = {}
                // Atualizar no pai anterior
                if (path.length > 1) {
                    const parentKey = path[path.length - 2]
                    // Navegar de volta até o pai
                    let parent: unknown = result
                    for (let i = 0; i < path.length - 2; i++) {
                        parent = getValue(parent, path[i])
                    }
                    setValue(parent, parentKey, current)
                } else {
                    // É a raiz
                    ;(current as Record<string, unknown>)[finalKey] = newValue
                    return current
                }
            }
            ;(current as Record<string, unknown>)[finalKey] = newValue
        }

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
                                                    jsonViewValue,
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
                                                    jsonViewValue,
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
                                                    jsonViewValue,
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
                                                    jsonViewValue,
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
                                                    jsonViewValue,
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
