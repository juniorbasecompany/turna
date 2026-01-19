'use client'

import { ReactNode, useEffect, useRef, useState } from 'react'

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
     *
     * Para forçar animação quando o erro muda (mesmo texto), você pode:
     * - Passar uma string com separador `|` e versão: `"mensagem|1"`, `"mensagem|2"`, etc.
     * - Ou usar a prop `error` que gerencia versão automaticamente
     * - Ou usar a prop `errorKey` para indicar mudanças
     */
    leftContent?: ReactNode
    /**
     * Mensagem de erro simples. Se fornecida, será exibida no leftContent e a versão
     * será gerenciada automaticamente para disparar animação mesmo quando a mensagem
     * é a mesma. Use esta prop em vez de leftContent quando quiser apenas exibir erro.
     */
    error?: string | null
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
    /**
     * Chave opcional para forçar atualização da animação de erro.
     * Mude este valor sempre que um novo erro ocorrer, mesmo que a mensagem seja a mesma.
     * Alternativamente, use o formato "mensagem|versão" no leftContent ou a prop `error`.
     */
    errorKey?: string | number
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
    error,
    buttons = [],
    show,
    errorKey,
}: BottomActionBarProps) {
    // Se show for explicitamente false, não renderizar
    // Caso contrário, sempre renderizar (mesmo sem botões/mensagem)
    if (show === false) {
        return null
    }

    // Estado para controlar a animação de piscar quando erro aparece
    const [shouldPulse, setShouldPulse] = useState(false)
    
    // Se a prop `error` foi fornecida, usar ela no leftContent automaticamente
    // e gerenciar versão internamente
    const [internalErrorVersion, setInternalErrorVersion] = useState(0)
    const errorVersionRef = useRef(0)
    
    // Se error mudou (mesmo que seja o mesmo texto), incrementar versão interna
    useEffect(() => {
        if (error !== null && error !== undefined) {
            errorVersionRef.current += 1
            setInternalErrorVersion(errorVersionRef.current)
        } else {
            // Quando erro é limpo, resetar versão
            errorVersionRef.current = 0
            setInternalErrorVersion(0)
        }
    }, [error])
    
    // Se error foi fornecido, usar ele no leftContent com versão automática
    const effectiveLeftContent = error !== null && error !== undefined 
        ? `${error}|${internalErrorVersion}`
        : leftContent
    
    const hasError = !!effectiveLeftContent || (message && messageType === 'error')

    // Extrair conteúdo do erro (remover versão se presente no formato "mensagem|versão")
    const errorContent = typeof effectiveLeftContent === 'string'
        ? effectiveLeftContent.split('|')[0]
        : message && typeof message === 'string'
            ? message
            : ''

    // Usar ref para rastrear o estado anterior e detectar mudanças
    const prevErrorStateRef = useRef<{ content: string; key?: string | number; hasError: boolean }>({
        content: '',
        hasError: false,
    })

    // Detectar quando um erro aparece ou muda e ativar animação
    useEffect(() => {
        // Determinar a chave única do erro (prioridade: errorKey > versão no leftContent > conteúdo)
        let currentErrorKey: string | number | undefined = errorKey

        // Se leftContent é string e tem formato "mensagem|versão", usar a versão
        if (!currentErrorKey && typeof effectiveLeftContent === 'string' && effectiveLeftContent.includes('|')) {
            const parts = effectiveLeftContent.split('|')
            if (parts.length > 1) {
                const versionPart = parts[1].trim()
                // Tentar converter para número, senão usar como string
                currentErrorKey = isNaN(Number(versionPart)) ? versionPart : Number(versionPart)
            }
        }

        // Se não há errorKey e o conteúdo é o mesmo, usar o conteúdo como chave
        if (!currentErrorKey && errorContent) {
            currentErrorKey = errorContent
        }

        const prevState = prevErrorStateRef.current

        // Se não há erro, limpar estado anterior
        if (!hasError) {
            if (prevState.hasError || prevState.content !== '' || prevState.key !== undefined) {
                prevErrorStateRef.current = {
                    content: '',
                    key: undefined,
                    hasError: false,
                }
            }
            setShouldPulse(false)
            return
        }

        // Se há erro, verificar se mudou
        if (hasError && errorContent) {
            const errorChanged =
                !prevState.hasError || // Erro apareceu (não havia erro antes)
                prevState.content !== errorContent || // Conteúdo mudou
                prevState.key !== currentErrorKey // Chave mudou (mesmo conteúdo, mas nova ocorrência)

            if (errorChanged) {
                // Atualizar estado anterior
                prevErrorStateRef.current = {
                    content: errorContent,
                    key: currentErrorKey,
                    hasError: true,
                }

                setShouldPulse(true)
                // Remover a classe após a animação completar
                const timer = setTimeout(() => {
                    setShouldPulse(false)
                }, 1200) // Animação dura 1.2 segundos
                return () => clearTimeout(timer)
            }
        }
    }, [errorContent, hasError, errorKey, effectiveLeftContent, internalErrorVersion]) // Incluir effectiveLeftContent e internalErrorVersion nas dependências

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
                        className={`px-3 sm:px-4 py-2 text-sm font-medium border rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ${buttonClasses[button.variant || 'primary']
                            }`}
                    >
                        {button.loading ? 'Processando...' : button.label}
                    </button>
                ))}
            </>
        )
    }

    return (
        <>
            <style>{`
                @keyframes errorPulse {
                    0%, 100% {
                        background-color: rgb(255, 255, 255);
                    }
                    50% {
                        background-color: rgba(252, 165, 165, 1);
                    }
                }
                .error-pulse {
                    animation: errorPulse 1.2s ease-in-out;
                }
            `}</style>
            <div
                className={`fixed bottom-0 left-0 lg:left-64 right-0 z-30 bg-white border-t border-gray-200 shadow-lg min-h-20 pb-[env(safe-area-inset-bottom,0px)] ${shouldPulse && hasError ? 'error-pulse' : ''
                    }`}
            >
                {message ? (
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-20 flex items-center py-2">
                        <div className="flex flex-wrap items-center gap-2 sm:gap-4 w-full">
                            {/* Mensagem */}
                            <div
                                className={`flex-1 min-w-[200px] px-4 py-2 rounded-md border ${messageColorClasses[messageType]}`}
                            >
                                {typeof message === 'string' ? (
                                    <p className="text-sm font-medium break-words">{message}</p>
                                ) : (
                                    message
                                )}
                            </div>

                            {/* Botões de ação - alinhados à direita, podem quebrar para linha de baixo */}
                            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                                {renderButtons()}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="min-h-20 flex flex-wrap items-center gap-2 sm:gap-4 px-4 sm:px-6 lg:px-8 py-2">
                        {/* Conteúdo à esquerda - sem bordas, apenas texto - sempre reserva espaço */}
                        <div className="flex-1 min-w-[200px] text-sm text-red-600">
                            {effectiveLeftContent && (
                                typeof effectiveLeftContent === 'string' ? (
                                    <p className="break-words">{effectiveLeftContent.split('|')[0]}</p>
                                ) : (
                                    effectiveLeftContent
                                )
                            )}
                        </div>
                        {/* Botões de ação - alinhados à direita, podem quebrar para linha de baixo */}
                        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                            {renderButtons()}
                        </div>
                    </div>
                )}
            </div>
        </>
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
