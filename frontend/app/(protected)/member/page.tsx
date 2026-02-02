'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import type { FilterOption } from '@/components/filter'
import { FilterButtons, FilterPanel } from '@/components/filter'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { JsonEditor } from '@/components/JsonEditor'
import { Pagination } from '@/components/Pagination'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarRightButtons } from '@/hooks/useActionBarRightButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { useEntityPage } from '@/hooks/useEntityPage'
import { useReportButton } from '@/hooks/useReportButton'
import { protectedFetch } from '@/lib/api'
import { getCardTextClasses } from '@/lib/cardStyles'
import {
    MemberCreateRequest,
    MemberResponse,
    MemberUpdateRequest,
} from '@/types/api'
import { useEffect, useMemo, useState } from 'react'

function parseIsoToDate(iso: string): Date | null {
    if (!iso?.trim()) return null
    try {
        const d = new Date(iso)
        return isNaN(d.getTime()) ? null : d
    } catch {
        return null
    }
}

type MemberFormData = {
    role: string
    status: string
    name: string
    label: string  // Rótulo opcional
    email: string
    attribute: unknown  // JSON como objeto para edição
    can_peds: boolean
    sequence: number
    vacation: [string, string][]  // Lista de pares [início, fim] em ISO datetime
}

export default function MemberPage() {
    const { settings } = useTenantSettings()

    // Estados auxiliares para funcionalidade de convite
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')
    const [sendInvite, setSendInvite] = useState(false)

    // Títulos dos filtros: definidos uma vez, usados no painel e no cabeçalho do relatório
    const SITUATION_FILTER_LABEL = 'Situação'
    const ROLE_FILTER_LABEL = 'Função'

    const ALL_STATUS_FILTERS: string[] = ['PENDING', 'ACTIVE', 'REJECTED', 'REMOVED']
    const ALL_ROLE_FILTERS: string[] = ['account', 'admin']

    // Filtros usando hook reutilizável (retorna array; array vazio = zero resultados)
    const statusFilters = useEntityFilters<string>({
        allFilters: ALL_STATUS_FILTERS,
    })

    const roleFilters = useEntityFilters<string>({
        allFilters: ALL_ROLE_FILTERS,
    })

    // Configuração inicial (status PENDING para novo convite)
    const initialFormData: MemberFormData = {
        role: 'account',
        status: 'PENDING',
        name: '',
        label: '',  // Rótulo opcional
        email: '',
        attribute: {},
        can_peds: false,
        sequence: 0,
        vacation: [],
    }

    // Mapeamentos
    const mapEntityToFormData = (member: MemberResponse): MemberFormData => {
        return {
            role: member.role,
            status: member.status,
            name: member.member_name || '',
            label: member.member_label || '',  // Rótulo opcional
            email: member.member_email || '',
            attribute: member.attribute || {},
            can_peds: member.can_peds ?? false,
            sequence: member.sequence ?? 0,
            vacation: member.vacation ?? [],
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
            label: formData.label.trim() || null,  // Rótulo opcional
            role: formData.role,
            status: formData.status,
            attribute: attributeValue || null,
            can_peds: formData.can_peds,
            sequence: formData.sequence,
            vacation: (() => {
                const valid = formData.vacation.filter(([a, b]) => a?.trim() && b?.trim())
                return valid.length > 0 ? valid : null
            })(),
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
            label: formData.label.trim() || null,  // Rótulo opcional
            email: formData.email.trim() || null,
            attribute: attributeValue,
            can_peds: formData.can_peds,
            sequence: formData.sequence,
            vacation: (() => {
                const valid = formData.vacation.filter(([a, b]) => a?.trim() && b?.trim())
                return valid.length > 0 ? valid : null
            })(),
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
            formData.label.trim() === '' &&
            formData.email.trim() === '' &&
            formData.name.trim() === ''
        )
    }

    const additionalListParams = useMemo(
        () => ({
            ...statusFilters.toListParam('status_list'),
            ...roleFilters.toListParam('role_list'),
        }),
        [
            statusFilters.selectedValues,
            statusFilters.isFilterActive,
            statusFilters.toListParam,
            roleFilters.selectedValues,
            roleFilters.isFilterActive,
            roleFilters.toListParam,
        ]
    )

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
        handleSave,
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
        onOpenCreate: () => {
            setSendInvite(false)
            setEmailMessage(null)
        },
        onAfterSave: async (savedMember, isCreate) => {
            // Se o checkbox "Enviar convite" estiver marcado, enviar convite
            if (sendInvite) {
                await sendInviteEmail(savedMember)
            }
        },
        onSaveSuccess: () => {
            setSendInvite(false)
            setEmailMessage(null)
        },
    })

    // Resetar offset quando filtros mudarem
    useEffect(() => {
        paginationHandlers.onFirst()
    }, [statusFilters.selectedValues, statusFilters.isFilterActive, roleFilters.selectedValues, roleFilters.isFilterActive])

    const filteredMembers = members
    const paginatedMembers = members

    // Função para enviar convite por e-mail
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

    const reportFilters = useMemo((): { label: string; value: string }[] => {
        const list: { label: string; value: string }[] = []
        if (statusFilters.isFilterActive) {
            list.push({
                label: SITUATION_FILTER_LABEL,
                value: statusFilters.selectedValues.map(getStatusLabel).join(', '),
            })
        }
        if (roleFilters.isFilterActive) {
            list.push({
                label: ROLE_FILTER_LABEL,
                value: roleFilters.selectedValues.map(getRoleLabel).join(', '),
            })
        }
        return list
    }, [statusFilters.selectedValues, statusFilters.isFilterActive, roleFilters.selectedValues, roleFilters.isFilterActive])

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

    const { leftButtons: reportLeftButtons, reportError } = useReportButton({
        apiPath: '/api/member/report',
        params: additionalListParams ?? undefined,
        reportFilters,
    })

    // Sobrescrever actionBarButtons apenas para incluir sendInvite no hasChanges
    // (habilita botão Salvar quando checkbox "Enviar convite" está marcado)
    const actionBarButtonsWithInvite = useActionBarRightButtons({
        isEditing,
        selectedCount: selectedMembersCount,
        hasChanges: hasChanges() || sendInvite,
        submitting,
        deleting,
        onCancel: handleCancel,
        onDelete: handleDeleteSelected,
        onSave: handleSave,
    })

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
                    <FormFieldGrid cols={1} smCols={2} gap={4}>
                        <FormField label="Nome">
                            <input
                                id="name"
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            />
                        </FormField>
                        <FormField label="Rótulo">
                            <input
                                id="label"
                                type="text"
                                value={formData.label}
                                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                                placeholder="Identificador opcional"
                            />
                        </FormField>
                    </FormFieldGrid>
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
                    <FormFieldGrid cols={1} smCols={2} gap={4}>
                        <FormField label="Ordem (sequence)">
                            <input
                                id="sequence"
                                type="number"
                                min={0}
                                value={formData.sequence}
                                onChange={(e) => setFormData({ ...formData, sequence: parseInt(e.target.value, 10) || 0 })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            />
                        </FormField>
                        <div className="flex items-center pt-8">
                            <input
                                type="checkbox"
                                id="can_peds"
                                checked={formData.can_peds}
                                onChange={(e) => setFormData({ ...formData, can_peds: e.target.checked })}
                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                disabled={submitting}
                            />
                            <label htmlFor="can_peds" className="ml-2 block text-sm text-gray-700">
                                Pode atender pediatria
                            </label>
                        </div>
                    </FormFieldGrid>
                    <FormField label="Períodos de férias">
                        <div className="space-y-4">
                            {formData.vacation.map((pair, index) => (
                                <div key={index} className="flex flex-wrap items-start gap-4 p-3 border border-gray-200 rounded-md bg-gray-50">
                                    <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <TenantDateTimePicker
                                            id={`vacation_start_${index}`}
                                            label="Início"
                                            value={parseIsoToDate(pair[0])}
                                            onChange={(date) => {
                                                const newVacation = [...formData.vacation]
                                                newVacation[index] = [date ? date.toISOString() : '', pair[1] || '']
                                                setFormData({ ...formData, vacation: newVacation })
                                            }}
                                            disabled={submitting}
                                        />
                                        <TenantDateTimePicker
                                            id={`vacation_end_${index}`}
                                            label="Fim"
                                            value={parseIsoToDate(pair[1])}
                                            onChange={(date) => {
                                                const newVacation = [...formData.vacation]
                                                newVacation[index] = [pair[0] || '', date ? date.toISOString() : '']
                                                setFormData({ ...formData, vacation: newVacation })
                                            }}
                                            disabled={submitting}
                                        />
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const newVacation = formData.vacation.filter((_, i) => i !== index)
                                            setFormData({ ...formData, vacation: newVacation })
                                        }}
                                        className="text-sm text-red-600 hover:text-red-800 disabled:opacity-50 mt-8 shrink-0"
                                        disabled={submitting}
                                    >
                                        Remover
                                    </button>
                                </div>
                            ))}
                            <button
                                type="button"
                                onClick={() => setFormData({ ...formData, vacation: [...formData.vacation, ['', '']] })}
                                className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                disabled={submitting}
                            >
                                Adicionar período
                            </button>
                        </div>
                    </FormField>
                    <FormField label="Atributos (JSON)" required>
                        <JsonEditor
                            id="attribute"
                            value={
                                typeof formData.attribute === 'object' && formData.attribute !== null
                                    ? JSON.stringify(formData.attribute, null, 2)
                                    : typeof formData.attribute === 'string'
                                        ? formData.attribute
                                        : '{}'
                            }
                            on_change={(value: string) => {
                                try {
                                    const parsed = JSON.parse(value)
                                    setFormData({ ...formData, attribute: parsed })
                                } catch {
                                    // Se não for JSON válido, manter como string (será validado em validateFormData)
                                    setFormData({ ...formData, attribute: value })
                                }
                            }}
                            is_disabled={submitting}
                            height={400}
                        />
                    </FormField>
                    {emailMessage && (
                        <div
                            className={`p-3 rounded-md ${emailMessageType === 'success'
                                ? 'bg-green-50 text-green-800 border border-green-200'
                                : 'bg-red-50 text-red-800 border border-red-200'
                                }`}
                        >
                            <p className="text-sm">{emailMessage}</p>
                        </div>
                    )}
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
                        onClick={handleCreateClick}
                    />
                }
                filterContent={
                    !isEditing ? (
                        <FilterPanel>
                            <FilterButtons
                                title="Situação"
                                options={statusOptions}
                                selectedValues={statusFilters.selectedValues}
                                onToggle={statusFilters.toggleFilter}
                                onToggleAll={statusFilters.toggleAll}
                            />
                            <FilterButtons
                                title={ROLE_FILTER_LABEL}
                                options={roleOptions}
                                selectedValues={roleFilters.selectedValues}
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
                    grandTotal: total,
                    selectAllMode: selectAllMembersMode,
                    onToggleAll: () => toggleAllMembers(filteredMembers.map((m) => m.id)),
                }}
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
                error={reportError ?? actionBarErrorProps.error}
                message={actionBarErrorProps.message}
                messageType={actionBarErrorProps.messageType}
                leftButtons={reportLeftButtons}
                buttons={actionBarButtonsWithInvite}
            />
        </>
    )
}
