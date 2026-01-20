import { ReactNode } from 'react'
import { ActionBar } from './ActionBar'
import { LoadingSpinner } from './LoadingSpinner'

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
     * Mensagem de erro a ser exibida no ActionBar
     */
    error?: string | null
    /**
     * Conteúdo de filtros a ser exibido na área superior compartilhada
     * Não aparece se editContent estiver presente
     */
    filterContent?: ReactNode
    /**
     * Conteúdo do formulário de edição/criação a ser exibido na área superior compartilhada
     * Tem prioridade sobre filterContent (se presente, filterContent não aparece)
     */
    editContent?: ReactNode
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
    filterContent,
    editContent,
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

                {/* Área superior compartilhada: filtros ou formulário de edição */}
                {(editContent || filterContent) && (
                    <div className="mb-4 sm:mb-6">
                        {editContent || filterContent}
                    </div>
                )}

                {loading ? (
                    <div className="text-center py-12">
                        <LoadingSpinner />
                    </div>
                ) : totalCount === 0 && createCard ? (
                    // Quando não há itens mas há card de criação, mostrar apenas o card
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {createCard}
                    </div>
                ) : totalCount === 0 ? (
                    // Quando não há itens e não há card de criação, mostrar mensagem vazia
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

            {/* ActionBar para exibir erros quando não há botões de ação */}
            {error && (
                <ActionBar
                    message={error}
                    messageType="error"
                    show={!!error}
                />
            )}
        </>
    )
}
