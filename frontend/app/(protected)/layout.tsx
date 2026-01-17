'use client'

import { Header } from '@/components/Header'
import { Sidebar } from '@/components/Sidebar'

/**
 * Layout para páginas protegidas (autenticadas)
 *
 * Inclui Header com nome do tenant e menu do usuário no topo,
 * Sidebar fixa à esquerda para navegação,
 * e área de conteúdo principal à direita.
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
      <Sidebar />
      <main className="ml-64 pt-16">
        {children}
      </main>
    </div>
  )
}
