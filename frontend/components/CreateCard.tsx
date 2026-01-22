'use client'

import { getCardContainerClasses } from '@/lib/cardStyles'
import { ReactNode } from 'react'

interface CreateCardProps {
    /** Texto principal do card (ex: "Criar novo profissional") */
    label: string
    /** Texto secundário opcional (ex: "Clique para adicionar") */
    subtitle?: string
    /** Callback quando o card é clicado */
    onClick: () => void
    /** Se o card está desabilitado */
    disabled?: boolean
    /** Conteúdo customizado para substituir o conteúdo padrão */
    children?: ReactNode
    /** Ícone customizado (ReactNode) para substituir o ícone padrão */
    customIcon?: ReactNode
    /** Se está em estado de drag (para upload de arquivos) */
    isDragging?: boolean
    /** Se deve mostrar flash/erro (para upload de arquivos quando hospital não selecionado) */
    showFlash?: boolean
    /** Mensagem de flash/erro a ser exibida */
    flashMessage?: string
    /** Handlers de drag and drop (opcional) */
    onDragEnter?: (e: React.DragEvent) => void
    onDragOver?: (e: React.DragEvent) => void
    onDragLeave?: (e: React.DragEvent) => void
    onDrop?: (e: React.DragEvent) => void
    /** Classes CSS customizadas para o container interno */
    innerContainerClassName?: string
}

/**
 * Componente reutilizável para card de criação de novos itens.
 *
 * Usado em páginas CRUD (Hospitais, Clínicas, Associados, etc.) para permitir
 * criar novos itens. O card aparece no grid junto com os itens existentes.
 *
 * Suporta funcionalidades avançadas como drag & drop para upload de arquivos.
 *
 * @example
 * ```tsx
 * // Uso básico
 * <CreateCard
 *   label="Criar novo profissional"
 *   subtitle="Clique para adicionar"
 *   onClick={handleCreateClick}
 * />
 *
 * // Uso com drag & drop (arquivos)
 * <CreateCard
 *   label="Adicionar arquivos"
 *   isDragging={isDragging}
 *   showFlash={uploadCardFlash}
 *   flashMessage="Selecione o hospital"
 *   onDragEnter={handleDragEnter}
 *   onDragOver={handleDragOver}
 *   onDragLeave={handleDragLeave}
 *   onDrop={handleDrop}
 *   onClick={handleUploadCardClick}
 *   customIcon={<UploadIcon />}
 * >
 *   <p className="text-xs text-slate-400">PDF, XLSX, JPG, PNG, CSV</p>
 * </CreateCard>
 * ```
 */
export function CreateCard({
    label,
    subtitle,
    onClick,
    disabled = false,
    children,
    customIcon,
    isDragging = false,
    showFlash = false,
    flashMessage,
    onDragEnter,
    onDragOver,
    onDragLeave,
    onDrop,
    innerContainerClassName,
}: CreateCardProps) {
    // Determinar classes CSS baseadas no estado
    const getBorderClasses = () => {
        if (isDragging) return 'border-blue-500 bg-blue-50'
        if (showFlash) return 'border-red-500 bg-red-50'
        return 'border-slate-300'
    }

    const getIconColor = () => {
        if (isDragging) return 'text-blue-600'
        if (showFlash) return 'text-red-600'
        return 'text-slate-400'
    }

    const getLabelColor = () => {
        if (isDragging) return 'text-blue-600'
        if (showFlash) return 'text-red-700'
        return 'text-slate-500'
    }

    // Ícone padrão (plus-circle) se não houver customIcon
    const defaultIcon = (
        <svg
            className="w-full h-full"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
            />
        </svg>
    )

    return (
        <div
            onClick={disabled ? undefined : onClick}
            onDragEnter={onDragEnter}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            className={`${getCardContainerClasses(false)} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} ${onDragEnter ? 'overflow-hidden' : ''}`}
        >
            <div className="mb-3">
                <div className={`h-40 sm:h-48 rounded-lg flex flex-col border-2 border-dashed ${getBorderClasses()} ${innerContainerClassName || ''}`}>
                    {/* Conteúdo principal */}
                    <div className="flex-1 flex flex-col items-center justify-center text-center px-2 py-4 min-h-0">
                        <div className={`w-12 h-12 sm:w-16 sm:h-16 mb-2 shrink-0 ${getIconColor()}`}>
                            {customIcon || defaultIcon}
                        </div>
                        <p className={`text-sm font-medium text-center px-2 mb-1 ${getLabelColor()}`}>
                            {isDragging ? 'Solte os arquivos aqui' : showFlash && flashMessage ? flashMessage : label}
                        </p>
                        {children && !isDragging && (
                            <div className="w-full mt-auto">
                                {children}
                            </div>
                        )}
                    </div>
                </div>
            </div>
            {subtitle && !isDragging && (
                <div className="flex items-center justify-center py-2">
                    <span className="text-xs text-slate-400">{subtitle}</span>
                </div>
            )}
        </div>
    )
}
