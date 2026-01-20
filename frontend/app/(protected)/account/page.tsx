'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { Pagination } from '@/components/Pagination'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { FormCheckbox } from '@/components/FormCheckbox'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { protectedFetch } from '@/lib/api'
import { getCardContainerClasses } from '@/lib/cardStyles'
import { AccountResponse } from '@/types/api'
import { useEntityPage } from '@/hooks/useEntityPage'
import { useState, useCallback, useMemo } from 'react'
import { getActionBarErrorProps } from '@/lib/entityUtils'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'

type AccountFormData = {
    name: string
    email: string
    role: string
}

export default function AccountPage() {
    const { tenant, settings } = useTenantSettings()
    const [sendInvite, setSendInvite] = useState(false)
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')

    const initialFormData: AccountFormData = {
        name: '',
        email: '',
        role: 'account',
    }

    const {
        items: accounts,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingAccount,
        isEditing,
        hasChanges,
        handleCreateClick: baseHandleCreateClick,
        handleEditClick: baseHandleEditClick,
        handleCancel: baseHandleCancel,
        selectedItems: selectedAccounts,
        toggleSelection: toggleAccountSelection,
        selectedCount: selectedAccountsCount,
        pagination,
        total,
        paginationHandlers,
        handleDeleteSelected: baseHandleDeleteSelected,
        loadItems,
    } = useEntityPage<AccountFormData, AccountResponse, { name: string; email: string }, { name: string; email: string }>({
        endpoint: '/api/account',
        entityName: 'conta',
        initialFormData,
        isEmptyCheck: (data) => {
            return data.name.trim() === '' && data.email.trim() === ''
        },
        mapEntityToFormData: (account) => ({
            name: account.name,
            email: account.email,
            role: account.role,
        }),
        mapFormDataToCreateRequest: (formData) => ({
            name: formData.name.trim(),
            email: formData.email.trim(),
        }),
        mapFormDataToUpdateRequest: (formData) => ({
            name: formData.name.trim(),
            email: formData.email.trim(),
        }),
        validateFormData: (formData) => {
            if (!formData.name.trim()) {
                return 'Nome é obrigatório'
            }
            if (!formData.email.trim()) {
                return 'Email é obrigatório'
            }
            return null
        },
    })

    // Handlers customizados para preservar lógica específica
    const handleCreateClick = useCallback(() => {
        baseHandleCreateClick()
        setSendInvite(false)
        setEmailMessage(null)
    }, [baseHandleCreateClick])

    const handleEditClick = useCallback(
        (account: AccountResponse) => {
            baseHandleEditClick(account)
            setSendInvite(false)
            setEmailMessage(null)
        },
        [baseHandleEditClick]
    )

    const handleCancel = useCallback(() => {
        baseHandleCancel()
        setSendInvite(false)
        setEmailMessage(null)
    }, [baseHandleCancel])

    // Handler de salvar customizado com lógica de envio de convite
    const handleSave = useCallback(async () => {
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
            setError(null)
            setEmailMessage(null)

            let savedAccount: AccountResponse | null = null

            if (editingAccount) {
                // Editar account existente
                const updateData = {
                    name: formData.name.trim(),
                    email: formData.email.trim(),
                }

                savedAccount = await protectedFetch<AccountResponse>(`/api/account/${editingAccount.id}`, {
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
                    const accountId = savedAccount.id
                    const membership = memberships.items.find((m: any) => m.account_id === accountId)

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

                savedAccount = await protectedFetch<AccountResponse>('/api/account', {
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
                    status: 'ACTIVE',
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

                // Se o checkbox "Enviar convite" estiver marcado, enviar email de convite
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
                        setEmailMessage(`E-mail de convite não foi enviado para ${formData.name} (${formData.email}). ${errorMsg}`)
                        setEmailMessageType('error')
                    }
                }
            }

            // Recarregar lista e limpar formulário
            await loadItems()
            baseHandleCancel()
            setSendInvite(false)
        } catch (err) {
            const message = err instanceof Error ? err.message : (editingAccount ? 'Erro ao atualizar conta' : 'Erro ao criar conta')
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao salvar conta:', err)
        }
    }, [
        formData,
        editingAccount,
        sendInvite,
        tenant,
        setError,
        loadItems,
        baseHandleCancel,
    ])

    // Handler de exclusão customizado com confirm
    const handleDeleteSelectedWithConfirm = useCallback(async () => {
        if (selectedAccountsCount === 0) return

        if (!confirm(`Tem certeza que deseja remover ${selectedAccountsCount} conta(s)?`)) {
            return
        }

        await baseHandleDeleteSelected()
    }, [selectedAccountsCount, baseHandleDeleteSelected])

    // Botões do ActionBar customizados
    const actionBarButtons = useActionBarButtons({
        isEditing,
        selectedCount: selectedAccountsCount,
        hasChanges: hasChanges() || sendInvite, // Inclui sendInvite na verificação
        submitting,
        deleting,
        onCancel: handleCancel,
        onDelete: handleDeleteSelectedWithConfirm,
        onSave: handleSave,
        deleteLabel: 'Remover',
    })

    // Props de erro do ActionBar com suporte a emailMessage
    const actionBarErrorProps = getActionBarErrorProps(error, isEditing, selectedAccountsCount, emailMessage, emailMessageType)

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
                pagination={
                    total > 0 ? (
                        <Pagination
                            offset={pagination.offset}
                            limit={pagination.limit}
                            total={total}
                            onFirst={paginationHandlers.onFirst}
                            onPrevious={paginationHandlers.onPrevious}
                            onNext={paginationHandlers.onNext}
                            onLast={paginationHandlers.onLast}
                            disabled={loading}
                        />
                    ) : undefined
                }
                error={actionBarErrorProps.error}
                message={actionBarErrorProps.message}
                messageType={actionBarErrorProps.messageType}
                buttons={actionBarButtons}
            />
        </>
    )
}
