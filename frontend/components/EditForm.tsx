import { ReactNode } from 'react'

interface EditFormProps {
    title: string
    editTitle?: string
    createTitle?: string
    isEditing: boolean
    children: ReactNode
    /** Remove o padding externo (usar quando o componente pai já tem padding) */
    noPadding?: boolean
    className?: string
}

/**
 * Componente wrapper para formulários de edição.
 * 
 * Encapsula a estrutura padrão de edição:
 * - Container branco com borda âmbar à esquerda (indica edição/atenção)
 * - Título dinâmico (Editar/Criar)
 * - Espaçamento consistente
 * 
 * @param noPadding - Use quando o EditForm está dentro de um container que já tem padding
 */
export function EditForm({ title, editTitle, createTitle, isEditing, children, noPadding = false, className = '' }: EditFormProps) {
    if (!isEditing) return null

    const displayTitle = isEditing ? (editTitle || `Editar ${title}`) : (createTitle || `Criar ${title}`)

    const content = (
        <div className="mb-4 sm:mb-6 bg-white rounded-lg border border-gray-200 border-l-4 border-l-amber-500 p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{displayTitle}</h2>
            {children}
        </div>
    )

    if (noPadding) {
        return content
    }

    return (
        <div className={`p-4 sm:p-6 lg:p-8 min-w-0 ${className}`}>
            {content}
        </div>
    )
}
