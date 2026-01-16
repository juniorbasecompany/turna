'use client'

import { TenantOption, InviteOption, TenantListResponse } from '@/types/api'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'


export default function SelectTenantPage() {
    const router = useRouter()
    const [loading, setLoading] = useState(true)
    const [selecting, setSelecting] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [tenants, setTenants] = useState<TenantOption[]>([])
    const [invites, setInvites] = useState<InviteOption[]>([])
    // Carregar lista de tenants
    const loadTenants = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
            // Usar dados do sessionStorage (vindos do login) como fonte primária
            // Isso permite que a página funcione mesmo após refresh
            const loginResponseStr = sessionStorage.getItem('login_response')
            if (loginResponseStr) {
                try {
                    const loginResponse = JSON.parse(loginResponseStr)
                    if (loginResponse.tenants && Array.isArray(loginResponse.tenants)) {
                        setTenants(loginResponse.tenants)
                        // Manter sessionStorage para permitir refresh
                        setLoading(false)
                        return
                    }
                } catch (err) {
                    // Ignorar erro de parse e tentar buscar via API
                }
            }

            // Fallback: tentar buscar via GET /auth/tenant/list (pode falhar se não houver JWT válido)
            try {
                const response = await fetch('/api/auth/tenant/list', {
                    method: 'GET',
                    credentials: 'include',
                })

                if (response.ok) {
                    const data: TenantListResponse = await response.json()
                    setTenants(data.tenants || [])
                    setInvites(data.invites || [])
                    setLoading(false)
                    return
                }
            } catch (err) {
                // Ignorar erro e mostrar mensagem abaixo
            }

            // Se chegou aqui, não há dados disponíveis
            setError('Não foi possível carregar a lista de tenants. Por favor, faça login novamente.')
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message || 'Erro ao carregar lista de tenants')
            } else {
                setError('Erro desconhecido ao carregar lista de tenants')
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

            setSelecting(true)
            setError(null)

            try {
                // Obter id_token do sessionStorage (salvo durante o login)
                const idToken = sessionStorage.getItem('login_id_token')

                if (!idToken) {
                    // Se não há token, pedir para o usuário fazer login novamente
                    setError(
                        'Sessão expirada. Por favor, faça login novamente para continuar.'
                    )
                    setSelecting(false)
                    // Limpar dados antigos
                    sessionStorage.removeItem('login_response')
                    // Redirecionar para login após 2 segundos
                    setTimeout(() => {
                        router.push('/login')
                    }, 2000)
                    return
                }

                // Chamar handler de seleção de tenant
                const response = await fetch('/api/auth/google/select-tenant', {
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

                const result = await response.json()

                if (!response.ok) {
                    if (response.status === 403) {
                        setError('Acesso negado a este tenant')
                    } else if (response.status === 404) {
                        setError('Conta não encontrada')
                    } else {
                        setError(result.detail || 'Erro ao selecionar tenant')
                    }
                    setSelecting(false)
                    return
                }

                // Sucesso: limpar sessionStorage e redirecionar para dashboard
                sessionStorage.removeItem('login_id_token')
                sessionStorage.removeItem('login_response')
                router.push('/')
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message || 'Erro ao selecionar tenant')
                } else {
                    setError('Erro desconhecido ao selecionar tenant')
                }
                setSelecting(false)
            }
        },
        [selecting, router]
    )

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="max-w-md w-full space-y-8 p-8">
                    <div className="text-center">
                        <h2 className="text-3xl font-extrabold text-gray-900">Turna</h2>
                        <p className="mt-2 text-sm text-gray-600">Carregando tenants...</p>
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
                        <p className="text-sm text-red-800 mb-3">{error}</p>
                        <button
                            onClick={() => router.push('/login')}
                            className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium"
                        >
                            Voltar para login
                        </button>
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
                        Selecionar Tenant
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        Escolha o tenant que deseja acessar
                    </p>
                </div>

                {error && (
                    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                        <p className="text-sm text-yellow-800">{error}</p>
                    </div>
                )}

                {selecting ? (
                    <div className="flex justify-center items-center py-4">
                        <span className="text-gray-600">Selecionando tenant...</span>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {tenants.length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-700 mb-2">
                                    Seus Tenants
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
                                            key={`invite-${invite.membership_id}`}
                                            className="w-full px-4 py-3 text-left bg-yellow-50 border border-yellow-300 rounded-md"
                                        >
                                            <div className="font-medium text-gray-900">
                                                {invite.name}
                                            </div>
                                            <div className="text-sm text-yellow-700">
                                                Convite pendente • {invite.role}
                                            </div>
                                            <div className="text-xs text-gray-500 mt-1">
                                                Aceite o convite após fazer login em um tenant ativo
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {tenants.length === 0 && invites.length === 0 && !loading && (
                            <div className="p-4 bg-gray-50 border border-gray-200 rounded-md text-center">
                                <p className="text-sm text-gray-600 mb-3">
                                    Nenhum tenant disponível.
                                </p>
                                <button
                                    onClick={() => router.push('/login')}
                                    className="text-sm text-blue-600 hover:text-blue-800"
                                >
                                    Voltar para login
                                </button>
                            </div>
                        )}
                    </div>
                )}

                <div className="text-center">
                    <button
                        onClick={() => router.push('/login')}
                        className="text-sm text-gray-600 hover:text-gray-800"
                    >
                        Voltar para login
                    </button>
                </div>
            </div>
        </div>
    )
}
