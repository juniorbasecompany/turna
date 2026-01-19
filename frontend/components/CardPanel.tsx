import { ReactNode } from 'react'
import { BottomActionBar } from './BottomActionBar'

interface CardPanelProps {
    title: string
    description: string
    totalCount: number
    selectedCount?: number
    loading?: boolean
    loadingMessage?: string
    emptyMessage?: string
    countLabel?: string
    createCard?: ReactNode
    children: ReactNode
    className?: string
    /**
     * Mensagem de erro a ser exibida no BottomActionBar
     */
    error?: string | null
}

export function CardPanel({
    title,
    description,
    totalCount,
    selectedCount = 0,
    loading = false,
    loadingMessage = 'Carregando...',
    emptyMessage = 'Nenhum item cadastrado ainda.',
    countLabel = 'Total',
    createCard,
    children,
    className = '',
    error,
}: CardPanelProps) {
    return (
        <>
            <div className={`p-4 sm:p-6 lg:p-8 min-w-0 ${className}`}>
                {/* Cabeçalho com título e descrição */}
                <div className="mb-4 sm:mb-6">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">{title}</h1>
                        <p className="mt-1 text-sm text-gray-600">{description}</p>
                    </div>
                </div>

                {loading ? (
                    <div className="text-center py-12">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                        <p className="mt-2 text-sm text-gray-600">{loadingMessage}</p>
                    </div>
                ) : totalCount === 0 ? (
                    <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                        <p className="text-gray-600">{emptyMessage}</p>
                    </div>
                ) : (
                    <>
                        {/* Mensagem de total e contadores */}
                        <div className="mb-4 sm:mb-6">
                            <div className="text-sm text-gray-600">
                                {countLabel}: <span className="font-medium">{totalCount}</span>
                                {selectedCount > 0 && (
                                    <span className="ml-2 sm:ml-4 text-red-600">
                                        {selectedCount} marcado{selectedCount > 1 ? 's' : ''} para exclusão
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Grid de cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {createCard}
                            {children}
                        </div>
                    </>
                )}
            </div>

            {/* BottomActionBar para exibir erros quando não há botões de ação */}
            {error && (
                <BottomActionBar
                    message={error}
                    messageType="error"
                    show={!!error}
                />
            )}
        </>
    )
}
