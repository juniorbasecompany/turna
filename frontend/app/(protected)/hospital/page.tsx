'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { ColorPicker } from '@/components/ColorPicker'
import { CreateCard } from '@/components/CreateCard'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { getCardContainerClasses } from '@/lib/cardStyles'
import {
    HospitalCreateRequest,
    HospitalListResponse,
    HospitalResponse,
    HospitalUpdateRequest,
} from '@/types/api'
import { extractErrorMessage } from '@/lib/api'
import { useEffect, useState } from 'react'

export default function HospitalPage() {
    const { settings } = useTenantSettings()
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [editingHospital, setEditingHospital] = useState<HospitalResponse | null>(null)
    const [formData, setFormData] = useState({ name: '', prompt: '', color: null as string | null })
    const [originalFormData, setOriginalFormData] = useState({ name: '', prompt: '', color: null as string | null })
    const [submitting, setSubmitting] = useState(false)
    const [selectedHospitals, setSelectedHospitals] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)

    // Carregar lista de hospitais
    const loadHospitals = async () => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch('/api/hospital/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
            }

            const data: HospitalListResponse = await response.json()
            setHospitals(data.items)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar hospitais'
            setError(message)
            console.error('Erro ao carregar hospitais:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadHospitals()
    }, [])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        // Se está criando (não há editingHospital), qualquer campo preenchido é mudança
        if (!editingHospital) {
            return formData.name.trim() !== '' || (formData.prompt || '').trim() !== '' || formData.color !== null
        }
        // Se está editando, compara com os valores originais
        return (
            formData.name.trim() !== originalFormData.name.trim() ||
            (formData.prompt || '').trim() !== (originalFormData.prompt || '').trim() ||
            formData.color !== originalFormData.color
        )
    }

    // Verificar se está em modo de edição/criação
    // Estado separado para controlar quando mostrar a área de edição
    const [showEditArea, setShowEditArea] = useState(false)
    const isEditing = showEditArea

    // Abrir modo de criação
    const handleCreateClick = () => {
        setFormData({ name: '', prompt: '', color: null })
        setOriginalFormData({ name: '', prompt: '', color: null })
        setEditingHospital(null)
        setShowEditArea(true)
        setError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (hospital: HospitalResponse) => {
        const initialData = { name: hospital.name, prompt: hospital.prompt || '', color: hospital.color || null }
        setFormData(initialData)
        setOriginalFormData(initialData)
        setEditingHospital(hospital)
        setShowEditArea(true)
        setError(null)
    }

    // Cancelar edição e/ou seleção
    const handleCancel = () => {
        setFormData({ name: '', prompt: '', color: null })
        setOriginalFormData({ name: '', prompt: '', color: null })
        setEditingHospital(null)
        setShowEditArea(false)
        setSelectedHospitals(new Set())
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

            if (editingHospital) {
                // Editar hospital existente
                const updateData: HospitalUpdateRequest = {
                    name: formData.name.trim(),
                    prompt: formData.prompt ? formData.prompt.trim() : undefined,
                    color: formData.color || null,
                }

                const response = await fetch(`/api/hospital/${editingHospital.id}`, {
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
                // Criar novo hospital
                const createData: HospitalCreateRequest = {
                    name: formData.name.trim(),
                    prompt: formData.prompt ? formData.prompt.trim() || undefined : undefined,
                    color: formData.color || undefined,
                }

                const response = await fetch('/api/hospital', {
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
            await loadHospitals()
            setFormData({ name: '', prompt: '', color: null })
            setOriginalFormData({ name: '', prompt: '', color: null })
            setEditingHospital(null)
            setShowEditArea(false)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar hospital'
            setError(message)
            console.error('Erro ao salvar hospital:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de hospital para exclusão
    const toggleHospitalSelection = (hospitalId: number) => {
        setSelectedHospitals((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(hospitalId)) {
                newSet.delete(hospitalId)
            } else {
                newSet.add(hospitalId)
            }
            return newSet
        })
    }

    // Excluir hospitais selecionados
    const handleDeleteSelected = async () => {
        if (selectedHospitals.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            // Excluir todos os hospitais selecionados em paralelo
            const deletePromises = Array.from(selectedHospitals).map(async (hospitalId) => {
                const response = await fetch(`/api/hospital/${hospitalId}`, {
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

                return hospitalId
            })

            await Promise.all(deletePromises)

            // Remover hospitais deletados da lista
            setHospitals(hospitals.filter((hospital) => !selectedHospitals.has(hospital.id)))
            setSelectedHospitals(new Set())

            // Recarregar lista para garantir sincronização
            await loadHospitals()
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao excluir hospitais. Tente novamente.'
            )
        } finally {
            setDeleting(false)
        }
    }

    return (
        <>
            {/* Área de edição */}
            {isEditing && (
                <div className="p-4 sm:p-6 lg:p-8 min-w-0">
                <div className="mb-4 sm:mb-6 bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">
                        {editingHospital ? 'Editar Hospital' : 'Criar Hospital'}
                    </h2>
                    <div className="space-y-4">
                        <div className="flex flex-col sm:flex-row gap-4 items-start">
                            <div className="flex-1 min-w-0">
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
                            <div className="flex-shrink-0">
                                <ColorPicker
                                    value={formData.color}
                                    onChange={(color) => setFormData({ ...formData, color })}
                                    label="Cor"
                                    disabled={submitting}
                                />
                            </div>
                        </div>
                        <div>
                            <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
                                Como os arquivos devem ser lidos?
                            </label>
                            <p className="text-xs text-gray-500 mb-2">
                                Escreva o prompt com as instruções para a IA extrair as demandas dos arquivos deste hospital.
                            </p>
                            <textarea
                                id="prompt"
                                value={formData.prompt || ''}
                                onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                                rows={15}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                                disabled={submitting}
                            />
                        </div>
                    </div>
                </div>
            </div>
            )}

            <CardPanel
                title="Hospitais"
                description="Gerencie os hospitais e seus prompts de extração"
                totalCount={hospitals.length}
                selectedCount={selectedHospitals.size}
                loading={loading}
                loadingMessage="Carregando hospitais..."
                emptyMessage="Nenhum hospital cadastrado ainda."
                countLabel="Total de hospitais"
                createCard={
                    <CreateCard
                        label="Criar novo hospital"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
            >
                {hospitals.map((hospital) => {
                            const isSelected = selectedHospitals.has(hospital.id)
                            return (
                                <div
                                    key={hospital.id}
                                    className={getCardContainerClasses(isSelected)}
                                >
                                    {/* 1. Corpo - Ícone de hospital e nome */}
                                    <div className="mb-3">
                                        <div
                                            className="h-40 sm:h-48 rounded-lg flex items-center justify-center"
                                            style={{
                                                backgroundColor: hospital.color || '#f1f5f9',
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
                                                            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                                                        />
                                                    </svg>
                                                </div>
                                                <h3
                                                    className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                        }`}
                                                    title={hospital.name}
                                                >
                                                    {hospital.name}
                                                </h3>
                                            </div>
                                        </div>
                                    </div>

                                    {/* 3. Rodapé - Metadados e ações */}
                                    <CardFooter
                                        isSelected={isSelected}
                                        date={hospital.created_at}
                                        settings={settings}
                                        onToggleSelection={(e) => {
                                            e.stopPropagation()
                                            toggleHospitalSelection(hospital.id)
                                        }}
                                        onEdit={() => handleEditClick(hospital)}
                                        disabled={deleting}
                                        deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                        editTitle="Editar hospital"
                                    />
                                </div>
                            )
                        })}
            </CardPanel>

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <BottomActionBarSpacer />

            {/* Barra inferior fixa com ações */}
            <BottomActionBar
                leftContent={(() => {
                    // Mostra erro no BottomActionBar apenas se houver botões de ação
                    const hasButtons = isEditing || selectedHospitals.size > 0
                    return hasButtons ? (error || undefined) : undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    // Botão Cancelar (aparece se houver edição OU seleção)
                    if (isEditing || selectedHospitals.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    // Botão Excluir (aparece se houver seleção)
                    if (selectedHospitals.size > 0) {
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
