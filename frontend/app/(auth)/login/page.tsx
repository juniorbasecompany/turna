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
        // Verificar Client ID
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
        if (!clientId) {
            setError('Google Client ID não configurado. Configure NEXT_PUBLIC_GOOGLE_CLIENT_ID no arquivo .env.local')
            return
        }

        // Função para inicializar o botão quando o script estiver pronto
        const initGoogleButton = () => {
            if (!window.google?.accounts?.id) {
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

            // Inicializa a API do Google
            window.google.accounts.id.initialize({
                client_id: clientId,
                callback: handleGoogleSignIn,
            })

            // Renderiza o botão imediatamente
            window.google.accounts.id.renderButton(buttonElement, {
                theme: 'outline',
                size: 'large',
            })

            initializedRef.current = true
            setGoogleClientId(clientId)
            return true
        }

        // Se o script já estiver carregado, inicializa imediatamente
        if (initGoogleButton()) {
            return
        }

        // Caso contrário, aguarda o script carregar
        // O script é carregado via next/script no layout, mas pode não estar pronto ainda
        const checkInterval = setInterval(() => {
            if (initGoogleButton()) {
                clearInterval(checkInterval)
            }
        }, 50) // Verifica a cada 50ms (mais rápido que o setTimeout anterior)

        // Timeout de segurança (5 segundos)
        const timeout = setTimeout(() => {
            clearInterval(checkInterval)
            if (!window.google?.accounts?.id) {
                setError('Erro ao carregar Google Identity Services')
            }
        }, 5000)

        return () => {
            clearInterval(checkInterval)
            clearTimeout(timeout)
        }
    }, [handleGoogleSignIn])

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
                            <p className="text-sm text-red-800">{error}</p>
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
