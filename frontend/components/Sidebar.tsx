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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
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
