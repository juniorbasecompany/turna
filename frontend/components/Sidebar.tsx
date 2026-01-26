'use client'

import { useDrawer } from '@/app/(protected)/layout'
import { useAuth } from '@/lib/context/auth-context'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface NavItem {
    href: string
    label: string
    icon: React.ReactNode
    adminOnly?: boolean
}

const navItems: NavItem[] = [
    {
        href: '/dashboard',
        label: 'Dashboard',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
        ),
    },
    {
        href: '/hospital',
        label: 'Hospitais',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
        ),
    },
    {
        href: '/tenant',
        label: 'Clínicas',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
        ),
        adminOnly: true,
    },
    {
        href: '/member',
        label: 'Associados',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <circle cx="12" cy="8" r="4" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
            </svg>
        ),
        adminOnly: true,
    },
    {
        href: '/file',
        label: 'Arquivos',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
        ),
    },
    {
        href: '/demand',
        label: 'Demandas',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
        ),
    },
    {
        href: '/schedule',
        label: 'Escalas',
        icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
        ),
    },
]

export function Sidebar() {
    const pathname = usePathname()
    const { isDrawerOpen, closeDrawer } = useDrawer()
    const { account, loading } = useAuth()

    // Handler para fechar drawer ao clicar em um item
    const handleLinkClick = () => {
        closeDrawer()
    }

    // Filtrar itens do menu baseado em permissões
    // Se ainda estiver carregando, não mostrar itens admin-only
    // Se já carregou e account existe, verificar role
    const visibleItems = navItems.filter((item) => {
        if (item.adminOnly) {
            // Se ainda está carregando, não mostrar
            if (loading) {
                return false
            }
            // Se account existe e é admin, mostrar
            return account?.role === 'admin'
        }
        return true
    })

    return (
        <>
            {/* Overlay para fechar drawer ao clicar fora (mobile/tablet) */}
            {isDrawerOpen && (
                <div
                    className="fixed inset-0 bg-black/30 z-40 lg:hidden"
                    onClick={closeDrawer}
                    aria-hidden="true"
                />
            )}

            {/* Sidebar: fixa em desktop, drawer em mobile/tablet */}
            <aside
                className={`
          w-64 bg-white border-r border-gray-200 fixed left-0 top-0 h-screen pt-16 z-50
          transform transition-transform duration-300 ease-in-out
          lg:translate-x-0
          ${isDrawerOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
            >
                <nav className="p-4 space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                onClick={handleLinkClick}
                                className={`
                  flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors
                  ${isActive
                                        ? 'bg-gray-100 text-gray-900'
                                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                                    }
                `}
                            >
                                <span className="mr-3">{item.icon}</span>
                                {item.label}
                            </Link>
                        )
                    })}
                </nav>
            </aside>
        </>
    )
}
