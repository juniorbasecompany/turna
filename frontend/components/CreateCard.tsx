'use client'

import { getCardContainerClasses } from '@/lib/cardStyles'

interface CreateCardProps {
    /** Texto principal do card (ex: "Criar novo profissional") */
    label: string
    /** Texto secundário opcional (ex: "Clique para adicionar") */
    subtitle?: string
    /** Callback quando o card é clicado */
    onClick: () => void
    /** Se o card está desabilitado */
    disabled?: boolean
}

/**
 * Componente reutilizável para card de criação de novos itens.
 *
 * Usado em páginas CRUD (Profissionais, Hospitais, Perfis, etc.) para permitir
 * criar novos itens. O card aparece no grid junto com os itens existentes.
 *
 * @example
 * ```tsx
 * <CreateCard
 *   label="Criar novo profissional"
 *   subtitle="Clique para adicionar"
 *   onClick={handleCreateClick}
 * />
 * ```
 */
export function CreateCard({ label, subtitle, onClick, disabled = false }: CreateCardProps) {
    return (
        <div
            onClick={disabled ? undefined : onClick}
            className={`${getCardContainerClasses(false)} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
            <div className="mb-3">
                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-slate-50 border-2 border-dashed border-slate-300">
                    <div className="flex flex-col items-center justify-center text-slate-400">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
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
                        </div>
                        <p className="text-sm font-medium text-center px-2 text-slate-500">
                            {label}
                        </p>
                    </div>
                </div>
            </div>
            {subtitle && (
                <div className="flex items-center justify-center py-2">
                    <span className="text-xs text-slate-400">{subtitle}</span>
                </div>
            )}
        </div>
    )
}
