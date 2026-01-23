'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterButtons, FilterOption } from '@/components/FilterButtons'
import { FilterPanel } from '@/components/FilterPanel'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { usePagination } from '@/hooks/usePagination'
import { protectedFetch } from '@/lib/api'
import { getActionBarErrorProps } from '@/lib/entityUtils'
import {
    MemberCreateRequest,
    MemberListResponse,
    MemberResponse,
    MemberUpdateRequest,
} from '@/types/api'
import { useEffect, useMemo, useState } from 'react'

export default function MemberPage() {
    const { settings } = useTenantSettings()
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')
    const [editingMember, setEditingMember] = useState<MemberResponse | null>(null)
    const [formData, setFormData] = useState({
        role: 'account',
        status: 'ACTIVE',
        name: '',
        email: '',
        attribute: '{}',
    })
    const [originalFormData, setOriginalFormData] = useState({
        role: 'account',
        status: 'ACTIVE',
        name: '',
        email: '',
        attribute: '{}',
    })
    const [jsonError, setJsonError] = useState<string | null>(null)
    const [sendInvite, setSendInvite] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [selectedMembers, setSelectedMembers] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    // Filtros usando hook reutilizável
    const statusFilters = useEntityFilters({
        allFilters: ['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED'],
        initialFilters: new Set(['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED']),
        onFilterChange: () => {
            setPagination((prev) => ({ ...prev, offset: 0 }))
        },
    })

    const roleFilters = useEntityFilters({
        allFilters: ['account', 'admin'],
        initialFilters: new Set(['account', 'admin']),
        onFilterChange: () => {
            setPagination((prev) => ({ ...prev, offset: 0 }))
        },
    })
    const { pagination, setPagination, total, setTotal, onFirst, onPrevious, onNext, onLast } = usePagination(20)
    const [showEditArea, setShowEditArea] = useState(false)
    const [allMembers, setAllMembers] = useState<MemberResponse[]>([])

    // Carregar lista de members (faz múltiplas requisições para carregar todos)
    const loadMembers = async () => {
        try {
            setLoading(true)
            setError(null)

            const allItems: MemberResponse[] = []
            const limit = 100 // Limite máximo do backend
            let offset = 0
            let hasMore = true

            // Fazer requisições paginadas até carregar todos os dados
            while (hasMore) {
                const params = new URLSearchParams()
                params.append('limit', String(limit))
                params.append('offset', String(offset))

                const data = await protectedFetch<MemberListResponse>(`/api/member/list?${params.toString()}`)
                allItems.push(...data.items)

                // Verificar se há mais dados para carregar
                if (data.items.length < limit || allItems.length >= data.total) {
                    hasMore = false
                } else {
                    offset += limit
                }
            }

            setAllMembers(allItems)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar associados'
            setError(message)
            console.error('Erro ao carregar associados:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadMembers()
    }, [])

    // Filtrar members no frontend
    const members = useMemo(() => {
        return allMembers.filter((member) => {
            const statusMatch = statusFilters.selectedFilters.has(member.status)
            const roleMatch = roleFilters.selectedFilters.has(member.role)
            return statusMatch && roleMatch
        })
    }, [allMembers, statusFilters.selectedFilters, roleFilters.selectedFilters])

    // Aplicar paginação
    const paginatedMembers = useMemo(() => {
        const start = pagination.offset
        const end = start + pagination.limit
        return members.slice(start, end)
    }, [members, pagination])

    // Atualizar total baseado nos filtros
    useEffect(() => {
        setTotal(members.length)
    }, [members.length, setTotal])

    // Validar JSON
    const validateJson = (jsonString: string): { valid: boolean; error?: string; parsed?: Record<string, unknown> } => {
        try {
            if (!jsonString.trim()) {
                return { valid: false, error: 'JSON não pode estar vazio' }
            }
            const parsed = JSON.parse(jsonString)
            if (typeof parsed !== 'object' || Array.isArray(parsed)) {
                return { valid: false, error: 'JSON deve ser um objeto' }
            }
            return { valid: true, parsed }
        } catch (e) {
            return { valid: false, error: `JSON inválido: ${e instanceof Error ? e.message : 'erro desconhecido'}` }
        }
    }

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingMember) {
            // Para criação, verificar se há dados preenchidos
            return formData.email.trim() !== '' || formData.name.trim() !== ''
        }
        return (
            formData.role !== originalFormData.role ||
            formData.status !== originalFormData.status ||
            formData.name !== originalFormData.name ||
            formData.email !== originalFormData.email ||
            formData.attribute !== originalFormData.attribute
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
            attribute: '{}',
        })
        setOriginalFormData({
            role: 'account',
            status: 'PENDING',
            name: '',
            email: '',
            attribute: '{}',
        })
        setEditingMember(null)
        setSendInvite(false)
        setShowEditArea(true)
        setError(null)
        setJsonError(null)
    }

    const handleEditClick = (member: MemberResponse) => {
        setEditingMember(member)
        const attributeJson = JSON.stringify(member.attribute || {}, null, 2)
        setFormData({
            role: member.role,
            status: member.status,
            name: member.member_name || '',
            email: member.member_email || '',
            attribute: attributeJson,
        })
        setOriginalFormData({
            role: member.role,
            status: member.status,
            name: member.member_name || '',
            email: member.member_email || '',
            attribute: attributeJson,
        })
        setShowEditArea(true)
        setError(null)
        setJsonError(null)
    }

    const handleCancel = () => {
        setEditingMember(null)
        setFormData({
            role: 'account',
            status: 'ACTIVE',
            name: '',
            email: '',
            attribute: '{}',
        })
        setOriginalFormData({
            role: 'account',
            status: 'ACTIVE',
            name: '',
            email: '',
            attribute: '{}',
        })
        setSendInvite(false)
        setShowEditArea(false)
        setError(null)
        setEmailMessage(null)
        setJsonError(null)
    }

    const handleCreate = async () => {
        // Validar que email está preenchido
        if (!formData.email || formData.email.trim() === '') {
            setError('E-mail é obrigatório')
            return
        }

        // Validar JSON
        const jsonValidation = validateJson(formData.attribute)
        if (!jsonValidation.valid) {
            setError(jsonValidation.error || 'JSON inválido')
            setJsonError(jsonValidation.error || 'JSON inválido')
            return
        }

        try {
            setSubmitting(true)
            setError(null)
            setEmailMessage(null)
            setJsonError(null)

            const createData: MemberCreateRequest = {
                email: formData.email.trim(),
                name: formData.name.trim() || null,
                role: formData.role,
                status: formData.status,
                attribute: jsonValidation.parsed || {},
            }

            const savedMember = await protectedFetch<MemberResponse>(`/api/member`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(createData),
            })

            // Se o checkbox "Enviar convite" estiver marcado, enviar convite
            if (sendInvite && savedMember) {
                await sendInviteEmail(savedMember)
            }

            // Recarregar lista e limpar formulário
            await loadMembers()
            handleCancel()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao criar member'
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao criar member:', err)
        } finally {
            setSubmitting(false)
        }
    }

    const sendInviteEmail = async (member: MemberResponse) => {
        try {
            await protectedFetch(`/api/member/${member.id}/invite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            const successMsg = `E-mail de convite foi enviado para ${member.member_name || member.member_email}`
            setEmailMessage(successMsg)
            setEmailMessageType('success')
        } catch (inviteErr) {
            const errorMsg = inviteErr instanceof Error ? inviteErr.message : 'Erro desconhecido'
            setEmailMessage(`E-mail de convite não foi enviado para ${member.member_name || member.member_email}. ${errorMsg}`)
            setEmailMessageType('error')
        }
    }

    const handleSave = async () => {
        if (!editingMember) return

        // Validar JSON
        const jsonValidation = validateJson(formData.attribute)
        if (!jsonValidation.valid) {
            setError(jsonValidation.error || 'JSON inválido')
            setJsonError(jsonValidation.error || 'JSON inválido')
            return
        }

        try {
            setSubmitting(true)
            setError(null)
            setEmailMessage(null)
            setJsonError(null)

            const updateData: MemberUpdateRequest = {
                role: formData.role,
                status: formData.status,
                name: formData.name.trim() || null,
                email: formData.email.trim() || null,
                attribute: jsonValidation.parsed || {},
            }

            const savedMember = await protectedFetch<MemberResponse>(`/api/member/${editingMember.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData),
            })

            // Se o checkbox "Enviar convite" estiver marcado, enviar convite
            if (sendInvite && savedMember) {
                await sendInviteEmail(savedMember)
            }

            // Recarregar lista e limpar formulário
            await loadMembers()
            handleCancel()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar member'
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao salvar member:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de member para exclusão
    const toggleMemberSelection = (memberId: number) => {
        setSelectedMembers((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(memberId)) {
                newSet.delete(memberId)
            } else {
                newSet.add(memberId)
            }
            return newSet
        })
    }

    // Excluir members selecionados
    const handleDeleteSelected = async () => {
        if (selectedMembers.size === 0) return

        try {
            setDeleting(true)
            setError(null)

            const deletePromises = Array.from(selectedMembers).map(async (memberId) => {
                try {
                    await protectedFetch(`/api/member/${memberId}`, {
                        method: 'DELETE',
                    })
                    return { success: true, memberId }
                } catch (err) {
                    return { success: false, memberId, error: err }
                }
            })

            const results = await Promise.allSettled(deletePromises)
            const failed = results.filter((r) => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success))

            if (failed.length > 0) {
                throw new Error(`${failed.length} associação(ões) não puderam ser removidas`)
            }

            // Recarregar lista
            await loadMembers()
            setSelectedMembers(new Set())
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao remover associados'
            setError(message)
            console.error('Erro ao remover associados:', err)
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

    const handleAttributeChange = (value: string) => {
        setFormData({ ...formData, attribute: value })
        const validation = validateJson(value)
        if (validation.valid) {
            setJsonError(null)
        } else {
            setJsonError(validation.error || 'JSON inválido')
        }
    }

    // Handlers para filtros (usando hooks reutilizáveis)
    // Os hooks já gerenciam o estado, apenas precisamos usar as funções retornadas

    // Opções para os filtros (ordenadas automaticamente pelo componente)
    const statusOptions: FilterOption<string>[] = [
        { value: 'ACTIVE', label: 'Ativo', color: 'text-green-600' },
        { value: 'PENDING', label: 'Pendente', color: 'text-yellow-600' },
        { value: 'REJECTED', label: 'Rejeitado', color: 'text-red-600' },
        { value: 'REMOVED', label: 'Removido', color: 'text-gray-600' },
    ]

    const roleOptions: FilterOption<string>[] = [
        { value: 'account', label: 'Conta', color: 'text-blue-600' },
        { value: 'admin', label: 'Administrador', color: 'text-purple-600' },
    ]

    // Botões do ActionBar usando hook reutilizável
    const actionBarButtons = useActionBarButtons({
        isEditing,
        selectedCount: selectedMembers.size,
        hasChanges: hasChanges() || sendInvite, // Customização: incluir sendInvite
        submitting,
        deleting,
        onCancel: handleCancel,
        onDelete: handleDeleteSelected,
        onSave: editingMember ? handleSave : handleCreate,
        saveLabel: submitting 
            ? (editingMember ? 'Salvando...' : 'Criando...') 
            : (editingMember ? 'Salvar' : 'Criar'),
        deleteLabel: 'Remover',
    })

    // Props de erro do ActionBar usando função utilitária
    const actionBarErrorProps = getActionBarErrorProps(
        error,
        isEditing,
        selectedMembers.size,
        emailMessage,
        emailMessageType
    )

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Associação" isEditing={isEditing}>
                <div className="space-y-4">
                    <FormField label="E-mail" required>
                        <input
                            id="email"
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            placeholder="E-mail público na clínica"
                            required={!editingMember}
                            disabled={submitting}
                        />
                    </FormField>
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
                    <FormField label="Nome">
                        <input
                            id="name"
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Nome público na clínica"
                            disabled={submitting}
                        />
                    </FormField>
                    <FormFieldGrid cols={1} smCols={2} gap={4}>
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
                        <FormField label="Situação" required>
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
                        </FormField>
                    </FormFieldGrid>
                    <FormField
                        label="Atributos (JSON)"
                        required
                        error={jsonError || undefined}
                    >
                        <textarea
                            id="attribute"
                            value={formData.attribute}
                            onChange={(e) => handleAttributeChange(e.target.value)}
                            rows={10}
                            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm ${jsonError ? 'border-red-300' : 'border-gray-300'
                                }`}
                            disabled={submitting}
                        />
                    </FormField>
                </div>
            </EditForm>

            <CardPanel
                title="Associados"
                loading={loading}
                error={undefined}
                createCard={
                    <CreateCard
                        label="Convidar novo membro"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
                filterContent={
                    !isEditing ? (
                        <FilterPanel>
                            <FilterButtons
                                title="Situação"
                                options={statusOptions}
                                selectedValues={statusFilters.selectedFilters}
                                onToggle={statusFilters.toggleFilter}
                                onToggleAll={statusFilters.toggleAll}
                            />
                            <FilterButtons
                                title="Função"
                                options={roleOptions}
                                selectedValues={roleFilters.selectedFilters}
                                onToggle={roleFilters.toggleFilter}
                                onToggleAll={roleFilters.toggleAll}
                                allOptionLabel="Todas"
                            />
                        </FilterPanel>
                    ) : undefined
                }
            >
                {paginatedMembers.map((member) => {
                    const isSelected = selectedMembers.has(member.id)
                    return (
                        <EntityCard
                            key={member.id}
                            id={member.id}
                            isSelected={isSelected}
                            footer={
                                <CardFooter
                                    isSelected={isSelected}
                                    date={member.created_at}
                                    settings={settings}
                                    onToggleSelection={(e) => {
                                        e.stopPropagation()
                                        toggleMemberSelection(member.id)
                                    }}
                                    onEdit={() => handleEditClick(member)}
                                    disabled={deleting}
                                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                    editTitle="Editar associação"
                                />
                            }
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
                                            title={member.member_name || member.member_email || 'Não disponível'}
                                        >
                                            {member.member_name || member.member_email || 'Não disponível'}
                                        </h3>
                                        <div className="mt-2 flex flex-wrap gap-1 justify-center px-2">
                                            <span className={`text-xs px-2 py-1 rounded ${getStatusColor(member.status)}`}>
                                                {getStatusLabel(member.status)}
                                            </span>
                                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                                {getRoleLabel(member.role)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </EntityCard>
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
                            onFirst={onFirst}
                            onPrevious={onPrevious}
                            onNext={onNext}
                            onLast={onLast}
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
