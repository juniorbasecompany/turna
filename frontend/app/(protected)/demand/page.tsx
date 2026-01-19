'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import { CardActionButtons } from '@/components/CardActionButtons'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { extractErrorMessage } from '@/lib/api'
import { getCardContainerClasses, getCardSecondaryTextClasses, getCardTextClasses } from '@/lib/cardStyles'
import { formatDateTime } from '@/lib/tenantFormat'
import {
    DemandCreateRequest,
    DemandListResponse,
    DemandResponse,
    DemandUpdateRequest,
    HospitalListResponse,
    HospitalResponse,
} from '@/types/api'
import { useEffect, useState } from 'react'

export default function DemandPage() {
    const { settings } = useTenantSettings()
    const [demands, setDemands] = useState<DemandResponse[]>([])
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [editingDemand, setEditingDemand] = useState<DemandResponse | null>(null)

    type DemandFormData = {
        hospital_id: number | null
        job_id: number | null
        room: string
        start_time: Date | null
        end_time: Date | null
        procedure: string
        anesthesia_type: string
        complexity: string
        skills: string[]
        priority: string | null
        is_pediatric: boolean
        notes: string
        source: Record<string, unknown> | null
    }

    const [formData, setFormData] = useState<DemandFormData>({
        hospital_id: null,
        job_id: null,
        room: '',
        start_time: null,
        end_time: null,
        procedure: '',
        anesthesia_type: '',
        complexity: '',
        skills: [],
        priority: null,
        is_pediatric: false,
        notes: '',
        source: null,
    })
    const [originalFormData, setOriginalFormData] = useState<DemandFormData>({ ...formData })
    const [submitting, setSubmitting] = useState(false)
    const [selectedDemands, setSelectedDemands] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [skillsInput, setSkillsInput] = useState('')

    // Carregar lista de hospitais
    const loadHospitals = async () => {
        try {
            setLoadingHospitals(true)
            const response = await fetch('/api/hospital/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (response.ok) {
                const data: HospitalListResponse = await response.json()
                setHospitals(data.items)
            }
        } catch (err) {
            console.error('Erro ao carregar hospitais:', err)
        } finally {
            setLoadingHospitals(false)
        }
    }

    // Carregar lista de demandas
    const loadDemands = async () => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch('/api/demand/list', {
                method: 'GET',
                credentials: 'include',
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
            }

            const data: DemandListResponse = await response.json()
            setDemands(data.items)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar demandas'
            setError(message)
            console.error('Erro ao carregar demandas:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadHospitals()
        loadDemands()
    }, [])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingDemand) {
            return (
                formData.procedure.trim() !== '' ||
                formData.start_time !== null ||
                formData.end_time !== null ||
                formData.hospital_id !== null ||
                formData.room.trim() !== ''
            )
        }
        // Comparação mais robusta para incluir Date objects
        return (
            formData.procedure !== originalFormData.procedure ||
            formData.start_time?.getTime() !== originalFormData.start_time?.getTime() ||
            formData.end_time?.getTime() !== originalFormData.end_time?.getTime() ||
            formData.hospital_id !== originalFormData.hospital_id ||
            formData.room !== originalFormData.room ||
            formData.anesthesia_type !== originalFormData.anesthesia_type ||
            formData.complexity !== originalFormData.complexity ||
            JSON.stringify(formData.skills) !== JSON.stringify(originalFormData.skills) ||
            formData.priority !== originalFormData.priority ||
            formData.is_pediatric !== originalFormData.is_pediatric ||
            formData.notes !== originalFormData.notes ||
            JSON.stringify(formData.source) !== JSON.stringify(originalFormData.source)
        )
    }

    const [showEditArea, setShowEditArea] = useState(false)
    const isEditing = showEditArea

    // Abrir modo de criação
    const handleCreateClick = () => {
        const newFormData: DemandFormData = {
            hospital_id: null,
            job_id: null,
            room: '',
            start_time: null,
            end_time: null,
            procedure: '',
            anesthesia_type: '',
            complexity: '',
            skills: [],
            priority: null,
            is_pediatric: false,
            notes: '',
            source: null,
        }
        setFormData(newFormData)
        setOriginalFormData({ ...newFormData })
        setEditingDemand(null)
        setSkillsInput('')
        setShowEditArea(true)
        setError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (demand: DemandResponse) => {
        const initialData: DemandFormData = {
            hospital_id: demand.hospital_id,
            job_id: demand.job_id,
            room: demand.room || '',
            start_time: demand.start_time ? new Date(demand.start_time) : null,
            end_time: demand.end_time ? new Date(demand.end_time) : null,
            procedure: demand.procedure,
            anesthesia_type: demand.anesthesia_type || '',
            complexity: demand.complexity || '',
            skills: demand.skills || [],
            priority: demand.priority,
            is_pediatric: demand.is_pediatric,
            notes: demand.notes || '',
            source: demand.source,
        }
        setFormData(initialData)
        setOriginalFormData({ ...initialData })
        setEditingDemand(demand)
        setSkillsInput((demand.skills || []).join(', '))
        setShowEditArea(true)
        setError(null)
    }

    // Cancelar edição e/ou seleção
    const handleCancel = () => {
        const resetData: DemandFormData = {
            hospital_id: null,
            job_id: null,
            room: '',
            start_time: null,
            end_time: null,
            procedure: '',
            anesthesia_type: '',
            complexity: '',
            skills: [],
            priority: null,
            is_pediatric: false,
            notes: '',
            source: null,
        }
        setFormData(resetData)
        setOriginalFormData({ ...resetData })
        setEditingDemand(null)
        setSkillsInput('')
        setShowEditArea(false)
        setSelectedDemands(new Set())
        setError(null)
    }

    // Atualizar skills a partir do input
    const updateSkills = (input: string) => {
        setSkillsInput(input)
        const skillsArray = input
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        setFormData({ ...formData, skills: skillsArray })
    }

    // Submeter formulário (criar ou editar)
    const handleSave = async () => {
        if (!formData.procedure.trim()) {
            setError('Procedimento é obrigatório')
            return
        }

        if (!formData.start_time || !formData.end_time) {
            setError('Data/hora de início e fim são obrigatórias')
            return
        }

        const startIso = formData.start_time.toISOString()
        const endIso = formData.end_time.toISOString()

        if (formData.end_time <= formData.start_time) {
            setError('Data/hora de fim deve ser maior que a de início')
            return
        }

        try {
            setSubmitting(true)
            setError(null)

            if (editingDemand) {
                // Editar demanda existente
                const updateData: DemandUpdateRequest = {
                    hospital_id: formData.hospital_id,
                    job_id: formData.job_id,
                    room: formData.room.trim() || null,
                    start_time: startIso,
                    end_time: endIso,
                    procedure: formData.procedure.trim(),
                    anesthesia_type: formData.anesthesia_type.trim() || null,
                    complexity: formData.complexity.trim() || null,
                    skills: formData.skills.length > 0 ? formData.skills : null,
                    priority: formData.priority || null,
                    is_pediatric: formData.is_pediatric,
                    notes: formData.notes.trim() || null,
                    source: formData.source,
                }

                const response = await fetch(`/api/demand/${editingDemand.id}`, {
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
                // Criar nova demanda
                const createData: DemandCreateRequest = {
                    hospital_id: formData.hospital_id,
                    job_id: formData.job_id,
                    room: formData.room.trim() || null,
                    start_time: startIso,
                    end_time: endIso,
                    procedure: formData.procedure.trim(),
                    anesthesia_type: formData.anesthesia_type.trim() || null,
                    complexity: formData.complexity.trim() || null,
                    skills: formData.skills.length > 0 ? formData.skills : null,
                    priority: formData.priority || null,
                    is_pediatric: formData.is_pediatric,
                    notes: formData.notes.trim() || null,
                    source: formData.source,
                }

                const response = await fetch('/api/demand', {
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
            await loadDemands()
            handleCancel()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar demanda'
            setError(message)
            console.error('Erro ao salvar demanda:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de demanda para exclusão
    const toggleDemandSelection = (demandId: number) => {
        setSelectedDemands((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(demandId)) {
                newSet.delete(demandId)
            } else {
                newSet.add(demandId)
            }
            return newSet
        })
    }

    // Excluir demandas selecionadas
    const handleDeleteSelected = async () => {
        if (selectedDemands.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            const deletePromises = Array.from(selectedDemands).map(async (demandId) => {
                const response = await fetch(`/api/demand/${demandId}`, {
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

                return demandId
            })

            await Promise.all(deletePromises)

            setDemands(demands.filter((demand) => !selectedDemands.has(demand.id)))
            setSelectedDemands(new Set())

            await loadDemands()
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao excluir demandas. Tente novamente.'
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
                            {editingDemand ? 'Editar Demanda' : 'Criar Demanda'}
                        </h2>
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="hospital_id" className="block text-sm font-medium text-gray-700 mb-2">
                                        Hospital
                                    </label>
                                    <select
                                        id="hospital_id"
                                        value={formData.hospital_id || ''}
                                        onChange={(e) =>
                                            setFormData({
                                                ...formData,
                                                hospital_id: e.target.value ? parseInt(e.target.value) : null,
                                            })
                                        }
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting || loadingHospitals}
                                    >
                                        <option value="">Selecione um hospital</option>
                                        {hospitals.map((hospital) => (
                                            <option key={hospital.id} value={hospital.id}>
                                                {hospital.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="procedure" className="block text-sm font-medium text-gray-700 mb-2">
                                        Procedimento <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        id="procedure"
                                        value={formData.procedure}
                                        onChange={(e) => setFormData({ ...formData, procedure: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        required
                                        disabled={submitting}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <TenantDateTimePicker
                                        id="start_time"
                                        label="Data/Hora Início"
                                        value={formData.start_time}
                                        onChange={(date) => setFormData({ ...formData, start_time: date })}
                                        disabled={submitting}
                                    />
                                </div>
                                <div>
                                    <TenantDateTimePicker
                                        id="end_time"
                                        label="Data/Hora Fim"
                                        value={formData.end_time}
                                        onChange={(date) => setFormData({ ...formData, end_time: date })}
                                        disabled={submitting}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="room" className="block text-sm font-medium text-gray-700 mb-2">
                                        Sala/Quarto
                                    </label>
                                    <input
                                        type="text"
                                        id="room"
                                        value={formData.room}
                                        onChange={(e) => setFormData({ ...formData, room: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </div>
                                <div>
                                    <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-2">
                                        Prioridade
                                    </label>
                                    <select
                                        id="priority"
                                        value={formData.priority || ''}
                                        onChange={(e) =>
                                            setFormData({
                                                ...formData,
                                                priority: e.target.value || null,
                                            })
                                        }
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    >
                                        <option value="">Nenhuma</option>
                                        <option value="Urgente">Urgente</option>
                                        <option value="Emergência">Emergência</option>
                                    </select>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="anesthesia_type" className="block text-sm font-medium text-gray-700 mb-2">
                                        Tipo de Anestesia
                                    </label>
                                    <input
                                        type="text"
                                        id="anesthesia_type"
                                        value={formData.anesthesia_type}
                                        onChange={(e) => setFormData({ ...formData, anesthesia_type: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </div>
                                <div>
                                    <label htmlFor="complexity" className="block text-sm font-medium text-gray-700 mb-2">
                                        Complexidade
                                    </label>
                                    <input
                                        type="text"
                                        id="complexity"
                                        value={formData.complexity}
                                        onChange={(e) => setFormData({ ...formData, complexity: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </div>
                            </div>

                            <div>
                                <label htmlFor="skills" className="block text-sm font-medium text-gray-700 mb-2">
                                    Habilidades (separadas por vírgula)
                                </label>
                                <input
                                    type="text"
                                    id="skills"
                                    value={skillsInput}
                                    onChange={(e) => updateSkills(e.target.value)}
                                    placeholder="Ex: Obstétrica, Cardíaca"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    disabled={submitting}
                                />
                            </div>

                            <div>
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={formData.is_pediatric}
                                        onChange={(e) => setFormData({ ...formData, is_pediatric: e.target.checked })}
                                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        disabled={submitting}
                                    />
                                    <span className="ml-2 text-sm text-gray-700">Pediátrica</span>
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
                </div>
            )}

            <CardPanel
                title="Demandas"
                description="Gerencie as demandas cirúrgicas"
                totalCount={demands.length}
                selectedCount={selectedDemands.size}
                loading={loading}
                loadingMessage="Carregando demandas..."
                emptyMessage="Nenhuma demanda cadastrada ainda."
                countLabel="Total de demandas"
                error={(() => {
                    // Mostra erro no CardPanel apenas se não houver botões de ação
                    const hasButtons = isEditing || selectedDemands.size > 0
                    return hasButtons ? null : error
                })()}
                createCard={
                    <CreateCard
                        label="Criar nova demanda"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
            >
                {demands.map((demand) => {
                    const isSelected = selectedDemands.has(demand.id)
                    const hospital = hospitals.find((h) => h.id === demand.hospital_id)
                    return (
                        <div
                            key={demand.id}
                            className={getCardContainerClasses(isSelected)}
                        >
                            {/* Cabeçalho - Ícone e Hospital */}
                            <div className="mb-3 flex items-center gap-2">
                                <div className="flex-shrink-0">
                                    <svg
                                        className="w-5 h-5"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        style={{
                                            color: hospital?.color || '#64748b',
                                        }}
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                                        />
                                    </svg>
                                </div>
                                {hospital && (
                                    <h4
                                        className={`text-sm font-semibold truncate flex-1 ${getCardTextClasses(isSelected)}`}
                                        title={hospital.name}
                                    >
                                        {hospital.name}
                                    </h4>
                                )}
                            </div>

                            {/* Corpo - Detalhes da demanda */}
                            <div className="mb-3 space-y-2">
                                <div>
                                    <h3
                                        className={`text-base font-semibold mb-1 ${isSelected ? 'text-red-900' : 'text-gray-900'}`}
                                        title={demand.procedure}
                                    >
                                        {demand.procedure}
                                    </h3>
                                    <div className="flex flex-wrap gap-1 mb-2">
                                        {demand.is_pediatric && (
                                            <span className="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 rounded">
                                                👶 Pediátrica
                                            </span>
                                        )}
                                        {demand.priority && (
                                            <span
                                                className={`px-2 py-0.5 text-xs font-medium rounded ${demand.priority === 'Urgente'
                                                    ? 'bg-orange-100 text-orange-800'
                                                    : 'bg-red-100 text-red-800'
                                                    }`}
                                            >
                                                {demand.priority}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="space-y-1 text-sm">
                                    {demand.room && (
                                        <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                            <span className="font-medium">Sala:</span> {demand.room}
                                        </p>
                                    )}
                                    <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                        <span className="font-medium">Início:</span>{' '}
                                        {settings
                                            ? formatDateTime(demand.start_time, settings)
                                            : new Date(demand.start_time).toLocaleString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                    </p>
                                    <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                        <span className="font-medium">Fim:</span>{' '}
                                        {settings
                                            ? formatDateTime(demand.end_time, settings)
                                            : new Date(demand.end_time).toLocaleString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                    </p>
                                    {demand.anesthesia_type && (
                                        <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                            <span className="font-medium">Anestesia:</span> {demand.anesthesia_type}
                                        </p>
                                    )}
                                    {demand.complexity && (
                                        <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                            <span className="font-medium">Complexidade:</span> {demand.complexity}
                                        </p>
                                    )}
                                    {demand.skills && demand.skills.length > 0 && (
                                        <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                            <span className="font-medium">Habilidades:</span> {demand.skills.join(', ')}
                                        </p>
                                    )}
                                    {demand.notes && (
                                        <p className={`text-xs ${isSelected ? 'text-red-700' : 'text-gray-500'} line-clamp-2`}>
                                            <span className="font-medium">Obs:</span> {demand.notes}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Rodapé - Metadados e ações */}
                            <div className="flex items-center justify-between gap-2 pt-2 border-t border-gray-200">
                                <div className="flex flex-col min-w-0 flex-1">
                                    <span className={`text-xs truncate ${getCardSecondaryTextClasses(isSelected)}`}>
                                        {settings
                                            ? formatDateTime(demand.created_at || demand.start_time, settings)
                                            : new Date(demand.created_at || demand.start_time).toLocaleDateString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric',
                                            })}
                                    </span>
                                </div>
                                <CardActionButtons
                                    isSelected={isSelected}
                                    onToggleSelection={(e) => {
                                        e.stopPropagation()
                                        toggleDemandSelection(demand.id)
                                    }}
                                    onEdit={() => handleEditClick(demand)}
                                    disabled={deleting}
                                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                    editTitle="Editar demanda"
                                />
                            </div>
                        </div>
                    )
                })}
            </CardPanel>

            <BottomActionBarSpacer />

            <BottomActionBar
                leftContent={(() => {
                    // Mostra erro no BottomActionBar apenas se houver botões de ação
                    const hasButtons = isEditing || selectedDemands.size > 0
                    return hasButtons ? (error || undefined) : undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    // Botão Cancelar (aparece se houver edição OU seleção)
                    if (isEditing || selectedDemands.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    // Botão Excluir (aparece se houver seleção)
                    if (selectedDemands.size > 0) {
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
