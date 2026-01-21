'use client'

import { useDrawer } from '@/app/(protected)/layout'
import { AccountResponse, TenantListResponse, TenantOption, TenantResponse } from '@/types/api'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'

export function Header() {
    const router = useRouter()
    const { openDrawer } = useDrawer()
    const [tenant, setTenant] = useState<TenantResponse | null>(null)
    const [account, setAccount] = useState<AccountResponse | null>(null)
    const [showUserMenu, setShowUserMenu] = useState(false)
    const [availableTenants, setAvailableTenants] = useState<TenantOption[]>([])
    const [switchingTenant, setSwitchingTenant] = useState(false)

    // Função para carregar dados
    const loadData = useCallback(async () => {
        try {
            // Carregar tenant atual
            try {
                const tenantRes = await fetch('/api/tenant/me', {
                    method: 'GET',
                    credentials: 'include',
                })

                if (tenantRes.ok) {
                    const tenantData: TenantResponse = await tenantRes.json()
                    setTenant(tenantData)
                }
            } catch (err) {
                // Se API falhar, continuar (não quebrar Header)
            }

            // Carregar conta do usuário
            try {
                const accountRes = await fetch('/api/auth/me', {
                    method: 'GET',
                    credentials: 'include',
                })

                if (accountRes.ok) {
                    const accountData = await accountRes.json()
                    setAccount(accountData.account || null)
                }
            } catch (err) {
                // Se API falhar, continuar (não quebrar Header)
            }

            // Carregar lista de tenants disponíveis
            try {
                const tenantsRes = await fetch('/api/auth/tenant/list', {
                    method: 'GET',
                    credentials: 'include',
                })

                if (tenantsRes.ok) {
                    const tenantsData: TenantListResponse = await tenantsRes.json()
                    setAvailableTenants(tenantsData.tenants || [])
                }
            } catch (err) {
                // Se API falhar, continuar (não quebrar Header)
            }
        } catch (err) {
            // Erro geral - Header continua funcionando
        }
    }, [])

    // Carregar tenant atual, conta do usuário e lista de tenants disponíveis
    useEffect(() => {
        loadData()
    }, [loadData])

    // Resetar estado de switchingTenant quando o componente monta
    // Isso garante que se o estado ficou preso de uma sessão anterior, será resetado
    useEffect(() => {
        setSwitchingTenant(false)
    }, [])

    // Escutar eventos de mudança nos tenants
    useEffect(() => {
        const handleTenantChange = () => {
            // Recarregar lista de tenants quando houver mudanças
            loadData()
        }

        // Escutar evento customizado disparado pelo painel de tenants
        window.addEventListener('tenant-list-updated', handleTenantChange)

        return () => {
            window.removeEventListener('tenant-list-updated', handleTenantChange)
        }
    }, [loadData])

    // Handler para trocar de tenant
    const handleSwitchTenant = useCallback(async (tenantId: number) => {
        if (switchingTenant) return

        setSwitchingTenant(true)
        setShowUserMenu(false)

        try {
            // Trocar para o tenant selecionado
            const response = await fetch('/api/auth/switch-tenant', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ tenant_id: tenantId }),
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Erro ao trocar de clínica' }))
                console.error('Erro ao trocar de tenant:', errorData)
                alert(errorData.detail || 'Erro ao trocar de clínica')
                setSwitchingTenant(false)
                return
            }

            const result = await response.json()

            // O cookie já foi atualizado pelo backend via NextResponse no route.ts
            // Limpar sessionStorage (similar ao login)
            sessionStorage.removeItem('login_id_token')
            sessionStorage.removeItem('login_response')

            // Redirecionar para o dashboard usando window.location.href
            // Isso força um reload completo e desmonta o componente, resetando todos os estados
            // Similar ao login, garante que tudo seja reinicializado com o novo tenant
            // Não precisamos resetar switchingTenant aqui porque o componente será desmontado
            window.location.href = '/dashboard'

            // Se o redirect falhar por algum motivo (navegador bloqueou, etc.),
            // o componente não será desmontado e o estado ficará preso.
            // O useEffect que roda na montagem do componente garante que o estado seja resetado
            // se o usuário recarregar a página ou navegar manualmente.
        } catch (err) {
            console.error('Erro ao trocar de tenant:', err)
            alert('Erro ao trocar de clínica. Tente novamente.')
            setSwitchingTenant(false)
        }
    }, [switchingTenant])

    // Handler para sair (logout completo)
    const handleLogout = useCallback(async () => {
        try {
            // Verificar se há múltiplos tenants ou convites pendentes
            const tenantListRes = await fetch('/api/auth/tenant/list', {
                credentials: 'include',
            })

            if (tenantListRes.ok) {
                const tenantListData: TenantListResponse = await tenantListRes.json()
                const tenantsCount = (tenantListData.tenants || []).length
                const invitesCount = (tenantListData.invites || []).length

                const hasMultipleTenants = tenantsCount > 1
                const hasPendingInvites = invitesCount > 0

                // Se há múltiplos tenants OU convites pendentes: apenas redirecionar para seleção (sem logout)
                if (hasMultipleTenants || hasPendingInvites) {
                    router.push('/select-tenant')
                    return
                }
            }

            // Se chegou aqui, só tem um tenant e nenhum convite: fazer logout
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
            // Em caso de erro ao verificar, fazer logout completo e redirecionar para login
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    credentials: 'include',
                })
            } catch (logoutErr) {
                // Ignorar erro de logout
            }
            sessionStorage.removeItem('login_id_token')
            sessionStorage.removeItem('login_response')
            router.push('/login')
        }
    }, [router])

    return (
        <header className="bg-white border-b border-gray-200 fixed top-0 left-0 lg:left-64 right-0 z-30">
            <div className="px-4 sm:px-6 lg:px-8 min-h-16 py-2">
                <div className="flex flex-wrap items-center gap-2">
                    {/* Logo / Nome do tenant */}
                    <div className="flex items-center flex-shrink-0 min-w-0 flex-1">
                        {/* Botão hambúrguer para mobile/tablet */}
                        <button
                            onClick={openDrawer}
                            className="mr-3 lg:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 flex-shrink-0"
                            aria-label="Abrir menu"
                        >
                            <svg
                                className="w-6 h-6"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M4 6h16M4 12h16M4 18h16"
                                />
                            </svg>
                        </button>
                        {tenant && (
                            <h1 className="text-xl font-bold text-gray-900 truncate">{tenant.name}</h1>
                        )}
                    </div>

                    {/* Menu do usuário - alinhado à direita, quebra para linha de baixo quando necessário */}
                    {account && (
                        <div className="relative flex-shrink-0 ml-auto w-full sm:w-auto flex justify-end">
                            <button
                                onClick={() => setShowUserMenu(!showUserMenu)}
                                className="flex items-center text-sm text-gray-700 hover:text-gray-900"
                            >
                                <span className="mr-2">{account.name}</span>
                                <span className="text-gray-400">▼</span>
                            </button>

                            {/* Dropdown do menu do usuário */}
                            {showUserMenu && (
                                <div className="absolute right-0 top-full mt-1 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-[60]">
                                    <div className="py-1" role="menu">
                                        {/* Lista de tenants */}
                                        {availableTenants.length > 0 && (
                                            <>
                                                {availableTenants.map((t) => {
                                                    const isCurrentTenant = tenant?.id === t.tenant_id
                                                    return (
                                                        <button
                                                            key={t.tenant_id}
                                                            onClick={() => handleSwitchTenant(t.tenant_id)}
                                                            disabled={switchingTenant || isCurrentTenant}
                                                            className={`block w-full text-left px-4 py-2 text-sm ${isCurrentTenant
                                                                ? 'bg-blue-50 text-blue-700 font-medium'
                                                                : 'text-gray-700 hover:bg-gray-50'
                                                                } ${switchingTenant ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                            role="menuitem"
                                                            title={isCurrentTenant ? 'Clínica atual' : `Trocar para ${t.name}`}
                                                        >
                                                            <div className="flex items-center justify-between">
                                                                <span>{t.name}</span>
                                                                {isCurrentTenant && (
                                                                    <span className="text-xs text-blue-600">✓</span>
                                                                )}
                                                                {switchingTenant && !isCurrentTenant && (
                                                                    <LoadingSpinner />
                                                                )}
                                                            </div>
                                                        </button>
                                                    )
                                                })}
                                                <div className="border-t border-gray-200 my-1" />
                                            </>
                                        )}

                                        {/* Botão Sair */}
                                        <button
                                            onClick={handleLogout}
                                            disabled={switchingTenant}
                                            className={`block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 ${switchingTenant ? 'opacity-50 cursor-not-allowed' : ''
                                                }`}
                                            role="menuitem"
                                        >
                                            Sair
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Overlay para fechar dropdown do menu ao clicar fora */}
            {showUserMenu && (
                <div
                    className="fixed inset-0 z-[55]"
                    onClick={() => {
                        setShowUserMenu(false)
                    }}
                />
            )}
        </header>
    )
}
