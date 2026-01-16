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
                    renderButton: (
                        element: HTMLElement,
                        config: { theme?: string; size?: string; text?: string; shape?: string }
                    ) => void
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
    const initializedLoginRef = useRef(false)

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
                // Se a conta não foi encontrada (404), tentar cadastro automático
                if (res.status === 404) {
                    // Automaticamente chamar registro com os mesmos dados do Google
                    const registerRes = await fetch('/api/auth/google/register', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            id_token: response.credential,
                        }),
                    })

                    const registerResult: AuthResponse = await registerRes.json()

                    if (!registerRes.ok) {
                        // Se o registro também falhar, mostrar erro
                        setError(registerResult.detail || 'Erro ao cadastrar')
                        return
                    }

                    // Registro bem-sucedido - tratar resposta como login normal
                    // (continuar com o código abaixo que trata requires_tenant_selection)
                    const finalResult = registerResult

                    // Tratamento de resposta do registro (mesmo comportamento do login)
                    if (finalResult.requires_tenant_selection) {
                        sessionStorage.setItem('login_id_token', response.credential)
                        sessionStorage.setItem('login_response', JSON.stringify(finalResult))
                        router.push('/select-tenant')
                    } else if (finalResult.access_token) {
                        router.push('/')
                    } else {
                        setError('Resposta inesperada do servidor')
                    }
                    return
                }

                // Outros erros
                if (res.status === 403) {
                    setError('Usuário sem acesso a nenhum tenant')
                } else {
                    setError(result.detail || 'Erro ao fazer login')
                }
                return
            }

            // Tratamento de resposta
            // Verificar requires_tenant_selection PRIMEIRO antes de access_token
            // Isso garante que quando há múltiplos tenants, vamos para seleção
            if (result.requires_tenant_selection) {
                // Exige seleção de tenant → salvar dados e redirect para seleção
                // Salvar id_token e resposta do login no sessionStorage para permitir refresh
                sessionStorage.setItem('login_id_token', response.credential)
                sessionStorage.setItem('login_response', JSON.stringify(result))
                router.push('/select-tenant')
            } else if (result.access_token) {
                // Token direto → redirect para dashboard
                router.push('/')
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

            const loginButtonElement = document.getElementById('google-signin-button')
            if (!loginButtonElement) {
                return false
            }

            // Verifica se já foi inicializado
            if (initializedLoginRef.current) {
                return true
            }

            try {
                // Inicializar o Google Identity Services
                google.accounts.id.initialize({
                    client_id: clientId,
                    callback: handleGoogleSignIn,
                })

                // Renderizar botão de Login com texto do Google (não hardcoded)
                google.accounts.id.renderButton(loginButtonElement, {
                    theme: 'outline',
                    size: 'large',
                    text: 'signin_with',
                    shape: 'rectangular',
                })

                initializedLoginRef.current = true

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
        initializedLoginRef.current = false

        // Limpa qualquer conteúdo do botão que possa ter sido renderizado pelo Google
        const loginButtonElement = document.getElementById('google-signin-button')
        if (loginButtonElement) {
            while (loginButtonElement.firstChild) {
                loginButtonElement.removeChild(loginButtonElement.firstChild)
            }
        }

        // Aguarda um frame para garantir que o DOM foi atualizado
        requestAnimationFrame(() => {
            const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
            if (google?.accounts?.id && clientId && loginButtonElement) {
                try {
                    // Reinicializar o botão
                    google.accounts.id.initialize({
                        client_id: clientId,
                        callback: handleGoogleSignIn,
                    })
                    google.accounts.id.renderButton(loginButtonElement, {
                        theme: 'outline',
                        size: 'large',
                        text: 'signin_with',
                        shape: 'rectangular',
                    })
                    initializedLoginRef.current = true
                    setGoogleClientId(clientId)
                    return // Sucesso, não precisa rodar o useEffect novamente
                } catch (err) {
                    // Se falhar, continua para tentar novamente via useEffect
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
                                className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium"
                            >
                                Tentar novamente
                            </button>
                        </div>
                    )}

                    {loading ? (
                        <div className="flex justify-center items-center py-4">
                            <span className="text-gray-600">Autenticando...</span>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {/* Elemento onde o Google renderiza o botão de login - sempre presente no DOM */}
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
