'use client'

import React from 'react'

interface CardActionButtonsProps {
    isSelected: boolean
    onToggleSelection: (e: React.MouseEvent | React.ChangeEvent<HTMLInputElement>) => void
    onEdit: () => void
    disabled?: boolean
    deleteTitle?: string
    editTitle?: string
    showEdit?: boolean // Se false, oculta o botão de editar
    showDelete?: boolean // Se false, oculta o checkbox de exclusão
}

/**
 * Componente reutilizável para botões de ação em cards (checkbox para exclusão e editar).
 *
 * Usado em cards de Hospital, Demand, etc.
 *
 * Ordem padronizada:
 * 1. Checkbox para exclusão - à esquerda
 * 2. Editar (ícone de lápis) - à direita
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
    showEdit = true, // Por padrão mostra o botão de editar
    showDelete = true, // Por padrão mostra o checkbox de exclusão
}: CardActionButtonsProps) {
    return (
        <div className="flex items-center gap-1 shrink-0">
            {/* 1. Checkbox para exclusão */}
            {showDelete && (
                <label className="flex items-center cursor-pointer shrink-0 px-2 py-1.5">
                    <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                            e.stopPropagation()
                            onToggleSelection(e)
                        }}
                        disabled={disabled}
                        className="w-4 h-4 text-blue-600 border-blue-400 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        title={deleteTitle || (isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão')}
                    />
                </label>
            )}
            {/* 2. Ícone para editar (oculto se showEdit for false) */}
            {showEdit && (
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
            )}
        </div>
    )
}
