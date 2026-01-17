'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { TenantResponse, TenantListResponse, AccountResponse } from '@/types/api'
import { useDrawer } from '@/app/(protected)/layout'

// TenantListResponse ainda é usado no handleLogout para verificar múltiplos tenants

export function Header() {
  const router = useRouter()
  const { openDrawer } = useDrawer()
  const [tenant, setTenant] = useState<TenantResponse | null>(null)
  const [account, setAccount] = useState<AccountResponse | null>(null)
  const [showUserMenu, setShowUserMenu] = useState(false)

  // Carregar tenant atual e conta do usuário (padrão try { try { fetch() } catch {} } catch {})
  useEffect(() => {
    const loadData = async () => {
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
      } catch (err) {
        // Erro geral - Header continua funcionando
      }
    }

    loadData()
  }, [])

  // Handler para sair (pode ser logout ou apenas trocar de tenant)
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
    <header className="bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Nome do tenant */}
          <div className="flex items-center">
            {/* Botão hambúrguer para mobile/tablet */}
            <button
              onClick={openDrawer}
              className="mr-3 lg:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100"
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
            <h1 className="text-xl font-bold text-gray-900">Turna</h1>
            {tenant && (
              <>
                <span className="mx-3 text-gray-300">•</span>
                <span className="text-sm font-medium text-gray-700">{tenant.name}</span>
              </>
            )}
          </div>

          {/* Menu do usuário */}
          <div className="flex items-center">
            {account && (
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center text-sm text-gray-700 hover:text-gray-900"
                >
                  <span className="mr-2">{account.email}</span>
                  <span className="text-gray-400">▼</span>
                </button>

                {/* Dropdown do menu do usuário */}
                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-[60]">
                    <div className="py-1" role="menu">
                      <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-200">
                        {account.name}
                      </div>
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
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
