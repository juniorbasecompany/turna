'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { protectedFetch, extractErrorMessage } from '@/lib/api'
import { getCardContainerClasses } from '@/lib/cardStyles'
import {
    MembershipListResponse,
    MembershipResponse,
    MembershipUpdateRequest,
    MembershipCreateRequest,
} from '@/types/api'
import { useEffect, useState } from 'react'

export default function MembershipPage() {
    const { settings } = useTenantSettings()
    const [memberships, setMemberships] = useState<MembershipResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')
    const [editingMembership, setEditingMembership] = useState<MembershipResponse | null>(null)
    const [formData, setFormData] = useState({
        role: 'account',
        status: 'ACTIVE',
        name: '',
        email: '',
    })
    const [originalFormData, setOriginalFormData] = useState({
        role: 'account',
        status: 'ACTIVE',
        name: '',
        email: '',
    })
    const [sendInvite, setSendInvite] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [selectedMemberships, setSelectedMemberships] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [filters, setFilters] = useState({
        status: null as string | null,
        role: null as string | null,
    })
    const [pagination, setPagination] = useState({ limit: 20, offset: 0 })
    const [total, setTotal] = useState(0)
    const [showEditArea, setShowEditArea] = useState(false)

    // Carregar lista de memberships
    const loadMemberships = async () => {
        try {
            setLoading(true)
            setError(null)

            const params = new URLSearchParams()
            if (filters.status) params.append('status', filters.status)
            if (filters.role) params.append('role', filters.role)
            params.append('limit', String(pagination.limit))
            params.append('offset', String(pagination.offset))

            const data = await protectedFetch<MembershipListResponse>(`/api/membership/list?${params.toString()}`)
            setMemberships(data.items)
            setTotal(data.total)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar associações'
            setError(message)
            console.error('Erro ao carregar associações:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadMemberships()
    }, [filters, pagination])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingMembership) {
            // Para criação, verificar se há dados preenchidos
            return formData.email.trim() !== '' || formData.name.trim() !== ''
        }
        return (
            formData.role !== originalFormData.role ||
            formData.status !== originalFormData.status ||
            formData.name !== originalFormData.name ||
            formData.email !== originalFormData.email
        )
    }

    const isEditing = showEditArea

    // Handlers
    const handleCreateClick = () => {
        setFormData({
            role: 'account',
            status: 'PENDING',
            name: '',
            email: '',
        })
        setOriginalFormData({
            role: 'account',
            status: 'PENDING',
            name: '',
            email: '',
        })
        setEditingMembership(null)
        setSendInvite(false)
        setShowEditArea(true)
        setError(null)
    }

    const handleEditClick = (membership: MembershipResponse) => {
        setEditingMembership(membership)
        setFormData({
            role: membership.role,
            status: membership.status,
            name: membership.membership_name || '',
            email: membership.membership_email || '',
        })
        setOriginalFormData({
            role: membership.role,
            status: membership.status,
            name: membership.membership_name || '',
            email: membership.membership_email || '',
        })
        setShowEditArea(true)
        setError(null)
    }

    const handleCancel = () => {
        setEditingMembership(null)
        setFormData({
            role: 'account',
            status: 'ACTIVE',
            name: '',
            email: '',
        })
        setOriginalFormData({
            role: 'account',
            status: 'ACTIVE',
            name: '',
            email: '',
        })
        setSendInvite(false)
        setShowEditArea(false)
        setError(null)
        setEmailMessage(null)
    }

    const handleCreate = async () => {
        // Validar que email está preenchido
        if (!formData.email || formData.email.trim() === '') {
            setError('E-mail é obrigatório')
            return
        }

        try {
            setSubmitting(true)
            setError(null)
            setEmailMessage(null)

            const createData: MembershipCreateRequest = {
                email: formData.email.trim(),
                name: formData.name.trim() || null,
                role: formData.role,
                status: formData.status,
            }

            const savedMembership = await protectedFetch<MembershipResponse>(`/api/membership`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(createData),
            })

            // Se o checkbox "Enviar convite" estiver marcado, enviar convite
            if (sendInvite && savedMembership) {
                await sendInviteEmail(savedMembership)
            }

            // Recarregar lista e limpar formulário
            await loadMemberships()
            handleCancel()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao criar membership'
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao criar membership:', err)
        } finally {
            setSubmitting(false)
        }
    }

    const sendInviteEmail = async (membership: MembershipResponse) => {
        console.log(
            `[INVITE-UI] Iniciando envio de convite para membership ID=${membership.id} (${membership.membership_name || membership.membership_email})`
        )
        try {
            await protectedFetch(`/api/membership/${membership.id}/invite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            const successMsg = `E-mail de convite foi enviado para ${membership.membership_name || membership.membership_email}`
            console.log('[EMAIL-MESSAGE] Definindo mensagem de sucesso:', successMsg)
            setEmailMessage(successMsg)
            setEmailMessageType('success')
        } catch (inviteErr) {
            const errorMsg = inviteErr instanceof Error ? inviteErr.message : 'Erro desconhecido'
            console.error(
                `[INVITE-UI] ❌ FALHA - Erro ao enviar convite para membership ID=${membership.id}:`,
                inviteErr
            )
            setEmailMessage(`E-mail de convite não foi enviado para ${membership.membership_name || membership.membership_email}. ${errorMsg}`)
            setEmailMessageType('error')
        }
    }

    const handleSave = async () => {
        if (!editingMembership) return

        try {
            setSubmitting(true)
            setError(null)
            setEmailMessage(null)

            const updateData: MembershipUpdateRequest = {
                role: formData.role,
                status: formData.status,
                name: formData.name.trim() || null,
                email: formData.email.trim() || null,
            }

            const savedMembership = await protectedFetch<MembershipResponse>(`/api/membership/${editingMembership.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData),
            })

            // Se o checkbox "Enviar convite" estiver marcado, enviar convite
            if (sendInvite && savedMembership) {
                await sendInviteEmail(savedMembership)
            }

            // Recarregar lista e limpar formulário
            await loadMemberships()
            handleCancel()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar membership'
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao salvar membership:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de membership para exclusão
    const toggleMembershipSelection = (membershipId: number) => {
        setSelectedMemberships((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(membershipId)) {
                newSet.delete(membershipId)
            } else {
                newSet.add(membershipId)
            }
            return newSet
        })
    }

    // Excluir memberships selecionados
    const handleDeleteSelected = async () => {
        if (selectedMemberships.size === 0) return

        if (!confirm(`Tem certeza que deseja remover ${selectedMemberships.size} associação(ões)?`)) {
            return
        }

        try {
            setDeleting(true)
            setError(null)

            const deletePromises = Array.from(selectedMemberships).map(async (membershipId) => {
                try {
                    await protectedFetch(`/api/membership/${membershipId}`, {
                        method: 'DELETE',
                    })
                    return { success: true, membershipId }
                } catch (err) {
                    return { success: false, membershipId, error: err }
                }
            })

            const results = await Promise.allSettled(deletePromises)
            const failed = results.filter((r) => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success))

            if (failed.length > 0) {
                throw new Error(`${failed.length} associação(ões) não puderam ser removidas`)
            }

            // Recarregar lista
            await loadMemberships()
            setSelectedMemberships(new Set())
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao remover associações'
            setError(message)
            console.error('Erro ao remover associações:', err)
        } finally {
            setDeleting(false)
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'ACTIVE':
                return 'bg-green-100 text-green-800'
            case 'PENDING':
                return 'bg-yellow-100 text-yellow-800'
            case 'REJECTED':
                return 'bg-red-100 text-red-800'
            case 'REMOVED':
                return 'bg-gray-100 text-gray-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    const getRoleLabel = (role: string) => {
        return role === 'admin' ? 'Administrador' : 'Conta'
    }

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'ACTIVE':
                return 'Ativo'
            case 'PENDING':
                return 'Pendente'
            case 'REJECTED':
                return 'Rejeitado'
            case 'REMOVED':
                return 'Removido'
            default:
                return status
        }
    }

    return (
        <>
            <CardPanel
                title="Associações"
                loading={loading}
                error={undefined}
                editContent={
                    isEditing ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">
                                {editingMembership ? 'Editar Associação' : 'Criar Associação'}
                            </h2>
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                                        E-mail <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="email"
                                        type="email"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="E-mail público na clínica"
                                        required={!editingMembership}
                                        disabled={submitting}
                                    />
                                </div>
                                <div>
                                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                                        Nome
                                    </label>
                                    <input
                                        id="name"
                                        type="text"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="Nome público na clínica"
                                        disabled={submitting}
                                    />
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div>
                                        <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-2">
                                            Função <span className="text-red-500">*</span>
                                        </label>
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
                                    </div>
                                    <div>
                                        <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                                            Status <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            id="status"
                                            value={formData.status}
                                            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            required
                                            disabled={submitting}
                                        >
                                            <option value="PENDING">Pendente</option>
                                            <option value="ACTIVE">Ativo</option>
                                            <option value="REJECTED">Rejeitado</option>
                                            <option value="REMOVED">Removido</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <div className="flex items-center">
                                        <input
                                            type="checkbox"
                                            id="sendInvite"
                                            checked={sendInvite}
                                            onChange={(e) => setSendInvite(e.target.checked)}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            disabled={submitting}
                                        />
                                        <label htmlFor="sendInvite" className="ml-2 block text-sm text-gray-700">
                                            Enviar convite
                                        </label>
                                    </div>
                                </div>
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
                filterContent={
                    !isEditing ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="filter-status" className="block text-sm font-medium text-gray-700 mb-2">
                                        Status
                                    </label>
                                    <select
                                        id="filter-status"
                                        value={filters.status || ''}
                                        onChange={(e) => {
                                            setFilters({
                                                ...filters,
                                                status: e.target.value === '' ? null : e.target.value,
                                            })
                                            setPagination({ ...pagination, offset: 0 })
                                        }}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="">Todos</option>
                                        <option value="PENDING">Pendente</option>
                                        <option value="ACTIVE">Ativo</option>
                                        <option value="REJECTED">Rejeitado</option>
                                        <option value="REMOVED">Removido</option>
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="filter-role" className="block text-sm font-medium text-gray-700 mb-2">
                                        Função
                                    </label>
                                    <select
                                        id="filter-role"
                                        value={filters.role || ''}
                                        onChange={(e) => {
                                            setFilters({
                                                ...filters,
                                                role: e.target.value === '' ? null : e.target.value,
                                            })
                                            setPagination({ ...pagination, offset: 0 })
                                        }}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="">Todas</option>
                                        <option value="admin">Administrador</option>
                                        <option value="account">Conta</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    ) : undefined
                }
            >
                {memberships.map((membership) => {
                    const isSelected = selectedMemberships.has(membership.id)
                    return (
                        <div
                            key={membership.id}
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
                                                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                                                />
                                            </svg>
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                }`}
                                            title={membership.membership_name || membership.membership_email || 'Não disponível'}
                                        >
                                            {membership.membership_name || membership.membership_email || 'Não disponível'}
                                        </h3>
                                        <div className="mt-2 flex flex-wrap gap-1 justify-center px-2">
                                            <span className={`text-xs px-2 py-1 rounded ${getStatusColor(membership.status)}`}>
                                                {getStatusLabel(membership.status)}
                                            </span>
                                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                                {getRoleLabel(membership.role)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <CardFooter
                                isSelected={isSelected}
                                date={membership.created_at}
                                settings={settings}
                                onToggleSelection={(e) => {
                                    e.stopPropagation()
                                    toggleMembershipSelection(membership.id)
                                }}
                                onEdit={() => handleEditClick(membership)}
                                disabled={deleting}
                                deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                editTitle="Editar associação"
                            />
                        </div>
                    )
                })}
            </CardPanel>

            <ActionBarSpacer />

            <ActionBar
                pagination={
                    total > 0 ? (
                        <Pagination
                            offset={pagination.offset}
                            limit={pagination.limit}
                            total={total}
                            onFirst={() => setPagination({ ...pagination, offset: 0 })}
                            onPrevious={() => setPagination({ ...pagination, offset: Math.max(0, pagination.offset - pagination.limit) })}
                            onNext={() => setPagination({ ...pagination, offset: pagination.offset + pagination.limit })}
                            onLast={() => setPagination({ ...pagination, offset: Math.floor((total - 1) / pagination.limit) * pagination.limit })}
                            disabled={loading}
                        />
                    ) : undefined
                }
                error={(() => {
                    // Se houver mensagem de email, não mostrar erro genérico
                    // A mensagem de email será exibida via prop 'message'
                    if (emailMessage) {
                        console.log('[ACTIONBAR] Mensagem de email presente, não mostrando erro genérico')
                        return undefined
                    }
                    const hasButtons = isEditing || selectedMemberships.size > 0
                    return hasButtons ? error : undefined
                })()}
                message={(() => {
                    // Priorizar mensagem de email se houver
                    if (emailMessage) {
                        return emailMessage
                    }
                    // Se não há botões mas há erro, mostrar via message
                    const hasButtons = isEditing || selectedMemberships.size > 0
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
                    const hasButtons = isEditing || selectedMemberships.size > 0
                    if (!hasButtons && error) {
                        return 'error' as const
                    }
                    return undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    if (isEditing || selectedMemberships.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    if (selectedMemberships.size > 0) {
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
                            label: submitting ? (editingMembership ? 'Salvando...' : 'Criando...') : (editingMembership ? 'Salvar' : 'Criar'),
                            onClick: editingMembership ? handleSave : handleCreate,
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
