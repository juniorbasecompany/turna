'use client'

import { ReactNode } from 'react'
import { TenantFormatSettings } from '@/lib/tenantFormat'
import { getCardSecondaryTextClasses, getCardTertiaryTextClasses } from '@/lib/cardStyles'
import { formatDateTime } from '@/lib/tenantFormat'
import { CardActionButtons } from './CardActionButtons'

interface CardFooterProps {
    /** Se o card está selecionado */
    isSelected: boolean
    /** Data para exibir (ISO string) */
    date: string
    /** Configurações do tenant para formatação de data */
    settings: TenantFormatSettings | null
    /** Callback quando o botão de exclusão é clicado */
    onToggleSelection: (e: React.MouseEvent) => void
    /** Callback quando o botão de editar é clicado */
    onEdit: () => void
    /** Se os botões estão desabilitados */
    disabled?: boolean
    /** Título do botão de exclusão */
    deleteTitle?: string
    /** Título do botão de editar */
    editTitle?: string
    /** Se deve mostrar o botão de editar (padrão: true) */
    showEdit?: boolean
    /** Texto secundário opcional (ex: tamanho do arquivo) */
    secondaryText?: string
    /** Elemento React opcional para renderizar antes dos botões de ação (ex: checkbox) */
    beforeActions?: ReactNode
}

/**
 * Componente reutilizável para o rodapé de cards selecionáveis.
 *
 * Padroniza o rodapé usado em Hospital, Demand, File, etc:
 * - Data formatada à esquerda (com texto secundário opcional)
 * - Botões de ação (excluir/editar) à direita (com elemento opcional antes)
 *
 * @example
 * ```tsx
 * // Uso básico (Hospital, Demand)
 * <CardFooter
 *   isSelected={selectedItems.has(item.id)}
 *   date={item.created_at}
 *   settings={settings}
 *   onToggleSelection={(e) => {
 *     e.stopPropagation()
 *     toggleSelection(item.id)
 *   }}
 *   onEdit={() => handleEdit(item)}
 *   disabled={deleting}
 * />
 *
 * // Uso com texto secundário e elemento antes dos botões (File)
 * <CardFooter
 *   isSelected={isSelected}
 *   date={file.created_at}
 *   settings={settings}
 *   secondaryText={formatFileSize(file.file_size)}
 *   beforeActions={<Checkbox ... />}
 *   onToggleSelection={...}
 *   onEdit={...}
 * />
 * ```
 */
export function CardFooter({
    isSelected,
    date,
    settings,
    onToggleSelection,
    onEdit,
    disabled = false,
    deleteTitle,
    editTitle,
    showEdit = true,
    secondaryText,
    beforeActions,
}: CardFooterProps) {
    return (
        <div className="flex items-center justify-between gap-2">
            <div className="flex flex-col min-w-0 flex-1">
                <span className={`text-sm truncate ${getCardSecondaryTextClasses(isSelected)}`}>
                    {settings
                        ? formatDateTime(date, settings)
                        : new Date(date).toLocaleDateString('pt-BR', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                        })}
                </span>
                {secondaryText && (
                    <span className={`text-xs truncate ${getCardTertiaryTextClasses(isSelected)}`}>
                        {secondaryText}
                    </span>
                )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
                {beforeActions}
                <CardActionButtons
                    isSelected={isSelected}
                    onToggleSelection={onToggleSelection}
                    onEdit={onEdit}
                    disabled={disabled}
                    deleteTitle={deleteTitle}
                    editTitle={editTitle}
                    showEdit={showEdit}
                />
            </div>
        </div>
    )
}
