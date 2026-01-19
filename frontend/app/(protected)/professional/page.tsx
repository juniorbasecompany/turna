'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { getCardContainerClasses } from '@/lib/cardStyles'
import {
    ProfessionalCreateRequest,
    ProfessionalListResponse,
    ProfessionalResponse,
    ProfessionalUpdateRequest,
} from '@/types/api'
import { extractErrorMessage } from '@/lib/api'
import { useEffect, useState } from 'react'

export default function ProfessionalPage() {
    const { settings } = useTenantSettings()
    const [professionals, setProfessionals] = useState<ProfessionalResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [editingProfessional, setEditingProfessional] = useState<ProfessionalResponse | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
        notes: '',
        active: true,
    })
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

            const response = await fetch(`/api/professional/list?${params.toString()}`, {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
            }

            const data: ProfessionalListResponse = await response.json()
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

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingProfessional) {
            return formData.name.trim() !== '' || formData.email.trim() !== '' || formData.phone.trim() !== '' || formData.notes.trim() !== ''
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
        setShowEditArea(true)
        setError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (professional: ProfessionalResponse) => {
        const initialData = {
            name: professional.name,
            email: professional.email || '',
            phone: professional.phone || '',
            notes: professional.notes || '',
            active: professional.active,
        }
        setFormData(initialData)
        setOriginalFormData(initialData)
        setEditingProfessional(professional)
        setShowEditArea(true)
        setError(null)
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
        setShowEditArea(false)
        setSelectedProfessionals(new Set())
        setError(null)
    }

    // Submeter formulário (criar ou editar)
    const handleSave = async () => {
        if (!formData.name.trim()) {
            setError('Nome é obrigatório')
            return
        }

        try {
            setSubmitting(true)
            setError(null)

            if (editingProfessional) {
                // Editar profissional existente
                const updateData: ProfessionalUpdateRequest = {
                    name: formData.name.trim(),
                    email: formData.email.trim() || null,
                    phone: formData.phone.trim() || null,
                    notes: formData.notes.trim() || null,
                    active: formData.active,
                }

                const response = await fetch(`/api/professional/${editingProfessional.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify(updateData),
                })

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}))
                    throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
                }
            } else {
                // Criar novo profissional
                const createData: ProfessionalCreateRequest = {
                    name: formData.name.trim(),
                    email: formData.email.trim() || undefined,
                    phone: formData.phone.trim() || undefined,
                    notes: formData.notes.trim() || undefined,
                    active: formData.active,
                }

                const response = await fetch('/api/professional', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify(createData),
                })

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}))
                    throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
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
            setShowEditArea(false)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar profissional'
            setError(message)
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
                const response = await fetch(`/api/professional/${professionalId}`, {
                    method: 'DELETE',
                    credentials: 'include',
                })

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Sessão expirada. Por favor, faça login novamente.')
                    }
                    const errorData = await response.json().catch(() => ({}))
                    throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
                }

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
                countLabel="Total de profissionais"
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
                                            Email
                                        </label>
                                        <input
                                            type="email"
                                            id="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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

            {/* Paginação */}
            {total > 0 && (
                <div className="p-4 sm:p-6 lg:p-8 min-w-0">
                    <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between">
                        <div className="text-sm text-gray-700">
                            Mostrando {pagination.offset + 1} a {Math.min(pagination.offset + pagination.limit, total)} de {total}
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPagination({ ...pagination, offset: Math.max(0, pagination.offset - pagination.limit) })}
                                disabled={pagination.offset === 0 || loading}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Anterior
                            </button>
                            <button
                                onClick={() => setPagination({ ...pagination, offset: pagination.offset + pagination.limit })}
                                disabled={pagination.offset + pagination.limit >= total || loading}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Próxima
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <ActionBarSpacer />

            <ActionBar
                error={(() => {
                    const hasButtons = isEditing || selectedProfessionals.size > 0
                    return hasButtons ? error : undefined
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
                    if (isEditing && hasChanges()) {
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
