'use client'

import { Header } from '@/components/Header'
import { Sidebar } from '@/components/Sidebar'
import { TenantSettingsProvider } from '@/contexts/TenantSettingsContext'
import { createContext, useContext, useState } from 'react'

// Contexto para controlar o drawer em mobile/tablet
const DrawerContext = createContext<{
    isDrawerOpen: boolean
    openDrawer: () => void
    closeDrawer: () => void
}>({
    isDrawerOpen: false,
    openDrawer: () => { },
    closeDrawer: () => { },
})

export const useDrawer = () => useContext(DrawerContext)

/**
 * Layout para páginas protegidas (autenticadas)
 *
 * Inclui Header com nome do tenant e menu do usuário no topo,
 * Sidebar fixa à esquerda para navegação (drawer em mobile/tablet),
 * e área de conteúdo principal à direita.
 * NÃO faz proteção via middleware - cada página deve usar protectedFetch()
 * de lib/api.ts para garantir tratamento padronizado de erros 401.
 */
export default function ProtectedLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const [isDrawerOpen, setIsDrawerOpen] = useState(false)

    return (
        <TenantSettingsProvider>
            <DrawerContext.Provider
                value={{
                    isDrawerOpen,
                    openDrawer: () => setIsDrawerOpen(true),
                    closeDrawer: () => setIsDrawerOpen(false),
                }}
            >
                <div className="min-h-screen bg-gray-50 overflow-x-hidden">
                    <Header />
                    <Sidebar />
                    <main className="pt-16 lg:ml-64 min-w-0">
                        {children}
                    </main>
                </div>
            </DrawerContext.Provider>
        </TenantSettingsProvider>
    )
}
