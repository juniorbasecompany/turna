'use client'

import { ReactNode } from 'react'

interface BottomActionBarButton {
    /**
     * Texto do botão
     */
    label: string
    /**
     * Função chamada ao clicar
     */
    onClick: () => void
    /**
     * Se true, desabilita o botão
     */
    disabled?: boolean
    /**
     * Tipo do botão (primary = azul, secondary = cinza)
     */
    variant?: 'primary' | 'secondary'
    /**
     * Se true, mostra estado de loading no botão
     */
    loading?: boolean
}

interface BottomActionBarProps {
    /**
     * Mensagem a ser exibida na barra (opcional)
     */
    message?: string | ReactNode
    /**
     * Tipo de mensagem (afeta a cor)
     */
    messageType?: 'info' | 'success' | 'warning' | 'error'
    /**
     * Conteúdo simples à esquerda, sem bordas ou estilos de mensagem
     */
    leftContent?: ReactNode
    /**
     * Botões de ação (array de botões)
     */
    buttons?: BottomActionBarButton[]
    /**
     * Se false, esconde a barra. Por padrão, a barra sempre aparece
     * (mesmo sem botões ou mensagem). Os botões aparecem/desaparecem
     * conforme o array de buttons.
     */
    show?: boolean
}

/**
 * Barra inferior fixa para exibir mensagens e ações ao usuário.
 *
 * A barra sempre aparece por padrão (mesmo sem botões ou mensagem).
 * Os botões aparecem/desaparecem conforme o array de buttons.
 * Use show={false} para esconder completamente a barra.
 *
 * IMPORTANTE: Use também <BottomActionBarSpacer /> ou adicione padding-bottom
 * no conteúdo da página para evitar que o conteúdo fique escondido atrás da barra.
 *
 * @example
 * ```tsx
 * // Barra sempre visível, botões aparecem quando há seleção
 * <BottomActionBar
 *   buttons={selectedItems.length > 0 ? [{ label: "Salvar", onClick: handleSave }] : []}
 * />
 * <BottomActionBarSpacer />
 * ```
 */
export function BottomActionBar({
    message,
    messageType = 'info',
    leftContent,
    buttons = [],
    show,
}: BottomActionBarProps) {
    // Se show for explicitamente false, não renderizar
    // Caso contrário, sempre renderizar (mesmo sem botões/mensagem)
    if (show === false) {
        return null
    }

    const messageColorClasses = {
        info: 'text-gray-700 bg-blue-50 border-blue-200',
        success: 'text-green-800 bg-green-50 border-green-200',
        warning: 'text-yellow-800 bg-yellow-50 border-yellow-200',
        error: 'text-red-800 bg-red-50 border-red-200',
    }

    const buttonClasses = {
        primary: 'bg-blue-600 border-blue-700 text-white hover:bg-blue-700',
        secondary: 'bg-gray-200 border-gray-300 text-gray-800 hover:bg-gray-300',
    }

    // Renderizar botões
    const renderButtons = () => {
        if (!buttons || buttons.length === 0) return null
        return (
            <>
                {buttons.map((button, index) => (
                    <button
                        key={index}
                        onClick={button.onClick}
                        disabled={button.disabled || button.loading}
                        className={`px-3 sm:px-4 py-2 text-sm font-medium border rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ${
                            buttonClasses[button.variant || 'primary']
                        }`}
                    >
                        {button.loading ? 'Processando...' : button.label}
                    </button>
                ))}
            </>
        )
    }

    return (
        <div className="fixed bottom-0 left-0 lg:left-64 right-0 z-30 bg-white border-t border-gray-200 shadow-lg min-h-20 pb-[env(safe-area-inset-bottom,0px)]">
            {message ? (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-20 flex items-center">
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-4 w-full">
                        {/* Mensagem */}
                        <div
                            className={`flex-1 px-4 py-2 rounded-md border ${messageColorClasses[messageType]} min-w-0`}
                        >
                            {typeof message === 'string' ? (
                                <p className="text-sm font-medium truncate">{message}</p>
                            ) : (
                                message
                            )}
                        </div>

                        {/* Botões de ação - alinhados à direita */}
                        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                            {renderButtons()}
                        </div>
                    </div>
                </div>
            ) : leftContent ? (
                <div className="min-h-20 flex items-center justify-between px-4 sm:px-6 lg:px-8">
                    {/* Conteúdo à esquerda - sem bordas */}
                    <div className="flex-1 min-w-0">
                        {leftContent}
                    </div>
                    {/* Botões de ação - alinhados à direita */}
                    <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                        {renderButtons()}
                    </div>
                </div>
            ) : buttons.length > 0 ? (
                <div className="min-h-20 flex items-center justify-end px-4 sm:px-6 lg:px-8">
                    {/* Botões de ação - alinhados à direita da tela */}
                    <div className="flex items-center gap-2 sm:gap-3">
                        {renderButtons()}
                    </div>
                </div>
            ) : (
                <div className="min-h-20 flex items-center justify-end px-4 sm:px-6 lg:px-8">
                    {/* Botões de ação - alinhados à direita da tela */}
                    <div className="flex items-center gap-2 sm:gap-3">
                        {renderButtons()}
                    </div>
                </div>
            )}
        </div>
    )
}

/**
 * Spacer para reservar espaço quando BottomActionBar está visível.
 *
 * Use este componente no final do conteúdo da página para evitar
 * que o conteúdo fique escondido atrás da barra inferior.
 * Já considera a safe-area do iOS.
 *
 * @example
 * ```tsx
 * <div>
 *   {/* Conteúdo da página *\/}
 *   <BottomActionBarSpacer />
 * </div>
 * ```
 */
export function BottomActionBarSpacer() {
    // Altura mínima da barra (80px) + safe-area (env(safe-area-inset-bottom))
    return <div className="min-h-20 pb-[env(safe-area-inset-bottom,0px)]" />
}
