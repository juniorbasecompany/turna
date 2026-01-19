'use client'

interface CardActionButtonsProps {
    isSelected: boolean
    onToggleSelection: (e: React.MouseEvent) => void
    onEdit: () => void
    disabled?: boolean
    deleteTitle?: string
    editTitle?: string
}

/**
 * Componente reutilizável para botões de ação em cards (excluir e editar).
 *
 * Usado em cards de Hospital, Profile, Demand, etc.
 *
 * @example
 * ```tsx
 * <CardActionButtons
 *   isSelected={selectedItems.has(item.id)}
 *   onToggleSelection={(e) => {
 *     e.stopPropagation()
 *     toggleSelection(item.id)
 *   }}
 *   onEdit={() => handleEdit(item)}
 *   disabled={deleting}
 * />
 * ```
 */
export function CardActionButtons({
    isSelected,
    onToggleSelection,
    onEdit,
    disabled = false,
    deleteTitle,
    editTitle,
}: CardActionButtonsProps) {
    return (
        <div className="flex items-center gap-1 shrink-0">
            {/* Ícone para exclusão */}
            <button
                onClick={onToggleSelection}
                disabled={disabled}
                className={`shrink-0 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${isSelected
                        ? 'text-red-700 bg-red-100 opacity-100'
                        : 'text-gray-400'
                    }`}
                title={deleteTitle || (isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão')}
            >
                <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                </svg>
            </button>
            <button
                onClick={onEdit}
                className="shrink-0 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer text-blue-600"
                title={editTitle || 'Editar'}
            >
                <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                </svg>
            </button>
        </div>
    )
}
