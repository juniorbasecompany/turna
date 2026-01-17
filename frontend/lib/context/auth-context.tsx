'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { AccountResponse, TenantResponse } from '@/types/api'

interface AuthContextType {
  account: AccountResponse | null
  tenant: TenantResponse | null
  loading: boolean
  refreshAccount: () => Promise<void>
  refreshTenant: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<AccountResponse | null>(null)
  const [tenant, setTenant] = useState<TenantResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshAccount = async () => {
    try {
      // Usar fetch() direto seguindo padrão de outras páginas
      const response = await fetch('/api/me', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        // Se 401, limpar estado mas não redirecionar (páginas protegidas gerenciam isso)
        if (response.status === 401) {
          setAccount(null)
          setTenant(null)
          return
        }
        throw new Error(`Erro HTTP ${response.status}`)
      }

      const data: AccountResponse = await response.json()
      setAccount(data)
    } catch (error) {
      // Silenciosamente falha se não autenticado
      console.debug('Erro ao carregar account:', error)
      setAccount(null)
    }
  }

  const refreshTenant = async () => {
    try {
      // Usar fetch() direto seguindo padrão de outras páginas
      const response = await fetch('/api/tenant/me', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        setTenant(null)
        return
      }

      const data: TenantResponse = await response.json()
      setTenant(data)
    } catch (error) {
      console.debug('Erro ao carregar tenant:', error)
      setTenant(null)
    }
  }

  useEffect(() => {
    // Não carregar dados de autenticação se estiver em páginas de autenticação
    // Isso evita loops de redirecionamento
    if (typeof window !== 'undefined') {
      const path = window.location.pathname
      if (path.startsWith('/login') || path.startsWith('/select-tenant')) {
        setLoading(false)
        return
      }
    }

    // Carregar dados iniciais
    const loadAuth = async () => {
      setLoading(true)
      try {
        await Promise.all([refreshAccount(), refreshTenant()])
      } catch (error) {
        // Silenciosamente falha se não autenticado
        console.debug('Auth check failed:', error)
      } finally {
        setLoading(false)
      }
    }

    loadAuth()
  }, [])

  const value: AuthContextType = {
    account,
    tenant,
    loading,
    refreshAccount,
    refreshTenant,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
