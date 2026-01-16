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
    const [retryKey, setRetryKey] = useState(0) // Força re-render do useEffect quando mudar
    const [isRetry, setIsRetry] = useState(false) // Indica se é uma tentativa após retry
    const [logs, setLogs] = useState<string[]>([]) // Logs para exibir na tela
    const initializedRef = useRef(false)
    const firstAttemptRef = useRef(true) // Controla simulação de erro na primeira tentativa

    // Função para adicionar log (também mostra no console)
    const addLog = useCallback((message: string) => {
        const timestamp = new Date().toLocaleTimeString()
        const logMessage = `[${timestamp}] ${message}`
        console.log(logMessage)
        setLogs(prev => [...prev.slice(-19), logMessage]) // Mantém apenas últimas 20 linhas
    }, [])

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
        const startTime = Date.now()
        addLog(`useEffect iniciado (retry: ${isRetry}, timeout: ${isRetry ? 20000 : 5000}ms)`)

        // SIMULAÇÃO DE ERRO: Na primeira tentativa, não carrega o script propositalmente
        if (firstAttemptRef.current && !isRetry) {
            addLog('⚠️ Primeira tentativa: simulando falha (não carregando script)')
            // Remove qualquer script que possa ter sido injetado pelo layout
            const existingScripts = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"]')
            existingScripts.forEach(script => {
                if (script.hasAttribute('data-manual-inject') || script.hasAttribute('data-nextjs-script')) {
                    script.remove()
                }
            })
            addLog('🗑️ Scripts removidos para simular erro')
            // Não carrega o script - força timeout para mostrar botão "Tentar novamente"
        } else {
            // Verifica se há scripts do Google carregando na página
            let scripts = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"]')
            addLog(`Scripts do Google encontrados no DOM: ${scripts.length}`)

            // Se não há script no DOM, injeta manualmente (fallback)
            if (scripts.length === 0) {
                addLog('⚠️ Script do Google não encontrado no DOM, injetando manualmente...')
                const script = document.createElement('script')
                script.src = 'https://accounts.google.com/gsi/client'
                script.async = true
                script.defer = true
                script.setAttribute('data-manual-inject', 'true')
                document.head.appendChild(script)
                addLog('✅ Script injetado manualmente no head')

                // Atualiza a lista de scripts
                scripts = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"]')
                addLog(`Scripts do Google agora: ${scripts.length}`)
            } else {
                scripts.forEach((script, idx) => {
                    addLog(`Script ${idx + 1}: async=${script.hasAttribute('async')}, defer=${script.hasAttribute('defer')}`)
                })
            }
        }

        // Verificar Client ID
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
        if (!clientId) {
            addLog('ERRO: Client ID não configurado')
            setError('Google Client ID não configurado. Configure NEXT_PUBLIC_GOOGLE_CLIENT_ID no arquivo .env.local')
            return
        }
        addLog(`Client ID encontrado: ${clientId.substring(0, 20)}...`)

        // Função para inicializar o botão quando o script estiver pronto
        const initGoogleButton = () => {
            // SIMULAÇÃO DE ERRO: Na primeira tentativa, sempre retorna false
            if (firstAttemptRef.current && !isRetry) {
                return false // Força timeout para testar o botão "Tentar novamente"
            }

            const hasGoogle = !!window.google?.accounts?.id
            const elapsed = Date.now() - startTime
            if (elapsed > 0 && elapsed % 1000 < 50) { // Log apenas quando passa 1 segundo
                addLog(`Verificando script... (${elapsed}ms) - Google: ${hasGoogle ? 'SIM' : 'NÃO'}`)
            }

            if (!hasGoogle) {
                return false
            }

            const buttonElement = document.getElementById('google-signin-button')
            if (!buttonElement) {
                addLog('ERRO: elemento do botão não encontrado')
                return false
            }

            // Verifica se já foi inicializado para evitar múltiplas inicializações
            if (initializedRef.current) {
                return true
            }

            addLog('Inicializando botão Google...')

            // Type guard: sabemos que window.google existe aqui, mas TypeScript precisa de confirmação
            const google = window.google
            if (!google?.accounts?.id) {
                return false
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
                const elapsed = Date.now() - startTime
                addLog(`✅ Botão inicializado! (${elapsed}ms)`)
                return true
            } catch (error) {
                const elapsed = Date.now() - startTime
                addLog(`❌ Erro ao inicializar (${elapsed}ms): ${error instanceof Error ? error.message : String(error)}`)
                return false
            }
        }

        // Aguarda o script carregar (mesmo se já estiver carregado, garante que o DOM está pronto)
        // Timeout de segurança: 5s na primeira tentativa, 20s após retry
        const timeoutDuration = isRetry ? 20000 : 5000

        // Usa let para permitir referência cruzada
        let timeoutId: NodeJS.Timeout
        let checkInterval: NodeJS.Timeout
        let checkCount = 0

        // Função para parar as verificações quando sucesso
        const stopChecking = () => {
            if (checkInterval) {
                clearInterval(checkInterval)
            }
            if (timeoutId) {
                clearTimeout(timeoutId)
            }
        }

        // Verifica imediatamente (caso o script já esteja carregado)
        addLog('Verificando se script já está carregado...')
        if (initGoogleButton()) {
            addLog('✅ Script já estava carregado!')
            return
        }
        addLog('Script ainda não carregado, aguardando...')

        // Listener para detectar quando o script carrega via evento
        const scriptElements = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"]')
        scriptElements.forEach((script) => {
            if (!script.hasAttribute('data-loaded')) {
                script.addEventListener('load', () => {
                    script.setAttribute('data-loaded', 'true')
                    addLog('📥 Evento "load" do script disparado')
                    // Aguarda um pouco para o script executar
                    setTimeout(() => {
                        if (initGoogleButton()) {
                            stopChecking()
                        }
                    }, 100)
                })
                script.addEventListener('error', () => {
                    addLog('❌ Erro ao carregar script do Google')
                })
            }
        })

        // Define interval para verificar continuamente (verifica a cada 50ms)
        checkInterval = setInterval(() => {
            checkCount++
            if (checkCount % 20 === 0) { // Log a cada 1 segundo (20 * 50ms)
                const elapsed = Date.now() - startTime
                const google = window.google
                const hasGoogle = !!google?.accounts?.id
                addLog(`Aguardando... (${elapsed}ms) - Google: ${hasGoogle ? 'SIM' : 'NÃO'}`)

                // Log adicional sobre o estado do script
                const loadedScripts = document.querySelectorAll('script[src*="accounts.google.com/gsi/client"][data-loaded="true"]')
                if (loadedScripts.length > 0 && !hasGoogle) {
                    addLog(`⚠️ Script marcado como carregado mas window.google ainda não existe`)
                }
            }

            if (initGoogleButton()) {
                const elapsed = Date.now() - startTime
                addLog(`✅ Sucesso após ${elapsed}ms!`)
                stopChecking()
            }
        }, 50)

        // Define timeout para parar se não carregar a tempo
        timeoutId = setTimeout(() => {
            const elapsed = Date.now() - startTime
            const google = window.google
            stopChecking()

            // SIMULAÇÃO DE ERRO: Na primeira tentativa, sempre mostra erro mesmo se script estiver carregado
            if (firstAttemptRef.current && !isRetry) {
                addLog(`⏰ Timeout após ${elapsed}ms - Simulando erro (primeira tentativa)`)
                setError('Não foi possível entrar no sistema agora. Verifique sua conexão e tente novamente.')
            } else if (!google?.accounts?.id) {
                addLog(`⏰ Timeout após ${elapsed}ms - Script NÃO carregou`)
                setError('Não foi possível entrar no sistema agora. Verifique sua conexão e tente novamente.')
            } else {
                addLog(`⏰ Timeout mas script está disponível - algo deu errado`)
            }
        }, timeoutDuration)

        return () => {
            clearInterval(checkInterval)
            clearTimeout(timeoutId)
        }
    }, [handleGoogleSignIn, retryKey, isRetry, addLog])

    const handleRetry = () => {
        const retryTime = Date.now()
        addLog('🔄 RETRY iniciado - desabilitando simulação de erro')
        const google = window.google
        addLog(`Estado: Google=${!!google?.accounts?.id ? 'SIM' : 'NÃO'}, Inicializado=${initializedRef.current}`)

        // Desabilita a simulação de erro - agora carrega normalmente
        firstAttemptRef.current = false
        setError(null)
        setGoogleClientId(null) // Limpa o estado do botão
        initializedRef.current = false

        // Limpa qualquer conteúdo do botão que possa ter sido renderizado pelo Google
        const buttonElement = document.getElementById('google-signin-button')
        if (buttonElement) {
            const childrenCount = buttonElement.children.length
            addLog(`Limpando botão (${childrenCount} filhos)`)
            // Remove todos os filhos do elemento
            while (buttonElement.firstChild) {
                buttonElement.removeChild(buttonElement.firstChild)
            }
        }

        // Aguarda um frame para garantir que o DOM foi atualizado
        requestAnimationFrame(() => {
            // Se o script já está carregado, tenta inicializar imediatamente
            if (google?.accounts?.id && buttonElement) {
                addLog('✅ Script já carregado, inicializando agora...')
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
                        addLog('✅ Botão inicializado no retry!')
                        return // Sucesso, não precisa rodar o useEffect novamente
                    } catch (err) {
                        addLog(`❌ Erro ao inicializar: ${err instanceof Error ? err.message : String(err)}`)
                    }
                }
            } else {
                addLog('Script ainda não carregou, forçando useEffect...')
            }

            // Se chegou aqui, o script não está pronto ou a inicialização falhou
            // Força nova tentativa via useEffect com timeout maior
            addLog('Iniciando useEffect com timeout de 20s...')
            setIsRetry(true) // Marca como retry para usar timeout maior
            setRetryKey(prev => prev + 1) // Força re-execução do useEffect
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

                    {/* Logs para debug - aparece na tela */}
                    {logs.length > 0 && (
                        <div className="mb-4 p-3 bg-gray-100 border border-gray-300 rounded-md max-h-48 overflow-y-auto">
                            <div className="text-xs font-semibold text-gray-600 mb-2">Logs de Debug:</div>
                            <div className="text-xs font-mono text-gray-700 space-y-0.5">
                                {logs.map((log, index) => (
                                    <div key={index} className="text-xs break-words">
                                        {log}
                                    </div>
                                ))}
                            </div>
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
