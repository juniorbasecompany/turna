'use client'

import { ActionBarSpacer } from '@/components/ActionBar'
import { CardPanel } from '@/components/CardPanel'
import { AccountOption } from '@/types/api'
import { extractErrorMessage } from '@/lib/api'
import { useEffect, useState } from 'react'

export default function AccountPage() {
    const [accounts, setAccounts] = useState<AccountOption[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Carregar lista de contas
    const loadAccounts = async () => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch('/api/account/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
            }

            const data: AccountOption[] = await response.json()
            setAccounts(data)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar contas'
            setError(message)
            console.error('Erro ao carregar contas:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadAccounts()
    }, [])

    return (
        <>
            <CardPanel
                title="Contas"
                description="Visualize as contas de usuários do tenant"
                totalCount={accounts.length}
                loading={loading}
                loadingMessage="Carregando contas..."
                emptyMessage="Nenhuma conta cadastrada ainda."
                countLabel="Total de contas"
                error={error}
            >
                {accounts.map((account) => {
                    return (
                        <div
                            key={account.id}
                            className="rounded-xl border border-slate-200 bg-white min-w-0 cursor-pointer transition-all duration-200 flex flex-col min-h-[200px] hover:shadow-md"
                        >
                            {/* Corpo - Ícone de usuário e informações */}
                            <div className="mb-3 flex-1">
                                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-slate-100">
                                    <div className="flex flex-col items-center justify-center text-blue-500">
                                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                                            <svg
                                                className="w-full h-full"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                                                />
                                            </svg>
                                        </div>
                                        <h3
                                            className="text-sm font-semibold text-center px-2 text-gray-900"
                                            title={account.name}
                                        >
                                            {account.name}
                                        </h3>
                                        <p
                                            className="text-xs text-center px-2 mt-1 text-gray-600"
                                            title={account.email}
                                        >
                                            {account.email}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </CardPanel>

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <ActionBarSpacer />
        </>
    )
}
