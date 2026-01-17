'use client'

import { Header } from '@/components/Header'

/**
 * Layout para páginas protegidas (autenticadas)
 *
 * Inclui Header com nome do tenant, seletor de tenant e menu do usuário.
 * NÃO faz proteção via middleware - cada página deve usar fetch() direto
 * seguindo o padrão de /dashboard.
 */
export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main>{children}</main>
    </div>
  )
}
