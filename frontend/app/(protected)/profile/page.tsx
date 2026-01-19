'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { formatDateTime } from '@/lib/tenantFormat'
import {
    ProfileCreateRequest,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    HospitalListResponse,
    HospitalResponse,
} from '@/types/api'
import { useEffect, useState } from 'react'

interface AccountOption {
    id: number
    email: string
    name: string
}

export default function ProfilePage() {
    const { settings } = useTenantSettings()
    const [profiles, setProfiles] = useState<ProfileResponse[]>([])
    const [accounts, setAccounts] = useState<AccountOption[]>([])
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [loadingAccounts, setLoadingAccounts] = useState(true)
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [editingProfile, setEditingProfile] = useState<ProfileResponse | null>(null)
    const [formData, setFormData] = useState({
        account_id: null as number | null,
        hospital_id: null as number | null,
        attribute: '{}',
    })
    const [originalFormData, setOriginalFormData] = useState({ ...formData })
    const [submitting, setSubmitting] = useState(false)
    const [selectedProfiles, setSelectedProfiles] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [jsonError, setJsonError] = useState<string | null>(null)

    // Carregar lista de accounts
    const loadAccounts = async () => {
        try {
            setLoadingAccounts(true)
            const response = await fetch('/api/account/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
            }

            const data: AccountOption[] = await response.json()
            setAccounts(data)
        } catch (err) {
            console.error('Erro ao carregar accounts:', err)
        } finally {
            setLoadingAccounts(false)
        }
    }

    // Carregar lista de hospitals
    const loadHospitals = async () => {
        try {
            setLoadingHospitals(true)
            const response = await fetch('/api/hospital/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
            }

            const data: HospitalListResponse = await response.json()
            setHospitals(data.items)
        } catch (err) {
            console.error('Erro ao carregar hospitals:', err)
        } finally {
            setLoadingHospitals(false)
        }
    }

    // Carregar lista de profiles
    const loadProfiles = async () => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch('/api/profile/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
            }

            const data: ProfileListResponse = await response.json()
            setProfiles(data.items)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar profiles'
            setError(message)
            console.error('Erro ao carregar profiles:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadAccounts()
        loadHospitals()
        loadProfiles()
    }, [])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingProfile) {
            return formData.account_id !== null || formData.hospital_id !== null || formData.attribute.trim() !== '{}'
        }
        return (
            formData.account_id !== originalFormData.account_id ||
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
        setFormData({ account_id: null, hospital_id: null, attribute: '{}' })
        setOriginalFormData({ account_id: null, hospital_id: null, attribute: '{}' })
        setEditingProfile(null)
        setShowEditArea(true)
        setError(null)
        setJsonError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (profile: ProfileResponse) => {
        const initialData = {
            account_id: profile.account_id,
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

    // Cancelar edição
    const handleCancel = () => {
        setFormData({ account_id: null, hospital_id: null, attribute: '{}' })
        setOriginalFormData({ account_id: null, hospital_id: null, attribute: '{}' })
        setEditingProfile(null)
        setShowEditArea(false)
        setError(null)
        setJsonError(null)
    }

    // Submeter formulário (criar ou editar)
    const handleSave = async () => {
        // Validar account_id
        if (!formData.account_id) {
            setError('Account é obrigatório')
            return
        }

        // Validar JSON
        const jsonValidation = validateJson(formData.attribute)
        if (!jsonValidation.valid) {
            setJsonError(jsonValidation.error || 'JSON inválido')
            setError(jsonValidation.error || 'JSON inválido')
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

                const response = await fetch(`/api/profile/${editingProfile.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify(updateData),
                })

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}))
                    throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
                }
            } else {
                // Criar novo profile
                const createData: ProfileCreateRequest = {
                    account_id: formData.account_id,
                    hospital_id: formData.hospital_id || null,
                    attribute: attributeObj,
                }

                const response = await fetch('/api/profile', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify(createData),
                })

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}))
                    throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
                }
            }

            // Recarregar lista e limpar formulário
            await loadProfiles()
            setFormData({ account_id: null, hospital_id: null, attribute: '{}' })
            setOriginalFormData({ account_id: null, hospital_id: null, attribute: '{}' })
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

    // Deletar profiles selecionados
    const handleDeleteSelected = async () => {
        if (selectedProfiles.size === 0) return

        if (!confirm(`Tem certeza que deseja deletar ${selectedProfiles.size} profile(s)?`)) {
            return
        }

        setDeleting(true)
        setError(null)

        try {
            const deletePromises = Array.from(selectedProfiles).map(async (profileId) => {
                const response = await fetch(`/api/profile/${profileId}`, {
                    method: 'DELETE',
                    credentials: 'include',
                })

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Sessão expirada. Por favor, faça login novamente.')
                    }
                    const errorData = await response.json().catch(() => ({
                        detail: `Erro HTTP ${response.status}`,
                    }))
                    throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
                }

                return profileId
            })

            await Promise.all(deletePromises)

            setProfiles(profiles.filter((profile) => !selectedProfiles.has(profile.id)))
            setSelectedProfiles(new Set())

            await loadProfiles()
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao deletar profiles. Tente novamente.'
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
        <div className="p-4 sm:p-6 lg:p-8 min-w-0">
            <div className="mb-4 sm:mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">Profiles</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Gerencie os perfis de usuários com atributos customizados
                    </p>
                </div>
                <button
                    onClick={handleCreateClick}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md transition-colors text-sm font-medium"
                >
                    Criar Profile
                </button>
            </div>

            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-800 text-sm">
                    {error}
                </div>
            )}

            {/* Área de edição */}
            {isEditing && (
                <div className="mb-4 sm:mb-6 bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">
                        {editingProfile ? 'Editar Profile' : 'Criar Profile'}
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <label htmlFor="account_id" className="block text-sm font-medium text-gray-700 mb-2">
                                Account <span className="text-red-500">*</span>
                            </label>
                            <select
                                id="account_id"
                                value={formData.account_id || ''}
                                onChange={(e) =>
                                    setFormData({ ...formData, account_id: e.target.value ? parseInt(e.target.value) : null })
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                required
                                disabled={submitting || editingProfile !== null || loadingAccounts}
                            >
                                <option value="">Selecione um account</option>
                                {accounts.map((account) => (
                                    <option key={account.id} value={account.id}>
                                        {account.name} ({account.email})
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
                                <option value="">Nenhum</option>
                                {hospitals.map((hospital) => (
                                    <option key={hospital.id} value={hospital.id}>
                                        {hospital.name}
                                    </option>
                                ))}
                            </select>
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
                                className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm ${
                                    jsonError ? 'border-red-300' : 'border-gray-300'
                                }`}
                                disabled={submitting}
                            />
                            {jsonError && (
                                <p className="mt-1 text-sm text-red-600">{jsonError}</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    <p className="mt-2 text-sm text-gray-600">Carregando profiles...</p>
                </div>
            ) : profiles.length === 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                    <p className="text-gray-600">Nenhum profile cadastrado ainda.</p>
                </div>
            ) : (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    ID
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Account
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Hospital
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Criado em
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Ações
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {profiles.map((profile) => {
                                const isSelected = selectedProfiles.has(profile.id)
                                const account = accounts.find((a) => a.id === profile.account_id)
                                const hospital = hospitals.find((h) => h.id === profile.hospital_id)
                                return (
                                    <tr
                                        key={profile.id}
                                        className={isSelected ? 'bg-red-50' : ''}
                                    >
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {profile.id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {account ? `${account.name} (${account.email})` : profile.account_id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {hospital ? hospital.name : profile.hospital_id || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {settings
                                                ? formatDateTime(profile.created_at, settings)
                                                : new Date(profile.created_at).toLocaleDateString('pt-BR', {
                                                    day: '2-digit',
                                                    month: '2-digit',
                                                    year: 'numeric',
                                                })}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        toggleProfileSelection(profile.id)
                                                    }}
                                                    disabled={deleting}
                                                    className={`px-2 py-1 rounded transition-colors ${
                                                        isSelected
                                                            ? 'text-red-700 bg-red-100'
                                                            : 'text-gray-400'
                                                    }`}
                                                    title={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                                >
                                                    <svg
                                                        className="w-4 h-4"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            strokeWidth={2}
                                                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                                        />
                                                    </svg>
                                                </button>
                                                <button
                                                    onClick={() => handleEditClick(profile)}
                                                    className="px-2 py-1 rounded text-blue-600 transition-colors"
                                                    title="Editar profile"
                                                >
                                                    <svg
                                                        className="w-4 h-4"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            strokeWidth={2}
                                                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                                        />
                                                    </svg>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            <BottomActionBarSpacer />

            <BottomActionBar
                leftContent={
                    <div className="text-sm text-gray-600">
                        Total de profiles: <span className="font-medium">{profiles.length}</span>
                        {selectedProfiles.size > 0 && (
                            <span className="ml-2 sm:ml-4 text-red-600">
                                {selectedProfiles.size} marcado{selectedProfiles.size > 1 ? 's' : ''} para exclusão
                            </span>
                        )}
                    </div>
                }
                buttons={(() => {
                    const buttons = []
                    if (isEditing) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting,
                        })
                    }
                    if (isEditing && hasChanges()) {
                        buttons.push({
                            label: submitting ? 'Salvando...' : 'Salvar',
                            onClick: handleSave,
                            variant: 'primary' as const,
                            disabled: submitting || !!jsonError,
                            loading: submitting,
                        })
                    }
                    if (selectedProfiles.size > 0) {
                        buttons.push({
                            label: 'Excluir',
                            onClick: handleDeleteSelected,
                            variant: 'primary' as const,
                            disabled: deleting || submitting,
                            loading: deleting,
                        })
                    }
                    return buttons
                })()}
            />
        </div>
    )
}
