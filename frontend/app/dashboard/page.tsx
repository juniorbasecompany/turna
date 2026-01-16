'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { TenantResponse, TenantListResponse } from '@/types/api'

export default function DashboardPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [tenant, setTenant] = useState<TenantResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Carregar informações do tenant (EXATAMENTE igual ao padrão de /select-tenant)
  const loadTenant = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Primeiro, tentar buscar dados atualizados do servidor
      // Isso garante que sempre temos os dados mais recentes
      try {
        const tenantRes = await fetch('/api/tenant/me', {
          method: 'GET',
          credentials: 'include',
        })

        if (tenantRes.ok) {
          const tenantData: TenantResponse = await tenantRes.json()
          setTenant(tenantData)
          setError(null)
          setLoading(false)
          return
        }
      } catch (err) {
        // Se a API falhar, continuar (não redirecionar, apenas tentar outras opções ou mostrar erro)
      }

      // Se chegou aqui, não foi possível carregar dados do servidor
      // Não redirecionar para /login - apenas mostrar erro
      // Isso permite que a página funcione mesmo após refresh se houver problema temporário
      setError('Não foi possível carregar informações da clínica. Por favor, tente recarregar a página.')
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || 'Erro ao carregar informações da clínica')
      } else {
        setError('Erro desconhecido ao carregar informações da clínica')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // Carregar tenant ao montar
  useEffect(() => {
    loadTenant()
  }, [loadTenant])

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

  // Mostrar loading enquanto carrega dados
  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Turna</h1>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </main>
    )
  }

  // Dashboard
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Turna</h1>
        {tenant ? (
          <p className="mt-4 text-gray-600">
            Dashboard - <span className="font-semibold text-gray-900">{tenant.name}</span>
          </p>
        ) : error ? (
          <p className="mt-4 text-red-600">{error}</p>
        ) : (
          <p className="mt-4 text-gray-600">Dashboard</p>
        )}
        <div className="mt-8">
          <button
            onClick={handleLogout}
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            Sair
          </button>
        </div>
      </div>
    </main>
  )
}
