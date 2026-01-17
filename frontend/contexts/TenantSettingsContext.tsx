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
        throw new Error('Erro ao carregar configurações do tenant')
      }

      const data: TenantResponse = await response.json()
      setTenant(data)
    } catch (err) {
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
