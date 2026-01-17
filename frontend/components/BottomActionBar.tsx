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
     * Botões de ação (array de botões)
     */
    buttons?: BottomActionBarButton[]
    /**
     * Se true, mostra a barra. Se false, a barra não é renderizada.
     * Se não especificado, a barra aparece quando há mensagem ou botões.
     */
    show?: boolean
}

/**
 * Barra inferior fixa para exibir mensagens e ações ao usuário.
 *
 * Usada para manter ações importantes (como botão Salvar) e mensagens
 * sempre visíveis enquanto o usuário rola a página.
 *
 * IMPORTANTE: Use também <BottomActionBarSpacer /> ou adicione padding-bottom
 * no conteúdo da página para evitar que o conteúdo fique escondido atrás da barra.
 *
 * @example
 * ```tsx
 * <BottomActionBar
 *   message="3 itens marcados para exclusão"
 *   messageType="info"
 *   buttons={[
 *     {
 *       label: "Salvar",
 *       onClick: handleSave,
 *       variant: "primary",
 *       loading: saving
 *     }
 *   ]}
 * />
 * <BottomActionBarSpacer />
 * ```
 */
export function BottomActionBar({
    message,
    messageType = 'info',
    buttons = [],
    show,
}: BottomActionBarProps) {
    // Determinar se deve mostrar: se show não especificado, mostrar quando há conteúdo
    const hasContent = message || (buttons && buttons.length > 0)
    const shouldShow = show !== undefined ? show : hasContent

    // Se show for true, sempre renderizar (mesmo sem conteúdo). Caso contrário, só renderizar se houver conteúdo
    if (!shouldShow || (show === undefined && !hasContent)) {
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
            <div className="flex items-center gap-3">
                {buttons.map((button, index) => (
                    <button
                        key={index}
                        onClick={button.onClick}
                        disabled={button.disabled || button.loading}
                        className={`px-4 py-2 text-sm font-medium border rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                            buttonClasses[button.variant || 'primary']
                        }`}
                    >
                        {button.loading ? 'Processando...' : button.label}
                    </button>
                ))}
            </div>
        )
    }

    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg h-20">
            {message ? (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center">
                    <div className="flex items-center justify-between gap-4 w-full">
                        {/* Mensagem */}
                        <div
                            className={`flex-1 px-4 py-2 rounded-md border ${messageColorClasses[messageType]}`}
                        >
                            {typeof message === 'string' ? (
                                <p className="text-sm font-medium">{message}</p>
                            ) : (
                                message
                            )}
                        </div>

                        {/* Botões de ação - alinhados à direita */}
                        {renderButtons()}
                    </div>
                </div>
            ) : (
                <div className="h-full flex items-center justify-end px-4 sm:px-6 lg:px-8">
                    {/* Botões de ação - alinhados à direita da tela */}
                    {renderButtons()}
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
    // Altura da barra: py-4 (16px top + 16px bottom) + conteúdo (~40px) = ~72px
    return <div className="h-20" />
}
