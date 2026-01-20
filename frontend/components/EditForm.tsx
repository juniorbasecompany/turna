import { ReactNode } from 'react'

interface EditFormProps {
    title: string
    editTitle?: string
    createTitle?: string
    isEditing: boolean
    children: ReactNode
    className?: string
}

export function EditForm({ title, editTitle, createTitle, isEditing, children, className = '' }: EditFormProps) {
    if (!isEditing) return null

    const displayTitle = isEditing ? (editTitle || `Editar ${title}`) : (createTitle || `Criar ${title}`)

    return (
        <div className={`p-4 sm:p-6 lg:p-8 min-w-0 ${className}`}>
            <div className="mb-4 sm:mb-6 bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">{displayTitle}</h2>
                {children}
            </div>
        </div>
    )
}
