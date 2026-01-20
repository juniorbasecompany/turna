'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { FormCheckbox } from '@/components/FormCheckbox'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { protectedFetch } from '@/lib/api'
import { getCardContainerClasses } from '@/lib/cardStyles'
import { AccountResponse } from '@/types/api'
import { useEffect, useState } from 'react'

export default function AccountPage() {
    const { tenant, settings } = useTenantSettings()
    const [accounts, setAccounts] = useState<AccountResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')
    const [showEditArea, setShowEditArea] = useState(false)
    const [editingAccount, setEditingAccount] = useState<AccountResponse | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        role: 'account',
    })
    const [originalFormData, setOriginalFormData] = useState({
        name: '',
        email: '',
        role: 'account',
    })
    const [sendInvite, setSendInvite] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [selectedAccounts, setSelectedAccounts] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)

    // Carregar lista de contas
    const loadAccounts = async () => {
        try {
            setLoading(true)
            setError(null)

            const data = await protectedFetch<AccountResponse[]>('/api/account/list')
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

    const isEditing = showEditArea

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingAccount) {
            return formData.name.trim() !== '' && formData.email.trim() !== ''
        }
        return (
            formData.name.trim() !== originalFormData.name.trim() ||
            formData.email.trim() !== originalFormData.email.trim()
        )
    }

    // Handlers
    const handleCreateClick = () => {
        setFormData({
            name: '',
            email: '',
            role: 'account',
        })
        setOriginalFormData({
            name: '',
            email: '',
            role: 'account',
        })
        setEditingAccount(null)
        setSendInvite(false)
        setShowEditArea(true)
        setError(null)
        setEmailMessage(null)
    }

    const handleEditClick = (account: AccountResponse) => {
        setEditingAccount(account)
        setFormData({
            name: account.name,
            email: account.email,
            role: account.role,
        })
        setOriginalFormData({
            name: account.name,
            email: account.email,
            role: account.role,
        })
        setSendInvite(false)
        setShowEditArea(true)
        setError(null)
        setEmailMessage(null)
    }

    const handleCancel = () => {
        setFormData({
            name: '',
            email: '',
            role: 'account',
        })
        setOriginalFormData({
            name: '',
            email: '',
            role: 'account',
        })
        setEditingAccount(null)
        setSendInvite(false)
        setShowEditArea(false)
        setSelectedAccounts(new Set())
        setError(null)
        setEmailMessage(null)
    }

    const handleSave = async () => {
        if (!formData.name.trim()) {
            setError('Nome é obrigatório')
            setEmailMessage(null)
            return
        }

        if (!formData.email.trim()) {
            setError('Email é obrigatório')
            setEmailMessage(null)
            return
        }

        try {
            setSubmitting(true)
            setError(null)
            setEmailMessage(null)

            if (editingAccount) {
                // Editar account existente
                const updateData = {
                    name: formData.name.trim(),
                    email: formData.email.trim(),
                }

                const savedAccount = await protectedFetch<AccountResponse>(`/api/account/${editingAccount.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                })

                // Se o checkbox "Enviar convite" estiver marcado, enviar email de convite
                if (sendInvite && savedAccount) {
                    // Buscar membership_id do account no tenant atual
                    const memberships = await protectedFetch<{ items: any[] }>('/api/membership/list')
                    const membership = memberships.items.find((m: any) => m.account_id === savedAccount.id)

                    if (membership) {
                        console.log(
                            `[INVITE-UI] Iniciando envio de convite para membership ID=${membership.id} (${formData.email})`
                        )
                        try {
                            await protectedFetch(`/api/membership/${membership.id}/invite`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                            })
                            // Definir mensagem de sucesso no ActionBar
                            const successMsg = `E-mail de convite foi enviado para ${formData.name} (${formData.email})`
                            console.log('[EMAIL-MESSAGE] Definindo mensagem de sucesso:', successMsg)
                            setEmailMessage(successMsg)
                            setEmailMessageType('success')
                        } catch (inviteErr) {
                            const errorMsg = inviteErr instanceof Error ? inviteErr.message : 'Erro desconhecido'
                            console.error(
                                `[INVITE-UI] ❌ FALHA - Erro ao enviar convite para membership ID=${membership.id}:`,
                                inviteErr
                            )
                            // Definir mensagem de erro no ActionBar
                            setEmailMessage(`E-mail de convite não foi enviado para ${formData.name} (${formData.email}). ${errorMsg}`)
                            setEmailMessageType('error')
                        }
                    }
                }
            } else {
                // Criar novo account
                const accountData = {
                    name: formData.name.trim(),
                    email: formData.email.trim(),
                }

                const savedAccount = await protectedFetch<AccountResponse>('/api/account', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(accountData),
                })

                // Criar membership para o account no tenant atual
                if (!tenant) {
                    setError('Tenant não encontrado')
                    setEmailMessage(null)
                    return
                }

                const membershipData = {
                    account_id: savedAccount.id,
                    role: formData.role,
                    status: 'ACTIVE', // Sempre criar como ACTIVE, o invite atualiza para PENDING
                }

                const savedMembership = await protectedFetch<{ id: number; account_id: number; status: string; role: string }>(
                    '/api/membership',
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(membershipData),
                    }
                )

                // Se o checkbox "Enviar convite" estiver marcado, enviar email de convite (que atualiza status para PENDING)
                if (sendInvite && savedMembership) {
                    console.log(
                        `[INVITE-UI] Iniciando envio de convite para membership ID=${savedMembership.id} (${formData.email})`
                    )
                    try {
                        await protectedFetch(`/api/membership/${savedMembership.id}/invite`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        })
                        // Definir mensagem de sucesso no ActionBar
                        const successMsg = `E-mail de convite foi enviado para ${formData.name} (${formData.email})`
                        console.log('[EMAIL-MESSAGE] Definindo mensagem de sucesso:', successMsg)
                        setEmailMessage(successMsg)
                        setEmailMessageType('success')
                    } catch (inviteErr) {
                        const errorMsg = inviteErr instanceof Error ? inviteErr.message : 'Erro desconhecido'
                        console.error(
                            `[INVITE-UI] ❌ FALHA - Erro ao enviar convite para membership ID=${savedMembership.id}:`,
                            inviteErr
                        )
                        // Definir mensagem de erro no ActionBar
                        setEmailMessage(`E-mail de convite não foi enviado para ${formData.name} (${formData.email}). ${errorMsg}`)
                        setEmailMessageType('error')
                    }
                }
            }

            // Recarregar lista e limpar formulário
            await loadAccounts()

            setFormData({
                name: '',
                email: '',
                role: 'account',
            })
            setOriginalFormData({
                name: '',
                email: '',
                role: 'account',
            })
            setEditingAccount(null)
            setSendInvite(false)
            setShowEditArea(false)
            // Mensagem de email permanece visível até o usuário fechar o formulário ou fazer nova ação
        } catch (err) {
            const message = err instanceof Error ? err.message : (editingAccount ? 'Erro ao atualizar conta' : 'Erro ao criar conta')
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao salvar conta:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de account para exclusão
    const toggleAccountSelection = (accountId: number) => {
        setSelectedAccounts((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(accountId)) {
                newSet.delete(accountId)
            } else {
                newSet.add(accountId)
            }
            return newSet
        })
    }

    // Excluir accounts selecionados
    const handleDeleteSelected = async () => {
        if (selectedAccounts.size === 0) return

        if (!confirm(`Tem certeza que deseja remover ${selectedAccounts.size} conta(s)?`)) {
            return
        }

        try {
            setDeleting(true)
            setError(null)

            const deletePromises = Array.from(selectedAccounts).map(async (accountId) => {
                try {
                    await protectedFetch(`/api/account/${accountId}`, {
                        method: 'DELETE',
                    })
                    return { success: true, accountId }
                } catch (err) {
                    return { success: false, accountId, error: err }
                }
            })

            const results = await Promise.allSettled(deletePromises)
            const failed = results.filter((r) => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success))

            if (failed.length > 0) {
                throw new Error(`${failed.length} conta(s) não puderam ser removidas`)
            }

            // Recarregar lista
            await loadAccounts()
            setSelectedAccounts(new Set())
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao remover contas'
            setError(message)
            console.error('Erro ao remover contas:', err)
        } finally {
            setDeleting(false)
        }
    }

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
                editContent={
                    isEditing ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">
                                {editingAccount ? 'Editar Conta' : 'Convidar novo membro'}
                            </h2>
                            <div className="space-y-4">
                                <FormFieldGrid>
                                    <FormField label="Nome" required>
                                        <input
                                            type="text"
                                            id="name"
                                            value={formData.name}
                                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            required
                                            disabled={submitting}
                                        />
                                    </FormField>
                                    <FormField
                                        label="Email"
                                        required
                                        helperText={editingAccount ? 'Observe que este é o e-mail de acesso ao sistema, portanto, não deve ser modificado.' : undefined}
                                    >
                                        <input
                                            type="email"
                                            id="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            required
                                            disabled={submitting || !!editingAccount}
                                        />
                                    </FormField>
                                </FormFieldGrid>
                                {!editingAccount && (
                                    <FormField label="Função" required>
                                        <select
                                            id="role"
                                            value={formData.role}
                                            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            required
                                            disabled={submitting}
                                        >
                                            <option value="account">Conta</option>
                                            <option value="admin">Administrador</option>
                                        </select>
                                    </FormField>
                                )}
                                <FormCheckbox
                                    id="sendInvite"
                                    label="Enviar convite"
                                    checked={sendInvite}
                                    onChange={setSendInvite}
                                    disabled={submitting}
                                />
                            </div>
                        </div>
                    ) : undefined
                }
                createCard={
                    <CreateCard
                        label="Convidar novo membro"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
            >
                {accounts.map((account) => {
                    const isSelected = selectedAccounts.has(account.id)
                    return (
                        <div
                            key={account.id}
                            className={getCardContainerClasses(isSelected)}
                        >
                            <div className="mb-3">
                                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-blue-50">
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
                                            className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'}`}
                                            title={account.name}
                                        >
                                            {account.name}
                                        </h3>
                                        <p
                                            className={`text-xs text-center px-2 mt-1 ${isSelected ? 'text-red-800' : 'text-gray-600'}`}
                                            title={account.email}
                                        >
                                            {account.email}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <CardFooter
                                isSelected={isSelected}
                                date={account.created_at}
                                settings={settings}
                                onToggleSelection={(e) => {
                                    e.stopPropagation()
                                    toggleAccountSelection(account.id)
                                }}
                                onEdit={() => handleEditClick(account)}
                                disabled={deleting}
                                deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                editTitle="Editar conta"
                            />
                        </div>
                    )
                })}
            </CardPanel>

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <ActionBarSpacer />

            {/* Barra inferior fixa com mensagens de erro */}
            <ActionBar
                error={(() => {
                    // Se houver mensagem de email, não mostrar erro genérico
                    // A mensagem de email será exibida via prop 'message'
                    if (emailMessage) {
                        console.log('[ACTIONBAR] Mensagem de email presente, não mostrando erro genérico')
                        return undefined
                    }
                    const hasButtons = isEditing || selectedAccounts.size > 0
                    return hasButtons ? error : undefined
                })()}
                message={(() => {
                    // Priorizar mensagem de email se houver
                    if (emailMessage) {
                        return emailMessage
                    }
                    // Se não há botões mas há erro, mostrar via message
                    const hasButtons = isEditing || selectedAccounts.size > 0
                    if (!hasButtons && error) {
                        return error
                    }
                    return undefined
                })()}
                messageType={(() => {
                    // Priorizar tipo de mensagem de email se houver
                    if (emailMessage) {
                        return emailMessageType
                    }
                    // Se não há botões mas há erro, usar tipo error
                    const hasButtons = isEditing || selectedAccounts.size > 0
                    if (!hasButtons && error) {
                        return 'error' as const
                    }
                    return undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    if (isEditing || selectedAccounts.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    if (selectedAccounts.size > 0) {
                        buttons.push({
                            label: 'Remover',
                            onClick: handleDeleteSelected,
                            variant: 'primary' as const,
                            disabled: deleting || submitting,
                            loading: deleting,
                        })
                    }
                    // Botão Salvar aparece se houver mudanças OU se o checkbox "Enviar convite" estiver marcado
                    if (isEditing && (hasChanges() || sendInvite)) {
                        buttons.push({
                            label: submitting ? 'Salvando...' : 'Salvar',
                            onClick: handleSave,
                            variant: 'primary' as const,
                            disabled: submitting,
                            loading: submitting,
                        })
                    }
                    return buttons
                })()}
            />
        </>
    )
}
