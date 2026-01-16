'use client'

import { AuthResponse } from '@/types/api'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'

declare global {
    interface Window {
        google?: {
            accounts: {
                id: {
                    initialize: (config: {
                        client_id: string
                        callback: (response: { credential: string }) => void
                    }) => void
                    renderButton: (element: HTMLElement, config: { theme?: string; size?: string }) => void
                    prompt: () => void
                }
            }
        }
    }
}

export default function LoginPage() {
    const router = useRouter()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [googleClientId, setGoogleClientId] = useState<string | null>(null)
    const [retryKey, setRetryKey] = useState(0)
    const [isRetry, setIsRetry] = useState(false)
    const initializedRef = useRef(false)

    const handleGoogleSignIn = useCallback(async (response: { credential: string }) => {
        setLoading(true)
        setError(null)

        try {
            // Enviar id_token para handler do Next.js (rota da própria aplicação)
            const res = await fetch('/api/auth/google/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    id_token: response.credential,
                }),
            })

            const result: AuthResponse = await res.json()

            if (!res.ok) {
                // Erro do servidor
                if (res.status === 403) {
                    setError('Usuário sem acesso a nenhum tenant')
                } else if (res.status === 404) {
                    setError('Conta não encontrada. Use a opção "Cadastrar-se" para criar uma conta.')
                } else {
                    setError(result.detail || 'Erro ao fazer login')
                }
                return
            }

            // Tratamento de resposta
            if (result.access_token) {
                // Token direto → redirect para dashboard
                router.push('/')
            } else if (result.requires_tenant_selection) {
                // Exige seleção de tenant → redirect para seleção
                router.push('/select-tenant')
            } else {
                setError('Resposta inesperada do servidor')
            }
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message || 'Erro ao fazer login')
            } else {
                setError('Erro desconhecido ao fazer login')
            }
        } finally {
            setLoading(false)
        }
    }, [router])

    useEffect(() => {
        // Verifica se há scripts do Google carregando na página
        let scripts = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"]')

        // Se não há script no DOM, injeta manualmente (fallback)
        if (scripts.length === 0) {
            const script = document.createElement('script')
            script.src = 'https://accounts.google.com/gsi/client'
            script.async = true
            script.defer = true
            script.setAttribute('data-manual-inject', 'true')
            document.head.appendChild(script)
        }

        // Verificar Client ID
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
        if (!clientId) {
            setError('Google Client ID não configurado. Configure NEXT_PUBLIC_GOOGLE_CLIENT_ID no arquivo .env.local')
            return
        }

        // Função para inicializar o botão quando o script estiver pronto
        const initGoogleButton = () => {
            const google = window.google
            if (!google?.accounts?.id) {
                return false
            }

            const buttonElement = document.getElementById('google-signin-button')
            if (!buttonElement) {
                return false
            }

            // Verifica se já foi inicializado para evitar múltiplas inicializações
            if (initializedRef.current) {
                return true
            }

            try {
                // Inicializa a API do Google
                google.accounts.id.initialize({
                    client_id: clientId,
                    callback: handleGoogleSignIn,
                })

                // Renderiza o botão imediatamente
                google.accounts.id.renderButton(buttonElement, {
                    theme: 'outline',
                    size: 'large',
                })

                initializedRef.current = true
                setGoogleClientId(clientId)
                return true
            } catch (error) {
                return false
            }
        }

        // Timeout de segurança: 5s na primeira tentativa, 20s após retry
        const timeoutDuration = isRetry ? 20000 : 5000

        let timeoutId: NodeJS.Timeout
        let checkInterval: NodeJS.Timeout

        const stopChecking = () => {
            if (checkInterval) {
                clearInterval(checkInterval)
            }
            if (timeoutId) {
                clearTimeout(timeoutId)
            }
        }

        // Verifica imediatamente (caso o script já esteja carregado)
        if (initGoogleButton()) {
            return
        }

        // Listener para detectar quando o script carrega via evento
        const scriptElements = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"]')
        scriptElements.forEach((script) => {
            if (!script.hasAttribute('data-loaded')) {
                script.addEventListener('load', () => {
                    script.setAttribute('data-loaded', 'true')
                    // Aguarda um pouco para o script executar
                    setTimeout(() => {
                        if (initGoogleButton()) {
                            stopChecking()
                        }
                    }, 100)
                })
            }
        })

        // Define interval para verificar continuamente (verifica a cada 50ms)
        checkInterval = setInterval(() => {
            if (initGoogleButton()) {
                stopChecking()
            }
        }, 50)

        // Define timeout para parar se não carregar a tempo
        timeoutId = setTimeout(() => {
            stopChecking()
            const google = window.google
            if (!google?.accounts?.id) {
                setError('Não foi possível entrar no sistema agora. Verifique sua conexão e tente novamente.')
            }
        }, timeoutDuration)

        return () => {
            clearInterval(checkInterval)
            clearTimeout(timeoutId)
        }
    }, [handleGoogleSignIn, retryKey, isRetry])

    const handleRetry = () => {
        const google = window.google
        setError(null)
        setGoogleClientId(null)
        initializedRef.current = false

        // Limpa qualquer conteúdo do botão que possa ter sido renderizado pelo Google
        const buttonElement = document.getElementById('google-signin-button')
        if (buttonElement) {
            while (buttonElement.firstChild) {
                buttonElement.removeChild(buttonElement.firstChild)
            }
        }

        // Aguarda um frame para garantir que o DOM foi atualizado
        requestAnimationFrame(() => {
            // Se o script já está carregado, tenta inicializar imediatamente
            if (google?.accounts?.id && buttonElement) {
                const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
                if (clientId) {
                    try {
                        google.accounts.id.initialize({
                            client_id: clientId,
                            callback: handleGoogleSignIn,
                        })
                        google.accounts.id.renderButton(buttonElement, {
                            theme: 'outline',
                            size: 'large',
                        })
                        initializedRef.current = true
                        setGoogleClientId(clientId)
                        return // Sucesso, não precisa rodar o useEffect novamente
                    } catch (err) {
                        // Se falhar, continua para tentar novamente via useEffect
                    }
                }
            }

            // Se chegou aqui, o script não está pronto ou a inicialização falhou
            // Força nova tentativa via useEffect com timeout maior
            setIsRetry(true)
            setRetryKey(prev => prev + 1)
        })
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8 p-8">
                <div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        Turna
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        Sistema de gestão de escalas
                    </p>
                </div>

                <div className="mt-8">
                    {error && (
                        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                            <p className="text-sm text-red-800 mb-3">{error}</p>
                            <button
                                onClick={handleRetry}
                                className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm font-medium"
                            >
                                Tentar novamente
                            </button>
                        </div>
                    )}

                    {loading ? (
                        <div className="flex justify-center items-center py-4">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                            <span className="ml-3 text-gray-600">Autenticando...</span>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {/* Elemento onde o Google renderiza o botão real - sempre presente no DOM */}
                            <div
                                id="google-signin-button"
                                className="flex justify-center min-h-[48px]"
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
