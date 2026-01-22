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
    HospitalListResponse,
    HospitalResponse,
    ProfileCreateRequest,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdateRequest,
} from '@/types/api'
import { useEffect, useState } from 'react'

export default function ProfilePage() {
    const { settings } = useTenantSettings()
    const [profiles, setProfiles] = useState<ProfileResponse[]>([])
    const [memberships, setMemberships] = useState<MembershipResponse[]>([])
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [loadingMemberships, setLoadingMemberships] = useState(true)
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [editingProfile, setEditingProfile] = useState<ProfileResponse | null>(null)
    const [formData, setFormData] = useState({
        membership_id: null as number | null,
        hospital_id: null as number | null,
        attribute: '{}',
    })
    const [originalFormData, setOriginalFormData] = useState({ ...formData })
    const [submitting, setSubmitting] = useState(false)
    const [selectedProfiles, setSelectedProfiles] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [jsonError, setJsonError] = useState<string | null>(null)
    const [pagination, setPagination] = useState({ limit: 20, offset: 0 })
    const [total, setTotal] = useState(0)

    // Carregar memberships e hospitals (apenas uma vez, não dependem de paginação)
    const loadAccountsAndHospitals = async () => {
        try {
            setLoadingMemberships(true)
            setLoadingHospitals(true)
            setError(null)

            const [membershipsResult, hospitalsResult] = await Promise.allSettled([
                protectedFetch<MembershipListResponse>('/api/membership/list'),
                protectedFetch<HospitalListResponse>('/api/hospital/list'),
            ])

            if (membershipsResult.status === 'fulfilled') {
                setMemberships(membershipsResult.value.items)
            } else {
                const error = membershipsResult.reason
                const message = error instanceof Error ? error.message : 'Erro ao carregar associações'
                setError(message)
                console.error('Erro ao carregar memberships:', error)
            }

            if (hospitalsResult.status === 'fulfilled') {
                setHospitals(hospitalsResult.value.items)
            } else {
                const error = hospitalsResult.reason
                const message = error instanceof Error ? error.message : 'Erro ao carregar hospitais'
                setError(message)
                console.error('Erro ao carregar hospitals:', error)
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar dados'
            setError(message)
            console.error('Erro ao carregar dados:', err)
        } finally {
            setLoadingMemberships(false)
            setLoadingHospitals(false)
        }
    }

    // Carregar lista de perfis com paginação
    const loadProfiles = async () => {
        try {
            setLoading(true)
            setError(null)

            const params = new URLSearchParams()
            params.append('limit', String(pagination.limit))
            params.append('offset', String(pagination.offset))

            const data = await protectedFetch<ProfileListResponse>(`/api/profile/list?${params.toString()}`)
            setProfiles(data.items)
            setTotal(data.total)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar perfis'
            setError(message)
            console.error('Erro ao carregar perfis:', err)
        } finally {
            setLoading(false)
        }
    }

    // Carregar accounts e hospitals apenas uma vez ao montar
    useEffect(() => {
        loadAccountsAndHospitals()
    }, [])

    // Carregar perfis quando paginação mudar
    useEffect(() => {
        loadProfiles()
    }, [pagination])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingProfile) {
            return formData.membership_id !== null || formData.hospital_id !== null || formData.attribute.trim() !== '{}'
        }
        return (
            formData.membership_id !== originalFormData.membership_id ||
            formData.hospital_id !== originalFormData.hospital_id ||
            formData.attribute.trim() !== originalFormData.attribute.trim()
        )
    }

    // Verificar se está em modo de edição/criação
    const [showEditArea, setShowEditArea] = useState(false)
    const isEditing = showEditArea

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

    // Abrir modo de criação
    const handleCreateClick = () => {
        setFormData({ membership_id: null, hospital_id: null, attribute: '{}' })
        setOriginalFormData({ membership_id: null, hospital_id: null, attribute: '{}' })
        setEditingProfile(null)
        setShowEditArea(true)
        setError(null)
        setJsonError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (profile: ProfileResponse) => {
        const initialData = {
            membership_id: profile.membership_id,
            hospital_id: profile.hospital_id,
            attribute: JSON.stringify(profile.attribute, null, 2),
        }
        setFormData(initialData)
        setOriginalFormData(initialData)
        setEditingProfile(profile)
        setShowEditArea(true)
        setError(null)
        setJsonError(null)
    }

    // Cancelar edição e/ou seleção
    const handleCancel = () => {
        setFormData({ membership_id: null, hospital_id: null, attribute: '{}' })
        setOriginalFormData({ membership_id: null, hospital_id: null, attribute: '{}' })
        setEditingProfile(null)
        setShowEditArea(false)
        setSelectedProfiles(new Set())
        setError(null)
        setJsonError(null)
    }

    // Submeter formulário (criar ou editar)
    const handleSave = async () => {
        // Validar membership_id
        if (!formData.membership_id) {
            setError('Associação é obrigatória')
            return
        }

        // Validar JSON
        const jsonValidation = validateJson(formData.attribute)
        if (!jsonValidation.valid) {
            const errorMsg = jsonValidation.error || 'JSON inválido'
            setJsonError(errorMsg)
            setError(errorMsg)
            return
        }
        setJsonError(null)

        try {
            setSubmitting(true)
            setError(null)

            const attributeObj = jsonValidation.parsed || {}

            if (editingProfile) {
                // Editar profile existente
                const updateData: ProfileUpdateRequest = {
                    hospital_id: formData.hospital_id || null,
                    attribute: attributeObj,
                }

                await protectedFetch(`/api/profile/${editingProfile.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                })
            } else {
                // Criar novo profile
                const createData: ProfileCreateRequest = {
                    membership_id: formData.membership_id,
                    hospital_id: formData.hospital_id || null,
                    attribute: attributeObj,
                }

                await protectedFetch('/api/profile', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(createData),
                })
            }

            // Recarregar lista e limpar formulário
            await loadProfiles()
            setFormData({ membership_id: null, hospital_id: null, attribute: '{}' })
            setOriginalFormData({ membership_id: null, hospital_id: null, attribute: '{}' })
            setEditingProfile(null)
            setShowEditArea(false)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar profile'
            setError(message)
            console.error('Erro ao salvar profile:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de profile para exclusão
    const toggleProfileSelection = (profileId: number) => {
        setSelectedProfiles((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(profileId)) {
                newSet.delete(profileId)
            } else {
                newSet.add(profileId)
            }
            return newSet
        })
    }

    // Excluir profiles selecionados
    const handleDeleteSelected = async () => {
        if (selectedProfiles.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            const deletePromises = Array.from(selectedProfiles).map(async (profileId) => {
                await protectedFetch(`/api/profile/${profileId}`, {
                    method: 'DELETE',
                })
                return profileId
            })

            await Promise.all(deletePromises)

            setSelectedProfiles(new Set())

            await loadProfiles()
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao excluir perfis. Tente novamente.'
            )
        } finally {
            setDeleting(false)
        }
    }

    // Atualizar JSON e validar
    const handleAttributeChange = (value: string) => {
        setFormData({ ...formData, attribute: value })
        const validation = validateJson(value)
        if (validation.valid) {
            setJsonError(null)
        } else {
            setJsonError(validation.error || 'JSON inválido')
        }
    }

    return (
        <>
            {/* Área de edição */}
            {isEditing && (
                <div className="p-4 sm:p-6 lg:p-8 min-w-0">
                    <div className="mb-4 sm:mb-6 bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">
                            {editingProfile ? 'Editar Perfil' : 'Criar Perfil'}
                        </h2>
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="membership_id" className="block text-sm font-medium text-gray-700 mb-2">
                                        Associação <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        id="membership_id"
                                        value={formData.membership_id || ''}
                                        onChange={(e) =>
                                            setFormData({ ...formData, membership_id: e.target.value ? parseInt(e.target.value) : null })
                                        }
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        required
                                        disabled={submitting || editingProfile !== null || loadingMemberships}
                                    >
                                        <option value=""></option>
                                        {memberships.map((membership) => (
                                            <option key={membership.id} value={membership.id}>
                                                {membership.membership_name || membership.membership_email || 'Sem nome'} ({membership.role === 'admin' ? 'Admin' : 'Conta'})
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="hospital_id" className="block text-sm font-medium text-gray-700 mb-2">
                                        Hospital (opcional)
                                    </label>
                                    <select
                                        id="hospital_id"
                                        value={formData.hospital_id || ''}
                                        onChange={(e) =>
                                            setFormData({ ...formData, hospital_id: e.target.value ? parseInt(e.target.value) : null })
                                        }
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting || loadingHospitals}
                                    >
                                        <option value=""></option>
                                        {hospitals.map((hospital) => (
                                            <option key={hospital.id} value={hospital.id}>
                                                {hospital.name}
                                            </option>
                                        ))}
                                    </select>
                                    <p className="mt-1 text-xs text-gray-500">
                                        Informe o hospital se o perfil vale apenas para ele.
                                    </p>
                                </div>
                            </div>
                            <div>
                                <label htmlFor="attribute" className="block text-sm font-medium text-gray-700 mb-2">
                                    Atributos (JSON) <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    id="attribute"
                                    value={formData.attribute}
                                    onChange={(e) => handleAttributeChange(e.target.value)}
                                    rows={10}
                                    className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm ${jsonError ? 'border-red-300' : 'border-gray-300'
                                        }`}
                                    disabled={submitting}
                                />
                                {jsonError && (
                                    <p className="mt-1 text-sm text-red-600">{jsonError}</p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <CardPanel
                title="Perfis"
                description="Gerencie os perfis de usuários com atributos customizados"
                totalCount={total}
                selectedCount={selectedProfiles.size}
                loading={loading}
                loadingMessage="Carregando perfis..."
                emptyMessage="Nenhum perfil cadastrado ainda."
                createCard={
                    <CreateCard
                        label="Criar novo perfil"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
            >
                {profiles.map((profile) => {
                    const isSelected = selectedProfiles.has(profile.id)
                    const membership = memberships.find((m) => m.id === profile.membership_id)
                    const hospital = hospitals.find((h) => h.id === profile.hospital_id)
                    return (
                        <div
                            key={profile.id}
                            className={getCardContainerClasses(isSelected)}
                        >
                            {/* 1. Corpo - Ícone de perfil e informações */}
                            <div className="mb-3">
                                <div
                                    className="h-40 sm:h-48 rounded-lg flex items-center justify-center"
                                    style={{
                                        backgroundColor: '#f1f5f9',
                                    }}
                                >
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
                                            title={membership ? (membership.membership_name || membership.membership_email) : `ID: ${profile.id}`}
                                        >
                                            {membership ? (membership.membership_name || membership.membership_email) : `Perfil ${profile.id}`}
                                        </h3>
                                        {membership && (
                                            <p className={`text-xs text-center px-2 mt-1 truncate w-full ${isSelected ? 'text-red-700' : 'text-gray-500'
                                                }`}>
                                                {membership.membership_email || 'Sem email'}
                                            </p>
                                        )}
                                        {hospital && (
                                            <p className={`text-xs text-center px-2 mt-1 ${isSelected ? 'text-red-700' : 'text-gray-500'
                                                }`}>
                                                {hospital.name}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* 3. Rodapé - Metadados e ações */}
                            <CardFooter
                                isSelected={isSelected}
                                date={profile.created_at}
                                settings={settings}
                                onToggleSelection={(e) => {
                                    e.stopPropagation()
                                    toggleProfileSelection(profile.id)
                                }}
                                onEdit={() => handleEditClick(profile)}
                                disabled={deleting}
                                deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                editTitle="Editar perfil"
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
                    // Mostra erro no ActionBar apenas se houver botões de ação
                    const hasButtons = isEditing || selectedProfiles.size > 0
                    return hasButtons ? error : undefined
                })()}
                message={(() => {
                    // Se não há botões mas há erro, mostrar via message
                    const hasButtons = isEditing || selectedProfiles.size > 0
                    if (!hasButtons && error) {
                        return error
                    }
                    return undefined
                })()}
                messageType={(() => {
                    // Se não há botões mas há erro, usar tipo error
                    const hasButtons = isEditing || selectedProfiles.size > 0
                    if (!hasButtons && error) {
                        return 'error' as const
                    }
                    return undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    // Botão Cancelar (aparece se houver edição OU seleção)
                    if (isEditing || selectedProfiles.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    // Botão Excluir (aparece se houver seleção)
                    if (selectedProfiles.size > 0) {
                        buttons.push({
                            label: 'Excluir',
                            onClick: handleDeleteSelected,
                            variant: 'primary' as const,
                            disabled: deleting || submitting,
                            loading: deleting,
                        })
                    }
                    // Botão Salvar (aparece se houver edição com mudanças)
                    if (isEditing && hasChanges()) {
                        buttons.push({
                            label: submitting ? 'Salvando...' : 'Salvar',
                            onClick: handleSave,
                            variant: 'primary' as const,
                            disabled: submitting || !!jsonError,
                            loading: submitting,
                        })
                    }
                    return buttons
                })()}
            />
        </>
    )
}
