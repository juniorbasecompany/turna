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

/**
 * Redireciona para login, limpando dados de sessão.
 */
function redirectToLogin() {
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem('login_id_token')
    sessionStorage.removeItem('login_response')
    window.location.href = '/login'
  }
}

/**
 * Verifica se o erro ou resposta indica problema de conexão.
 */
function isConnectionError(error?: Error, response?: Response, errorData?: { detail?: string }): boolean {
  // Erro de rede (fetch falhou)
  if (error) {
    const msg = error.message.toLowerCase()
    return msg.includes('fetch') || msg.includes('network') || msg.includes('connection')
  }
  // Resposta 500 com indicação de erro de conexão
  if (response?.status === 500 && errorData?.detail) {
    const detail = errorData.detail.toLowerCase()
    return detail.includes('fetch') || detail.includes('conexão') || detail.includes('interno do servidor')
  }
  return false
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<AccountResponse | null>(null)
  const [tenant, setTenant] = useState<TenantResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshAccount = async () => {
    let response: Response | undefined
    let errorData: { detail?: string } | undefined

    try {
      response = await fetch('/api/me', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        errorData = await response.json().catch(() => ({}))
        
        // 401 ou erro de conexão → redirecionar para login
        if (response.status === 401 || isConnectionError(undefined, response, errorData)) {
          console.log('[AuthContext] refreshAccount: 401 ou erro de conexão, redirecionando para login')
          setAccount(null)
          setTenant(null)
          redirectToLogin()
          return
        }
        throw new Error(`Erro HTTP ${response.status}`)
      }

      const data: AccountResponse = await response.json()
      setAccount(data)
    } catch (error) {
      console.error('[AuthContext] refreshAccount erro:', error)
      // Erro de conexão (fetch falhou) → redirecionar para login
      if (isConnectionError(error instanceof Error ? error : undefined)) {
        console.log('[AuthContext] refreshAccount: erro de conexão detectado, redirecionando para login')
        redirectToLogin()
        return
      }
      setAccount(null)
    }
  }

  const refreshTenant = async () => {
    let response: Response | undefined
    let errorData: { detail?: string } | undefined

    try {
      response = await fetch('/api/tenant/me', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        errorData = await response.json().catch(() => ({}))
        
        // 401 ou erro de conexão → redirecionar para login
        if (response.status === 401 || isConnectionError(undefined, response, errorData)) {
          console.log('[AuthContext] refreshTenant: 401 ou erro de conexão, redirecionando para login')
          setTenant(null)
          redirectToLogin()
          return
        }
        setTenant(null)
        return
      }

      const data: TenantResponse = await response.json()
      setTenant(data)
    } catch (error) {
      console.error('[AuthContext] refreshTenant erro:', error)
      // Erro de conexão (fetch falhou) → redirecionar para login
      if (isConnectionError(error instanceof Error ? error : undefined)) {
        console.log('[AuthContext] refreshTenant: erro de conexão detectado, redirecionando para login')
        redirectToLogin()
        return
      }
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
