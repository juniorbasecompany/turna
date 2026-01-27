'use client'

import { LoadingSpinner } from '@/components/LoadingSpinner'
import { InviteOption, TenantListResponse, TenantOption } from '@/types/api'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'

// Função utilitária para decidir navegação baseada em ACTIVE e PENDING
function decideNavigation(tenants: TenantOption[], invites: InviteOption[]): 'dashboard' | 'create-tenant' | 'select' {
    const activeCount = tenants.length
    const pendingCount = invites.length

    if (activeCount === 1 && pendingCount === 0) {
        return 'dashboard'
    }
    if (activeCount === 0 && pendingCount === 0) {
        return 'create-tenant'
    }
    return 'select'
}

export default function SelectTenantPage() {
    const router = useRouter()
    const [loading, setLoading] = useState(true)
    const [selecting, setSelecting] = useState(false)
    const [creating, setCreating] = useState(false)
    const [processingInvite, setProcessingInvite] = useState<number | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [tenants, setTenants] = useState<TenantOption[]>([])
    const [invites, setInvites] = useState<InviteOption[]>([])
    // Carregar lista de tenants
    const loadTenants = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
            // Primeiro, tentar buscar dados atualizados do servidor
            // Isso garante que sempre temos os dados mais recentes (incluindo novos convites)
            try {
                const response = await fetch('/api/auth/tenant/list', {
                    method: 'GET',
                    credentials: 'include',
                })

                if (response.ok) {
                    const data: TenantListResponse = await response.json()
                    setTenants(data.tenants || [])
                    setInvites(data.invites || [])
                    // Atualizar sessionStorage com os dados mais recentes
                    const loginResponseStr = sessionStorage.getItem('login_response')
                    if (loginResponseStr) {
                        try {
                            const loginResponse = JSON.parse(loginResponseStr)
                            loginResponse.tenants = data.tenants || []
                            loginResponse.invites = data.invites || []
                            sessionStorage.setItem('login_response', JSON.stringify(loginResponse))
                        } catch (err) {
                            // Ignorar erro de atualização do sessionStorage
                        }
                    }
                    setLoading(false)
                    return
                }
            } catch (err) {
                // Se a API falhar, tentar usar dados do sessionStorage como fallback
            }

            // Fallback: usar dados do sessionStorage (vindos do login) se a API não estiver disponível
            // Isso permite que a página funcione mesmo após refresh sem autenticação ativa
            const loginResponseStr = sessionStorage.getItem('login_response')
            if (loginResponseStr) {
                try {
                    const loginResponse = JSON.parse(loginResponseStr)
                    if (loginResponse.tenants && Array.isArray(loginResponse.tenants)) {
                        setTenants(loginResponse.tenants)
                        // Carregar invites se disponíveis
                        if (loginResponse.invites && Array.isArray(loginResponse.invites)) {
                            setInvites(loginResponse.invites)
                        }
                        setLoading(false)
                        return
                    }
                } catch (err) {
                    // Ignorar erro de parse
                }
            }

            // Se chegou aqui, não há dados disponíveis
            setError('Não foi possível carregar a lista de clínicas. Por favor, tente recarregar a página.')
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message || 'Erro ao carregar lista de clínicas')
            } else {
                setError('Erro desconhecido ao carregar lista de clínicas')
            }
        } finally {
            setLoading(false)
        }
    }, [])

    // Carregar tenants ao montar
    useEffect(() => {
        loadTenants()
    }, [loadTenants])

    // Handler para seleção de tenant
    const handleSelectTenant = useCallback(
        async (tenantId: number) => {
            if (selecting) {
                return
            }

            // Verificação de segurança: não permitir seleção se não há tenants
            if (tenants.length === 0) {
                setError('Nenhuma clínica disponível para seleção')
                return
            }

            setSelecting(true)
            setError(null)

            try {
                // Obter id_token do sessionStorage (salvo durante o login)
                const idToken = sessionStorage.getItem('login_id_token')

                let response: Response
                let result: any

                if (idToken) {
                    // Se há id_token, usar o endpoint que requer id_token do Google
                    response = await fetch('/api/auth/google/select-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            id_token: idToken,
                            tenant_id: tenantId,
                        }),
                    })
                    result = await response.json()
                } else {
                    // Se não há id_token, verificar se está autenticado via cookie
                    // Tentar usar switch-tenant (funciona apenas com cookie)
                    response = await fetch('/api/auth/switch-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            tenant_id: tenantId,
                        }),
                    })
                    result = await response.json()

                    // Se falhar por não estar autenticado, redirecionar imediatamente para login
                    if (response.status === 401) {
                        sessionStorage.removeItem('login_id_token')
                        sessionStorage.removeItem('login_response')
                        router.push('/login')
                        return
                    }
                }

                if (!response.ok) {
                    if (response.status === 403) {
                        setError('Acesso negado a esta clínica')
                    } else if (response.status === 404) {
                        setError('Conta não encontrada')
                    } else {
                        setError(result.detail || 'Erro ao selecionar clínica')
                    }
                    setSelecting(false)
                    return
                }

                // Sucesso: limpar sessionStorage e redirecionar para dashboard
                sessionStorage.removeItem('login_id_token')
                sessionStorage.removeItem('login_response')
                router.push('/dashboard')
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message || 'Erro ao selecionar clínica')
                } else {
                    setError('Erro desconhecido ao selecionar clínica')
                }
                setSelecting(false)
            }
        },
        [selecting, router, tenants]
    )

    // Handler para criar tenant automaticamente
    const handleCreateTenant = useCallback(
        async () => {
            if (creating) {
                return
            }

            setCreating(true)
            setError(null)

            try {
                // Obter id_token do sessionStorage (salvo durante o login)
                const idToken = sessionStorage.getItem('login_id_token')

                // Se não temos id_token, precisamos autenticar primeiro
                if (!idToken) {
                    sessionStorage.removeItem('login_response')
                    router.push('/login')
                    return
                }

                // Criar tenant automaticamente usando endpoint especial
                const createResponse = await fetch('/api/auth/google/create-tenant', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        id_token: idToken,
                    }),
                })

                if (!createResponse.ok) {
                    const createResult = await createResponse.json()
                    setError(createResult.detail || 'Erro ao criar clínica')
                    setCreating(false)
                    return
                }

                // Sucesso: limpar sessionStorage e redirecionar para dashboard
                sessionStorage.removeItem('login_id_token')
                sessionStorage.removeItem('login_response')
                router.push('/dashboard')
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message || 'Erro ao criar clínica')
                } else {
                    setError('Erro desconhecido ao criar clínica')
                }
                setCreating(false)
            }
        },
        [creating, router]
    )

    // Handler para aceitar convite
    const handleAcceptInvite = useCallback(
        async (invite: InviteOption) => {
            // Prevenir múltiplos cliques no mesmo botão
            if (processingInvite === invite.member_id || selecting) {
                return
            }

            setProcessingInvite(invite.member_id)
            setError(null)

            try {
                // Usar o tenant do próprio invite para obter token
                // Se não houver tenant ativo, usar o tenant do invite
                const idToken = sessionStorage.getItem('login_id_token')
                let tenantToUse: TenantOption | null = null

                // Priorizar usar um tenant ativo se disponível (mais seguro)
                if (tenants.length > 0) {
                    tenantToUse = tenants[0]
                } else {
                    // Se não há tenant ativo, usar o tenant do próprio invite
                    // Isso permite aceitar o primeiro convite mesmo sem tenant ativo
                    tenantToUse = {
                        tenant_id: invite.tenant_id,
                        name: invite.name,
                        slug: invite.slug,
                        role: invite.role,
                    }
                }

                // 1. Obter token usando o tenant selecionado
                // Tentar usar switch-tenant se não tiver id_token (mas estiver autenticado)
                let selectResponse: Response
                if (idToken) {
                    selectResponse = await fetch('/api/auth/google/select-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            id_token: idToken,
                            tenant_id: tenantToUse.tenant_id,
                        }),
                    })
                } else {
                    // Tentar usar switch-tenant (funciona apenas com cookie)
                    selectResponse = await fetch('/api/auth/switch-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            tenant_id: tenantToUse.tenant_id,
                        }),
                    })

                    // Se falhar por não estar autenticado, redirecionar imediatamente para login
                    if (selectResponse.status === 401) {
                        sessionStorage.removeItem('login_id_token')
                        sessionStorage.removeItem('login_response')
                        router.push('/login')
                        return
                    }
                }

                if (!selectResponse.ok) {
                    const selectResult = await selectResponse.json()
                    setError(selectResult.detail || 'Erro ao obter token de autenticação')
                    setProcessingInvite(null)
                    return
                }

                // 2. Aceitar o convite
                const acceptResponse = await fetch(`/api/auth/invites/${invite.member_id}/accept`, {
                    method: 'POST',
                    credentials: 'include',
                })

                if (!acceptResponse.ok) {
                    const acceptResult = await acceptResponse.json()
                    setError(acceptResult.detail || 'Erro ao aceitar convite')
                    setProcessingInvite(null)
                    return
                }

                // 3. Emitir token para o tenant do convite aceito
                let finalSelectResponse: Response
                if (idToken) {
                    finalSelectResponse = await fetch('/api/auth/google/select-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            id_token: idToken,
                            tenant_id: invite.tenant_id,
                        }),
                    })
                } else {
                    // Usar switch-tenant (já está autenticado após aceitar o convite)
                    finalSelectResponse = await fetch('/api/auth/switch-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            tenant_id: invite.tenant_id,
                        }),
                    })
                }

                if (!finalSelectResponse.ok) {
                    const finalResult = await finalSelectResponse.json()
                    setError(finalResult.detail || 'Erro ao entrar na clínica do convite')
                    setProcessingInvite(null)
                    return
                }

                // Sucesso: limpar sessionStorage e redirecionar para dashboard
                sessionStorage.removeItem('login_id_token')
                sessionStorage.removeItem('login_response')
                router.push('/dashboard')
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message || 'Erro ao aceitar convite')
                } else {
                    setError('Erro desconhecido ao aceitar convite')
                }
                setProcessingInvite(null)
            }
        },
        [processingInvite, selecting, tenants, router]
    )

    // Handler para rejeitar convite
    const handleRejectInvite = useCallback(
        async (invite: InviteOption) => {
            // Prevenir múltiplos cliques no mesmo botão
            if (processingInvite === invite.member_id || selecting) {
                return
            }

            setProcessingInvite(invite.member_id)
            setError(null)

            try {
                const idToken = sessionStorage.getItem('login_id_token')

                // Se não há tenant ativo, precisamos obter token via id_token para rejeitar
                if (tenants.length === 0) {
                    if (!idToken) {
                        sessionStorage.removeItem('login_response')
                        router.push('/login')
                        return
                    }

                    // Obter token temporário usando o tenant do próprio invite (PENDING)
                    const tempSelectResponse = await fetch('/api/auth/google/select-tenant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            id_token: idToken,
                            tenant_id: invite.tenant_id,
                        }),
                    })

                    if (!tempSelectResponse.ok) {
                        const tempResult = await tempSelectResponse.json()
                        setError(tempResult.detail || 'Erro ao obter token de autenticação')
                        setProcessingInvite(null)
                        return
                    }
                } else {
                    // Se há tenant ativo, usar o primeiro para obter token
                    const firstTenant = tenants[0]

                    // 1. Entrar no primeiro tenant ativo para obter token
                    let selectResponse: Response
                    if (idToken) {
                        selectResponse = await fetch('/api/auth/google/select-tenant', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            credentials: 'include',
                            body: JSON.stringify({
                                id_token: idToken,
                                tenant_id: firstTenant.tenant_id,
                            }),
                        })
                    } else {
                        // Tentar usar switch-tenant (funciona apenas com cookie)
                        selectResponse = await fetch('/api/auth/switch-tenant', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            credentials: 'include',
                            body: JSON.stringify({
                                tenant_id: firstTenant.tenant_id,
                            }),
                        })

                        // Se falhar por não estar autenticado, redirecionar imediatamente para login
                        if (selectResponse.status === 401) {
                            sessionStorage.removeItem('login_id_token')
                            sessionStorage.removeItem('login_response')
                            router.push('/login')
                            return
                        }
                    }

                    if (!selectResponse.ok) {
                        const selectResult = await selectResponse.json()
                        setError(selectResult.detail || 'Erro ao obter token de autenticação')
                        setProcessingInvite(null)
                        return
                    }
                }

                // 2. Rejeitar o convite
                const rejectResponse = await fetch(`/api/auth/invites/${invite.member_id}/reject`, {
                    method: 'POST',
                    credentials: 'include',
                })

                if (!rejectResponse.ok) {
                    const rejectResult = await rejectResponse.json()
                    setError(rejectResult.detail || 'Erro ao rejeitar convite')
                    setProcessingInvite(null)
                    return
                }

                // Sucesso: recarregar snapshot completo para aplicar regras de navegação
                setProcessingInvite(null)
                await loadTenants()
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message || 'Erro ao rejeitar convite')
                } else {
                    setError('Erro desconhecido ao rejeitar convite')
                }
                setProcessingInvite(null)
            }
        },
        [processingInvite, selecting, tenants, router, loadTenants]
    )

    // Aplicar decisão de navegação após carregar tenants/invites
    useEffect(() => {
        // Só aplicar decisão se não estiver carregando e não estiver processando ações
        if (loading || selecting || creating || processingInvite !== null) {
            return
        }

        const navigation = decideNavigation(tenants, invites)

        if (navigation === 'dashboard' && tenants.length === 1) {
            // Entrar direto no dashboard do único tenant
            handleSelectTenant(tenants[0].tenant_id)
        } else if (navigation === 'create-tenant') {
            // Criar clínica automaticamente
            handleCreateTenant()
        }
        // Caso contrário, mostrar tela de seleção (não fazer nada)
    }, [loading, selecting, creating, processingInvite, tenants, invites, handleSelectTenant, handleCreateTenant])

    // Handler para logout
    const handleLogout = useCallback(async () => {
        try {
            // Chamar API de logout para remover cookie
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include',
            })

            // Limpar sessionStorage
            sessionStorage.removeItem('login_id_token')
            sessionStorage.removeItem('login_response')

            // Redirecionar para login
            router.push('/login')
        } catch (err) {
            // Mesmo em caso de erro, limpar sessionStorage e redirecionar
            sessionStorage.removeItem('login_id_token')
            sessionStorage.removeItem('login_response')
            router.push('/login')
        }
    }, [router])

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="max-w-md w-full space-y-8 p-8">
                    <div className="text-center">
                        <h2 className="text-3xl font-extrabold text-gray-900">Turna</h2>
                        <div className="mt-2 flex justify-center">
                            <LoadingSpinner />
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    if (error && tenants.length === 0 && invites.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="max-w-md w-full space-y-8 p-8">
                    <div>
                        <h2 className="text-center text-3xl font-extrabold text-gray-900">
                            Turna
                        </h2>
                    </div>
                    <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-sm text-red-800">{error}</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8 p-8">
                <div>
                    <h2 className="text-center text-3xl font-extrabold text-gray-900">
                        Selecionar Clínica
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        Escolha a clínica que deseja acessar
                    </p>
                </div>

                {error && (
                    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                        <p className="text-sm text-yellow-800">{error}</p>
                    </div>
                )}

                {selecting ? (
                    <div className="flex justify-center items-center py-4">
                        <LoadingSpinner />
                    </div>
                ) : (
                    <div className="space-y-3">
                        {tenants.length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-700 mb-2">
                                    Suas Clínicas
                                </h3>
                                <div className="space-y-2">
                                    {tenants.map((tenant) => (
                                        <button
                                            key={tenant.tenant_id}
                                            onClick={() => handleSelectTenant(tenant.tenant_id)}
                                            disabled={selecting}
                                            className="w-full px-4 py-3 text-left bg-white border border-gray-300 rounded-md hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                        >
                                            <div className="font-medium text-gray-900">
                                                {tenant.name}
                                            </div>
                                            <div className="text-sm text-gray-500">
                                                {tenant.role}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {invites.length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-700 mb-2">
                                    Convites Pendentes
                                </h3>
                                <div className="space-y-2">
                                    {invites.map((invite) => (
                                        <div
                                            key={`invite-${invite.member_id}`}
                                            className="w-full px-4 py-3 bg-yellow-50 border border-yellow-300 rounded-md"
                                        >
                                            <div className="mb-2">
                                                <div className="font-medium text-gray-900">
                                                    {invite.name}
                                                </div>
                                                <div className="text-sm text-yellow-700">
                                                    Convite pendente • {invite.role}
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleAcceptInvite(invite)}
                                                    disabled={processingInvite === invite.member_id || selecting}
                                                    className="flex-1 px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                                                >
                                                    {processingInvite === invite.member_id ? <LoadingSpinner /> : 'Aceitar'}
                                                </button>
                                                <button
                                                    onClick={() => handleRejectInvite(invite)}
                                                    disabled={processingInvite === invite.member_id || selecting}
                                                    className="flex-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                                                >
                                                    {processingInvite === invite.member_id ? <LoadingSpinner /> : 'Rejeitar'}
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {tenants.length === 0 && (
                            <div>
                                <button
                                    onClick={handleCreateTenant}
                                    disabled={creating || selecting || processingInvite !== null}
                                    className="w-full px-4 py-3 text-center bg-blue-600 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                                >
                                    {creating ? (
                                        <>
                                            <LoadingSpinner />
                                            <span>Criando clínica...</span>
                                        </>
                                    ) : (
                                        'Criar clínica'
                                    )}
                                </button>
                            </div>
                        )}

                        {tenants.length === 0 && invites.length === 0 && !loading && !creating && (
                            <div className="p-4 bg-gray-50 border border-gray-200 rounded-md text-center">
                                <p className="text-sm text-gray-600">
                                    Nenhuma clínica disponível.
                                </p>
                            </div>
                        )}
                    </div>
                )}

                <div className="text-center">
                    <button
                        onClick={handleLogout}
                        className="text-sm text-gray-600 hover:text-gray-800"
                    >
                        Sair
                    </button>
                </div>
            </div>
        </div>
    )
}
