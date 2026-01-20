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
    ProfessionalCreateRequest,
    ProfessionalListResponse,
    ProfessionalResponse,
    ProfessionalUpdateRequest,
} from '@/types/api'
import { useEffect, useState } from 'react'

export default function ProfessionalPage() {
    const { settings } = useTenantSettings()
    const [professionals, setProfessionals] = useState<ProfessionalResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [emailMessage, setEmailMessage] = useState<string | null>(null)
    const [emailMessageType, setEmailMessageType] = useState<'success' | 'error'>('success')
    const [editingProfessional, setEditingProfessional] = useState<ProfessionalResponse | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
        notes: '',
        active: true,
    })
    const [sendInvite, setSendInvite] = useState(false)
    const [originalFormData, setOriginalFormData] = useState({
        name: '',
        email: '',
        phone: '',
        notes: '',
        active: true,
    })
    const [submitting, setSubmitting] = useState(false)
    const [selectedProfessionals, setSelectedProfessionals] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [filters, setFilters] = useState({
        q: '',
        active: null as boolean | null,
    })
    const [pagination, setPagination] = useState({ limit: 20, offset: 0 })
    const [total, setTotal] = useState(0)

    // Carregar lista de profissionais
    const loadProfessionals = async () => {
        try {
            setLoading(true)
            setError(null)

            const params = new URLSearchParams()
            if (filters.q) params.append('q', filters.q)
            if (filters.active !== null) params.append('active', String(filters.active))
            params.append('limit', String(pagination.limit))
            params.append('offset', String(pagination.offset))

            const data = await protectedFetch<ProfessionalListResponse>(`/api/professional/list?${params.toString()}`)
            setProfessionals(data.items)
            setTotal(data.total)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar profissionais'
            setError(message)
            console.error('Erro ao carregar profissionais:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadProfessionals()
    }, [filters, pagination])

    // Debug: log quando emailMessage mudar
    useEffect(() => {
        if (emailMessage) {
            console.log('[EMAIL-MESSAGE-EFFECT] emailMessage mudou para:', emailMessage, 'tipo:', emailMessageType)
        }
    }, [emailMessage, emailMessageType])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingProfessional) {
            return formData.name.trim() !== '' && formData.email.trim() !== ''
        }
        return (
            formData.name.trim() !== originalFormData.name.trim() ||
            formData.email.trim() !== originalFormData.email.trim() ||
            formData.phone.trim() !== originalFormData.phone.trim() ||
            formData.notes.trim() !== originalFormData.notes.trim() ||
            formData.active !== originalFormData.active
        )
    }

    const [showEditArea, setShowEditArea] = useState(false)
    const isEditing = showEditArea

    // Abrir modo de criação
    const handleCreateClick = () => {
        setFormData({
            name: '',
            email: '',
            phone: '',
            notes: '',
            active: true,
        })
        setOriginalFormData({
            name: '',
            email: '',
            phone: '',
            notes: '',
            active: true,
        })
        setEditingProfessional(null)
        setSendInvite(false)
        setShowEditArea(true)
        setError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (professional: ProfessionalResponse) => {
        const initialData = {
            name: professional.name,
            email: professional.email, // Email é obrigatório, sempre terá valor
            phone: professional.phone || '',
            notes: professional.notes || '',
            active: professional.active,
        }
        setFormData(initialData)
        setOriginalFormData(initialData)
        setEditingProfessional(professional)
        setSendInvite(false)
        setShowEditArea(true)
        setError(null)
        setEmailMessage(null)
    }

    // Cancelar edição e/ou seleção
    const handleCancel = () => {
        setFormData({
            name: '',
            email: '',
            phone: '',
            notes: '',
            active: true,
        })
        setOriginalFormData({
            name: '',
            email: '',
            phone: '',
            notes: '',
            active: true,
        })
        setEditingProfessional(null)
        setSendInvite(false)
        setShowEditArea(false)
        setSelectedProfessionals(new Set())
        setError(null)
        setEmailMessage(null)
    }

    // Submeter formulário (criar ou editar)
    const handleSave = async () => {
        if (!formData.name.trim()) {
            setError('Nome é obrigatório')
            setEmailMessage(null) // Limpar mensagem de email ao validar
            return
        }

        if (!formData.email.trim()) {
            setError('Email é obrigatório')
            setEmailMessage(null) // Limpar mensagem de email ao validar
            return
        }

        try {
            setSubmitting(true)
            setError(null)
            setEmailMessage(null) // Limpar mensagem de email anterior ao iniciar novo salvamento

            let savedProfessional: ProfessionalResponse | null = null

            if (editingProfessional) {
                // Editar profissional existente
                const updateData: ProfessionalUpdateRequest = {
                    name: formData.name.trim(),
                    email: formData.email.trim() || null,
                    phone: formData.phone.trim() || null,
                    notes: formData.notes.trim() || null,
                    active: formData.active,
                }

                savedProfessional = await protectedFetch<ProfessionalResponse>(`/api/professional/${editingProfessional.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                })
            } else {
                // Criar novo profissional
                const createData: ProfessionalCreateRequest = {
                    name: formData.name.trim(),
                    email: formData.email.trim(),
                    phone: formData.phone.trim() || undefined,
                    notes: formData.notes.trim() || undefined,
                    active: formData.active,
                }

                savedProfessional = await protectedFetch<ProfessionalResponse>('/api/professional', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(createData),
                })
            }

            // Se o checkbox "Enviar convite" estiver marcado, enviar convite
            if (sendInvite && savedProfessional) {
                console.log(
                    `[INVITE-UI] Iniciando envio de convite para profissional ID=${savedProfessional.id} (${savedProfessional.name})`
                )
                try {
                    await protectedFetch(`/api/professional/${savedProfessional.id}/invite`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                    })
                    // Definir mensagem de sucesso no ActionBar
                    const successMsg = `E-mail de convite foi enviado para ${savedProfessional.name}`
                    console.log('[EMAIL-MESSAGE] Definindo mensagem de sucesso:', successMsg)
                    setEmailMessage(successMsg)
                    setEmailMessageType('success')
                } catch (inviteErr) {
                    const errorMsg = inviteErr instanceof Error ? inviteErr.message : 'Erro desconhecido'
                    console.error(
                        `[INVITE-UI] ❌ FALHA - Erro ao enviar convite para profissional ID=${savedProfessional.id}:`,
                        inviteErr
                    )
                    // Definir mensagem de erro no ActionBar
                    setEmailMessage(`E-mail de convite não foi enviado para ${savedProfessional.name}. ${errorMsg}`)
                    setEmailMessageType('error')
                }
            }

            // Recarregar lista e limpar formulário
            await loadProfessionals()

            setFormData({
                name: '',
                email: '',
                phone: '',
                notes: '',
                active: true,
            })
            setOriginalFormData({
                name: '',
                email: '',
                phone: '',
                notes: '',
                active: true,
            })
            setEditingProfessional(null)
            setSendInvite(false)
            setShowEditArea(false)
            // Mensagem de email permanece visível até o usuário fechar o formulário ou fazer nova ação
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar profissional'
            setError(message)
            setEmailMessage(null) // Limpar mensagem de email se houver erro no salvamento
            console.error('Erro ao salvar profissional:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de profissional para exclusão
    const toggleProfessionalSelection = (professionalId: number) => {
        setSelectedProfessionals((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(professionalId)) {
                newSet.delete(professionalId)
            } else {
                newSet.add(professionalId)
            }
            return newSet
        })
    }

    // Excluir profissionais selecionados
    const handleDeleteSelected = async () => {
        if (selectedProfessionals.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            const deletePromises = Array.from(selectedProfessionals).map(async (professionalId) => {
                await protectedFetch(`/api/professional/${professionalId}`, {
                    method: 'DELETE',
                })
                return professionalId
            })

            await Promise.all(deletePromises)

            setProfessionals(professionals.filter((professional) => !selectedProfessionals.has(professional.id)))
            setSelectedProfessionals(new Set())

            await loadProfessionals()
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao excluir profissionais. Tente novamente.'
            )
        } finally {
            setDeleting(false)
        }
    }

    return (
        <>
            <CardPanel
                title="Profissionais"
                description="Gerencie os profissionais que podem ser alocados nas escalas"
                totalCount={total}
                selectedCount={selectedProfessionals.size}
                loading={loading}
                loadingMessage="Carregando profissionais..."
                emptyMessage="Nenhum profissional cadastrado ainda."
                editContent={
                    isEditing ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">
                                {editingProfessional ? 'Editar Profissional' : 'Criar Profissional'}
                            </h2>
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                                        Nome <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        id="name"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        required
                                        disabled={submitting}
                                    />
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div>
                                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                                            Email <span className="text-red-500">*</span>
                                        </label>
                                        <input
                                            type="email"
                                            id="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            required
                                            disabled={submitting}
                                        />
                                    </div>
                                    <div>
                                        <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                                            Telefone
                                        </label>
                                        <input
                                            type="text"
                                            id="phone"
                                            value={formData.phone}
                                            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            disabled={submitting}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-2">
                                        Observações
                                    </label>
                                    <textarea
                                        id="notes"
                                        value={formData.notes}
                                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                        rows={3}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                                    <div className="flex items-center">
                                        <input
                                            type="checkbox"
                                            id="active"
                                            checked={formData.active}
                                            onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            disabled={submitting}
                                        />
                                        <label htmlFor="active" className="ml-2 block text-sm text-gray-700">
                                            Ativo
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : undefined
                }
                filterContent={
                    !isEditing ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="filter-q" className="block text-sm font-medium text-gray-700 mb-2">
                                        Buscar
                                    </label>
                                    <input
                                        type="text"
                                        id="filter-q"
                                        value={filters.q}
                                        onChange={(e) => {
                                            setFilters({ ...filters, q: e.target.value })
                                            setPagination({ ...pagination, offset: 0 })
                                        }}
                                        placeholder="Nome..."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="filter-active" className="block text-sm font-medium text-gray-700 mb-2">
                                        Status
                                    </label>
                                    <select
                                        id="filter-active"
                                        value={filters.active === null ? '' : String(filters.active)}
                                        onChange={(e) => {
                                            setFilters({
                                                ...filters,
                                                active: e.target.value === '' ? null : e.target.value === 'true',
                                            })
                                            setPagination({ ...pagination, offset: 0 })
                                        }}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="">Todos</option>
                                        <option value="true">Ativos</option>
                                        <option value="false">Inativos</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    ) : undefined
                }
                createCard={
                    <CreateCard
                        label="Criar novo profissional"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
            >
                {professionals.map((professional) => {
                    const isSelected = selectedProfessionals.has(professional.id)
                    return (
                        <div
                            key={professional.id}
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
                                            className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                }`}
                                            title={professional.name}
                                        >
                                            {professional.name}
                                        </h3>
                                        <div className="mt-2 flex flex-wrap gap-1 justify-center px-2">
                                            {!professional.active && (
                                                <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                                    Inativo
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <CardFooter
                                isSelected={isSelected}
                                date={professional.created_at}
                                settings={settings}
                                onToggleSelection={(e) => {
                                    e.stopPropagation()
                                    toggleProfessionalSelection(professional.id)
                                }}
                                onEdit={() => handleEditClick(professional)}
                                disabled={deleting}
                                deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                editTitle="Editar profissional"
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
                    const hasButtons = isEditing || selectedProfessionals.size > 0
                    return hasButtons ? error : undefined
                })()}
                message={(() => {
                    // Priorizar mensagem de email se houver
                    if (emailMessage) {
                        return emailMessage
                    }
                    // Se não há botões mas há erro, mostrar via message
                    const hasButtons = isEditing || selectedProfessionals.size > 0
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
                    const hasButtons = isEditing || selectedProfessionals.size > 0
                    if (!hasButtons && error) {
                        return 'error' as const
                    }
                    return undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    if (isEditing || selectedProfessionals.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    if (selectedProfessionals.size > 0) {
                        buttons.push({
                            label: 'Excluir',
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
