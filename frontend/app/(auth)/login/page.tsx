'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { AuthResponse } from '@/types/api'

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
        // Verificar Client ID antes de carregar script
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
        if (!clientId) {
            setError('Google Client ID não configurado. Configure NEXT_PUBLIC_GOOGLE_CLIENT_ID no arquivo .env.local')
            return
        }

        // Carregar Google Identity Services
        const script = document.createElement('script')
        script.src = 'https://accounts.google.com/gsi/client'
        script.async = true
        script.defer = true

        script.onload = () => {
            if (!window.google) {
                setError('Erro ao carregar Google Identity Services')
                return
            }

            setGoogleClientId(clientId)

            window.google.accounts.id.initialize({
                client_id: clientId,
                callback: handleGoogleSignIn,
            })

            // Aguardar um pouco para garantir que o DOM está pronto
            setTimeout(() => {
                const buttonElement = document.getElementById('google-signin-button')
                if (buttonElement && window.google) {
                    window.google.accounts.id.renderButton(buttonElement, {
                        theme: 'outline',
                        size: 'large',
                        width: '100%',
                    })
                }
            }, 100)
        }

        script.onerror = () => {
            setError('Erro ao carregar script do Google Identity Services')
        }

        document.head.appendChild(script)

        return () => {
            if (document.head.contains(script)) {
                document.head.removeChild(script)
            }
        }
    }, [handleGoogleSignIn])

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8 p-8">
                <div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        Entrar no Turna
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
                            {googleClientId ? (
                                <div
                                    id="google-signin-button"
                                    className="flex justify-center"
                                />
                            ) : (
                                <div className="text-center py-4">
                                    <p className="text-sm text-gray-500">
                                        Carregando botão de login...
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
