'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { TenantResponse } from '@/types/api'
import { TenantFormatSettings } from '@/lib/tenantFormat'

interface TenantSettingsContextType {
  settings: TenantFormatSettings | null
  tenant: TenantResponse | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

const TenantSettingsContext = createContext<TenantSettingsContextType>({
  settings: null,
  tenant: null,
  loading: true,
  error: null,
  refresh: async () => {},
})

export const useTenantSettings = () => useContext(TenantSettingsContext)

/**
 * Verifica se é erro de conexão (fetch falhou ou 500 com mensagem de conexão).
 */
function isConnectionError(error?: Error | unknown, response?: Response, errorData?: { detail?: string }): boolean {
  if (error instanceof Error) {
    const msg = error.message.toLowerCase()
    return msg.includes('fetch') || msg.includes('network') || msg.includes('connection')
  }
  if (response?.status === 500 && errorData?.detail) {
    const detail = errorData.detail.toLowerCase()
    return detail.includes('fetch') || detail.includes('conexão') || detail.includes('interno do servidor')
  }
  if (response?.status === 401) {
    return true
  }
  return false
}

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
 * Provider que gerencia as configurações do tenant atual (timezone, locale, currency).
 * Carrega as configurações uma única vez via GET /tenant/me.
 */
export function TenantSettingsProvider({ children }: { children: ReactNode }) {
  const [tenant, setTenant] = useState<TenantResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTenantSettings = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('/api/tenant/me', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        if (isConnectionError(undefined, response, errorData)) {
          console.log('[TenantSettingsContext] Erro de conexão, redirecionando para login')
          redirectToLogin()
          return
        }
        throw new Error('Erro ao carregar configurações do tenant')
      }

      const data: TenantResponse = await response.json()
      setTenant(data)
    } catch (err) {
      if (isConnectionError(err)) {
        console.log('[TenantSettingsContext] Erro de conexão (catch), redirecionando para login')
        redirectToLogin()
        return
      }
      const message = err instanceof Error ? err.message : 'Erro desconhecido'
      setError(message)
      console.error('Erro ao carregar configurações do tenant:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTenantSettings()
  }, [])

  // Converter TenantResponse para TenantFormatSettings
  const settings: TenantFormatSettings | null = tenant
    ? {
        timezone: tenant.timezone,
        locale: tenant.locale,
        currency: tenant.currency,
      }
    : null

  return (
    <TenantSettingsContext.Provider
      value={{
        settings,
        tenant,
        loading,
        error,
        refresh: loadTenantSettings,
      }}
    >
      {children}
    </TenantSettingsContext.Provider>
  )
}
