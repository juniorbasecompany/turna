'use client'

import { ReactNode } from 'react'
import { TenantFormatSettings } from '@/lib/tenantFormat'
import { getCardSecondaryTextClasses, getCardTertiaryTextClasses } from '@/lib/cardStyles'
import { formatDateTime } from '@/lib/tenantFormat'
import { useCardSelection } from '@/components/EntityCard'
import { CardActionButtons } from './CardActionButtons'

interface CardFooterProps {
    /** Data para exibir (ISO string) */
    date: string
    /** Configurações do tenant para formatação de data */
    settings: TenantFormatSettings | null
    /** Callback quando o botão de editar é clicado */
    onEdit: () => void
    /** Se os botões estão desabilitados */
    disabled?: boolean
    /** Título do checkbox de exclusão */
    deleteTitle?: string
    /** Título do botão de editar */
    editTitle?: string
    /** Se deve mostrar o botão de editar (padrão: true) */
    showEdit?: boolean
    /** Se deve mostrar o checkbox de exclusão (padrão: true) */
    showDelete?: boolean
    /** Texto secundário opcional (ex: tamanho do arquivo) */
    secondaryText?: string
    /** Elemento React opcional para renderizar antes dos botões de ação (ex: checkbox) */
    beforeActions?: ReactNode
}

/**
 * Componente reutilizável para o rodapé de cards selecionáveis.
 *
 * Padroniza o rodapé usado em Hospital, Demand, File, etc:
 * - Checkbox de seleção à esquerda
 * - Data ao centro/esquerda (com texto secundário opcional)
 * - Ações à direita: botão de editar (com elemento opcional antes)
 * - isSelected e onToggle vêm obrigatoriamente do CardSelectionContext (EntityCard com selection)
 *
 * @example
 * ```tsx
 * <CardFooter date={item.created_at} settings={settings} onEdit={() => handleEdit(item)} />
 * ```
 */
export function CardFooter({
    date,
    settings,
    onEdit,
    disabled = false,
    deleteTitle,
    editTitle,
    showEdit = true,
    showDelete = true,
    secondaryText,
    beforeActions,
}: CardFooterProps) {
    const selectionContext = useCardSelection()
    if (!selectionContext) {
        throw new Error('CardFooter must be used within EntityCard')
    }

    const isSelected = selectionContext.isSelected
    const onToggleSelection = (e: React.MouseEvent | React.ChangeEvent<HTMLInputElement>) => {
        e.stopPropagation()
        selectionContext.onToggle()
    }

    return (
        <div className="flex items-center justify-between gap-2">
            <div className="shrink-0">
                <CardActionButtons
                    isSelected={isSelected}
                    onToggleSelection={onToggleSelection}
                    onEdit={onEdit}
                    disabled={disabled}
                    deleteTitle={deleteTitle}
                    editTitle={editTitle}
                    showEdit={false}
                    showDelete={showDelete}
                />
            </div>
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
                    onToggleSelection={undefined}
                    onEdit={onEdit}
                    disabled={disabled}
                    deleteTitle={deleteTitle}
                    editTitle={editTitle}
                    showEdit={showEdit}
                    showDelete={false}
                />
            </div>
        </div>
    )
}
