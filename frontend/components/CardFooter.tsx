'use client'

import { TenantSettings } from '@/contexts/TenantSettingsContext'
import { getCardSecondaryTextClasses } from '@/lib/cardStyles'
import { formatDateTime } from '@/lib/tenantFormat'
import { CardActionButtons } from './CardActionButtons'

interface CardFooterProps {
    /** Se o card está selecionado */
    isSelected: boolean
    /** Data para exibir (ISO string) */
    date: string
    /** Configurações do tenant para formatação de data */
    settings: TenantSettings | null
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
}

/**
 * Componente reutilizável para o rodapé de cards selecionáveis.
 *
 * Padroniza o rodapé usado em Hospital, Demand, etc:
 * - Data formatada à esquerda
 * - Botões de ação (excluir/editar) à direita
 *
 * @example
 * ```tsx
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
            </div>
            <CardActionButtons
                isSelected={isSelected}
                onToggleSelection={onToggleSelection}
                onEdit={onEdit}
                disabled={disabled}
                deleteTitle={deleteTitle}
                editTitle={editTitle}
            />
        </div>
    )
}
