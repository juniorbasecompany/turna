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
import { JsonEditor } from '@/components/JsonEditor'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { useEntityPage } from '@/hooks/useEntityPage'
import { protectedFetch } from '@/lib/api'
import { getCardTextClasses } from '@/lib/cardStyles'
import {
    MemberCreateRequest,
    MemberResponse,
    MemberUpdateRequest,
} from '@/types/api'
import { useEffect, useMemo, useState } from 'react'

type MemberFormData = {
    role: string
    status: string
    name: string
    email: string
    attribute: unknown  // JSON como objeto para edição
}

export default function MemberPage() {
    const { settings } = useTenantSettings()

    // Estados auxiliares (não gerenciados por useEntityPage)
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')
    const [jsonError, setJsonError] = useState<string | null>(null)
    const [sendInvite, setSendInvite] = useState(false)

    // Constantes para filtros
    const ALL_STATUS_FILTERS: string[] = ['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED']
    const ALL_ROLE_FILTERS: string[] = ['account', 'admin']

    // Filtros usando hook reutilizável
    const statusFilters = useEntityFilters<string>({
        allFilters: ALL_STATUS_FILTERS,
        initialFilters: new Set(ALL_STATUS_FILTERS),
    })

    const roleFilters = useEntityFilters<string>({
        allFilters: ALL_ROLE_FILTERS,
        initialFilters: new Set(ALL_ROLE_FILTERS),
    })

    // Configuração inicial
    const initialFormData: MemberFormData = {
        role: 'account',
        status: 'ACTIVE',
        name: '',
        email: '',
        attribute: {},
    }

    // Mapeamentos
    const mapEntityToFormData = (member: MemberResponse): MemberFormData => {
        return {
            role: member.role,
            status: member.status,
            name: member.member_name || '',
            email: member.member_email || '',
            attribute: member.attribute || {},
        }
    }

    const mapFormDataToCreateRequest = (formData: MemberFormData): MemberCreateRequest => {
        // Converter attribute para objeto (já é objeto, mas garantir tipo)
        const attributeValue = formData.attribute && typeof formData.attribute === 'object' && !Array.isArray(formData.attribute)
            ? (formData.attribute as Record<string, unknown>)
            : {}

        return {
            email: formData.email.trim() || null,
            name: formData.name.trim() || null,
            role: formData.role,
            status: formData.status,
            attribute: attributeValue || null,
        }
    }

    const mapFormDataToUpdateRequest = (formData: MemberFormData): MemberUpdateRequest => {
        // Converter attribute para objeto (já é objeto, mas garantir tipo)
        const attributeValue = formData.attribute && typeof formData.attribute === 'object' && !Array.isArray(formData.attribute)
            ? (formData.attribute as Record<string, unknown>)
            : null

        return {
            role: formData.role,
            status: formData.status,
            name: formData.name.trim() || null,
            email: formData.email.trim() || null,
            attribute: attributeValue,
        }
    }

    // Validação
    const validateFormData = (formData: MemberFormData): string | null => {
        // Validar email (obrigatório para criação, opcional para edição)
        if (!formData.email || formData.email.trim() === '') {
            return 'E-mail é obrigatório'
        }

        // Validar attribute (deve ser objeto, não array, não null, não undefined)
        if (formData.attribute === null || formData.attribute === undefined) {
            return 'Atributos não podem estar vazios'
        }

        if (typeof formData.attribute !== 'object') {
            return 'Atributos devem ser um objeto'
        }

        if (Array.isArray(formData.attribute)) {
            return 'Atributos devem ser um objeto, não um array'
        }

        return null
    }

    // isEmptyCheck
    const isEmptyCheck = (formData: MemberFormData): boolean => {
        return (
            formData.email.trim() === '' &&
            formData.name.trim() === ''
        )
    }

    // Calcular additionalListParams reativo baseado nos filtros
    const additionalListParams = useMemo(() => {
        const params: Record<string, string | number | boolean | null> = {}

        // Status: passar apenas se exatamente 1 estiver selecionado
        if (statusFilters.selectedFilters.size === 1) {
            const status = Array.from(statusFilters.selectedFilters)[0]
            params.status = status
        }

        // Role: passar apenas se exatamente 1 estiver selecionado
        if (roleFilters.selectedFilters.size === 1) {
            const role = Array.from(roleFilters.selectedFilters)[0]
            params.role = role
        }

        return params
    }, [statusFilters.selectedFilters, roleFilters.selectedFilters])

    // Verificar se precisa filtrar no frontend (quando múltiplos valores estão selecionados)
    const needsFrontendFilter = useMemo(() => {
        const allStatusSelected = statusFilters.selectedFilters.size === ALL_STATUS_FILTERS.length
        const allRoleSelected = roleFilters.selectedFilters.size === ALL_ROLE_FILTERS.length

        // Se todos estão selecionados, não precisa filtrar
        if (allStatusSelected && allRoleSelected) {
            return false
        }

        // Se apenas 1 de cada está selecionado, backend filtra (não precisa filtrar no frontend)
        const singleStatusSelected = statusFilters.selectedFilters.size === 1
        const singleRoleSelected = roleFilters.selectedFilters.size === 1

        if (singleStatusSelected && singleRoleSelected) {
            return false
        }

        // Se múltiplos estão selecionados, precisa filtrar no frontend
        return true
    }, [statusFilters.selectedFilters, roleFilters.selectedFilters])

    // useEntityPage
    const {
        items: members,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingMember,
        isEditing,
        hasChanges,
        handleCreateClick,
        handleEditClick,
        handleCancel,
        selectedItems: selectedMembers,
        toggleSelection: toggleMemberSelection,
        toggleAll: toggleAllMembers,
        selectedCount: selectedMembersCount,
        selectAllMode: selectAllMembersMode,
        getSelectedIdsForAction: getSelectedMemberIdsForAction,
        pagination,
        total,
        paginationHandlers,
        handleSave: baseHandleSave,
        handleDeleteSelected,
        loadItems,
        actionBarErrorProps,
    } = useEntityPage<MemberFormData, MemberResponse, MemberCreateRequest, MemberUpdateRequest>({
        endpoint: '/api/member',
        entityName: 'member',
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
        additionalListParams,
        onSaveSuccess: () => {
            // Resetar estados específicos após salvar
            setSendInvite(false)
            setEmailMessage(null)
            setJsonError(null)
        },
    })

    // Resetar offset quando filtros mudarem
    useEffect(() => {
        paginationHandlers.onFirst()
    }, [statusFilters.selectedFilters, roleFilters.selectedFilters])

    // Filtrar no frontend quando múltiplos valores estão selecionados (backend não suporta múltiplos)
    const filteredMembers = useMemo(() => {
        if (!needsFrontendFilter) {
            return members
        }

        // Filtrar no frontend
        return members.filter((member) => {
            const statusMatch = statusFilters.selectedFilters.has(member.status)
            const roleMatch = roleFilters.selectedFilters.has(member.role)
            return statusMatch && roleMatch
        })
    }, [members, statusFilters.selectedFilters, roleFilters.selectedFilters, needsFrontendFilter])

    // Aplicar paginação no frontend quando há filtro no frontend
    const paginatedMembers = useMemo(() => {
        if (!needsFrontendFilter) {
            return filteredMembers  // Backend já paginou
        }

        // Paginar no frontend
        const start = pagination.offset
        const end = start + pagination.limit
        return filteredMembers.slice(start, end)
    }, [filteredMembers, needsFrontendFilter, pagination])

    // Validar attribute (objeto JSON)
    const validateAttribute = (attribute: unknown): { valid: boolean; error?: string; parsed?: Record<string, unknown> } => {
        if (attribute === null || attribute === undefined) {
            return { valid: false, error: 'Atributos não podem estar vazios' }
        }

        if (typeof attribute !== 'object') {
            return { valid: false, error: 'Atributos devem ser um objeto' }
        }

        if (Array.isArray(attribute)) {
            return { valid: false, error: 'Atributos devem ser um objeto, não um array' }
        }

        return { valid: true, parsed: attribute as Record<string, unknown> }
    }

    // Wrappers customizados para funcionalidades específicas
    const handleCreateClickCustom = () => {
        handleCreateClick()
        setFormData({
            ...formData,
            status: 'PENDING',  // Status padrão para criação
        })
        setSendInvite(false)
        setEmailMessage(null)
        setJsonError(null)
    }

    const handleEditClickCustom = (member: MemberResponse) => {
        handleEditClick(member)
        setEmailMessage(null)
        setJsonError(null)
    }

    const handleCancelCustom = () => {
        handleCancel()
        setSendInvite(false)
        setEmailMessage(null)
        setJsonError(null)
    }

    // Handler customizado para criação com suporte a sendInvite
    const handleCreate = async () => {
        // Validar attribute antes de salvar
        const attributeValidation = validateAttribute(formData.attribute)
        if (!attributeValidation.valid) {
            setError(attributeValidation.error || 'Atributos inválidos')
            setJsonError(attributeValidation.error || 'Atributos inválidos')
            return
        }

        try {
            setError(null)
            setEmailMessage(null)
            setJsonError(null)

            // Usar handleSave do useEntityPage, mas precisamos customizar
            // Como não podemos customizar handleSave facilmente, vamos fazer manualmente
            const createData: MemberCreateRequest = {
                email: formData.email.trim(),
                name: formData.name.trim() || null,
                role: formData.role,
                status: formData.status,
                attribute: attributeValidation.parsed || {},
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
            await loadItems()
            handleCancelCustom()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao criar member'
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao criar member:', err)
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

    // Handler customizado para edição com suporte a sendInvite
    const handleSave = async () => {
        if (!editingMember) {
            // Se não está editando, usar handleCreate
            await handleCreate()
            return
        }

        // Validar attribute antes de salvar
        const attributeValidation = validateAttribute(formData.attribute)
        if (!attributeValidation.valid) {
            setError(attributeValidation.error || 'Atributos inválidos')
            setJsonError(attributeValidation.error || 'Atributos inválidos')
            return
        }

        try {
            setError(null)
            setEmailMessage(null)
            setJsonError(null)

            // Usar handleSave do useEntityPage, mas precisamos customizar
            // Como não podemos customizar handleSave facilmente, vamos fazer manualmente
            const updateData: MemberUpdateRequest = {
                role: formData.role,
                status: formData.status,
                name: formData.name.trim() || null,
                email: formData.email.trim() || null,
                attribute: attributeValidation.parsed || {},
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
            await loadItems()
            handleCancelCustom()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar member'
            setError(message)
            setEmailMessage(null)
            console.error('Erro ao salvar member:', err)
        }
    }

    // Handler customizado para exclusão (mantém lógica de Promise.allSettled)
    const handleDeleteSelectedCustom = async () => {
        if (selectedMembers.size === 0) return

        try {
            setError(null)

            // Obter IDs para ação: null = todos (selectAllMode), array = IDs específicos
            const idsForAction = getSelectedMemberIdsForAction()
            let idsToDelete: number[]

            if (idsForAction === null) {
                // Modo "todos": buscar todos os IDs que atendem aos filtros atuais
                const params = new URLSearchParams()
                params.set('limit', '10000')
                params.set('offset', '0')

                if (additionalListParams) {
                    Object.entries(additionalListParams).forEach(([key, value]) => {
                        if (value !== null && value !== undefined) {
                            params.set(key, String(value))
                        }
                    })
                }

                const response = await protectedFetch<{ items: MemberResponse[]; total: number }>(
                    `/api/member/list?${params.toString()}`
                )
                idsToDelete = response.items.map((item) => item.id)
            } else {
                idsToDelete = idsForAction
            }

            if (idsToDelete.length === 0) {
                setError('Nenhum item para excluir')
                return
            }

            const deletePromises = idsToDelete.map(async (memberId) => {
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

            // Recarregar lista (useEntityPage já limpa seleção)
            await loadItems()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao remover associados'
            setError(message)
            console.error('Erro ao remover associados:', err)
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

    const handleAttributeChange = (value: unknown) => {
        setFormData({ ...formData, attribute: value })
        const validation = validateAttribute(value)
        if (validation.valid) {
            setJsonError(null)
        } else {
            setJsonError(validation.error || 'Atributos inválidos')
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
        selectedCount: selectedMembersCount,
        hasChanges: hasChanges() || sendInvite, // Customização: incluir sendInvite
        submitting,
        deleting,
        onCancel: handleCancelCustom,
        onDelete: handleDeleteSelectedCustom,
        onSave: handleSave,
        saveLabel: submitting
            ? (editingMember ? 'Salvando...' : 'Criando...')
            : (editingMember ? 'Salvar' : 'Criar'),
    })

    // Props de erro do ActionBar (customizado para incluir emailMessage)
    const actionBarErrorPropsCustom = useMemo(() => {
        const baseProps = actionBarErrorProps
        // Se houver emailMessage, usar ele em vez de error
        if (emailMessage) {
            return {
                ...baseProps,
                message: emailMessage,
                messageType: emailMessageType,
            }
        }
        return baseProps
    }, [actionBarErrorProps, emailMessage, emailMessageType])

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
                        <JsonEditor
                            id="attribute"
                            value={formData.attribute}
                            on_change={handleAttributeChange}
                            is_disabled={submitting}
                            height={400}
                        />
                    </FormField>
                </div>
            </EditForm>

            <CardPanel
                title="Associados"
                description="Gerencie os membros associados da clínica"
                totalCount={filteredMembers.length}
                selectedCount={selectedMembersCount}
                loading={loading}
                error={undefined}
                createCard={
                    <CreateCard
                        label="Convidar novo membro"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClickCustom}
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
                                    onEdit={() => handleEditClickCustom(member)}
                                    disabled={deleting}
                                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                    editTitle="Editar associação"
                                />
                            }
                        >
                            <div className="mb-3">
                                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-blue-50 border border-blue-200">
                                    <div className="flex flex-col items-center justify-center text-blue-600">
                                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                                            <svg
                                                className="w-full h-full"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                {/* Cabeça */}
                                                <circle
                                                    cx="12"
                                                    cy="8"
                                                    r="4"
                                                    strokeWidth={2}
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                />
                                                {/* Corpo */}
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"
                                                />
                                            </svg>
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${getCardTextClasses(isSelected)}`}
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
                selection={{
                    selectedCount: selectedMembersCount,
                    totalCount: filteredMembers.length,
                    grandTotal: needsFrontendFilter ? filteredMembers.length : total,
                    selectAllMode: selectAllMembersMode,
                    onToggleAll: () => toggleAllMembers(filteredMembers.map((m) => m.id)),
                }}
                pagination={
                    (needsFrontendFilter ? filteredMembers.length : total) > 0 ? (
                        <Pagination
                            offset={pagination.offset}
                            limit={pagination.limit}
                            total={needsFrontendFilter ? filteredMembers.length : total}
                            onFirst={paginationHandlers.onFirst}
                            onPrevious={paginationHandlers.onPrevious}
                            onNext={paginationHandlers.onNext}
                            onLast={paginationHandlers.onLast}
                            disabled={loading}
                        />
                    ) : undefined
                }
                error={actionBarErrorPropsCustom.error}
                message={actionBarErrorPropsCustom.message}
                messageType={actionBarErrorPropsCustom.messageType}
                buttons={actionBarButtons}
            />
        </>
    )
}
