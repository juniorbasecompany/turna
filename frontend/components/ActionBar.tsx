'use client'

import { ReactNode } from 'react'
import { LoadingSpinner } from './LoadingSpinner'

interface ActionBarButton {
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
     * Tipo do botão (primary = azul, secondary = cinza, danger = vermelho)
     */
    variant?: 'primary' | 'secondary' | 'danger'
    /**
     * Se true, mostra estado de loading no botão
     */
    loading?: boolean
}

interface ActionBarProps {
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
     * Mensagem de erro simples. Use esta prop em vez de leftContent quando quiser exibir apenas um erro.
     */
    error?: string | null
    /**
     * Botões de ação (array de botões)
     */
    buttons?: ActionBarButton[]
    /**
     * Componente de paginação a ser exibido junto com os botões à direita
     */
    pagination?: ReactNode
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
 * IMPORTANTE: Use também <ActionBarSpacer /> ou adicione padding-bottom
 * no conteúdo da página para evitar que o conteúdo fique escondido atrás da barra.
 *
 * @example
 * ```tsx
 * // Barra sempre visível, botões aparecem quando há seleção
 * <ActionBar
 *   buttons={selectedItems.length > 0 ? [{ label: "Salvar", onClick: handleSave }] : []}
 * />
 * <ActionBarSpacer />
 * ```
 */
export function ActionBar({
    message,
    messageType = 'info',
    leftContent,
    error,
    buttons = [],
    pagination,
    show,
}: ActionBarProps) {
    // Se show for explicitamente false, não renderizar
    // Caso contrário, sempre renderizar (mesmo sem botões/mensagem)
    if (show === false) {
        return null
    }

    // Cores de texto baseadas no tipo (sem bordas, sem fundo, apenas cor do texto)
    const textColorClasses = {
        info: 'text-gray-700',
        success: 'text-green-600',
        warning: 'text-yellow-600',
        error: 'text-red-600',
    }

    const buttonClasses = {
        primary: 'bg-blue-600 border-blue-700 text-white hover:bg-blue-700',
        secondary: 'bg-gray-200 border-gray-300 text-gray-800 hover:bg-gray-300',
        danger: 'bg-red-200 border-red-300 text-gray-800 hover:bg-red-300',
    }

    // Renderizar botões
    const renderButtons = () => {
        if (!buttons || buttons.length === 0) return null
        return buttons.map((button, index) => (
            <button
                key={index}
                onClick={button.onClick}
                disabled={button.disabled || button.loading}
                className={`px-3 sm:px-4 py-2 text-sm font-medium border rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap flex items-center justify-center gap-2 ${buttonClasses[button.variant || 'primary']}`}
            >
                {button.loading ? <LoadingSpinner /> : button.label}
            </button>
        ))
    }

    // Determinar qual conteúdo exibir e qual cor usar
    // Prioridade: message > error > leftContent
    let content: ReactNode = null
    let textColor = 'text-gray-700' // padrão

    if (message) {
        content = typeof message === 'string' ? message : message
        textColor = textColorClasses[messageType]
    } else if (error) {
        content = error
        textColor = textColorClasses.error
    } else if (leftContent) {
        content = leftContent
        // leftContent não tem cor padrão definida, usa a cor do container (text-gray-700)
        // Se o leftContent já tiver cor definida internamente (ex: span com className), ela será aplicada
        textColor = ''
    }

    return (
        <div className="fixed bottom-0 left-0 lg:left-64 right-0 z-30 bg-white border-t border-gray-200 shadow-lg min-h-20 pb-[env(safe-area-inset-bottom,0px)]">
            <div className="min-h-20 flex flex-wrap items-center gap-2 sm:gap-4 px-4 sm:px-6 lg:px-8 py-2">
                {/* Conteúdo à esquerda - sem bordas, apenas texto - sempre reserva espaço */}
                <div className={`flex-1 min-w-[200px] text-sm ${textColor}`}>
                    {content ? (
                        typeof content === 'string' ? (
                            <p className="break-words">{content}</p>
                        ) : (
                            content
                        )
                    ) : null}
                </div>
                {/* Botões de ação e paginação - alinhados à direita, podem quebrar para linha de baixo */}
                <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    {pagination}
                    {renderButtons()}
                </div>
            </div>
        </div>
    )
}

/**
 * Spacer para reservar espaço quando ActionBar está visível.
 *
 * Use este componente no final do conteúdo da página para evitar
 * que o conteúdo fique escondido atrás da barra inferior.
 * Já considera a safe-area do iOS.
 *
 * @example
 * ```tsx
 * <div>
 *   {/* Conteúdo da página *\/}
 *   <ActionBarSpacer />
 * </div>
 * ```
 */
export function ActionBarSpacer() {
    // Altura mínima da barra (80px) + safe-area (env(safe-area-inset-bottom))
    return <div className="min-h-20 pb-[env(safe-area-inset-bottom,0px)]" />
}

