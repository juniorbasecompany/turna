'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
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
    const [formData, setFormData] = useState({
        hospital_id: null as number | null,
        job_id: null as number | null,
        room: '',
        start_time: '',
        end_time: '',
        procedure: '',
        anesthesia_type: '',
        complexity: '',
        skills: [] as string[],
        priority: null as string | null,
        is_pediatric: false,
        notes: '',
        source: null as Record<string, unknown> | null,
    })
    const [originalFormData, setOriginalFormData] = useState({ ...formData })
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
                throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
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

    // Converter ISO datetime para formato datetime-local
    const isoToDatetimeLocal = (iso: string): string => {
        const date = new Date(iso)
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        const hours = String(date.getHours()).padStart(2, '0')
        const minutes = String(date.getMinutes()).padStart(2, '0')
        return `${year}-${month}-${day}T${hours}:${minutes}`
    }

    // Converter datetime-local para ISO
    const datetimeLocalToIso = (local: string): string => {
        if (!local) return ''
        const date = new Date(local)
        return date.toISOString()
    }

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        if (!editingDemand) {
            return (
                formData.procedure.trim() !== '' ||
                formData.start_time !== '' ||
                formData.end_time !== '' ||
                formData.hospital_id !== null ||
                formData.room.trim() !== ''
            )
        }
        return JSON.stringify(formData) !== JSON.stringify(originalFormData)
    }

    const [showEditArea, setShowEditArea] = useState(false)
    const isEditing = showEditArea

    // Abrir modo de criação
    const handleCreateClick = () => {
        setFormData({
            hospital_id: null,
            job_id: null,
            room: '',
            start_time: '',
            end_time: '',
            procedure: '',
            anesthesia_type: '',
            complexity: '',
            skills: [],
            priority: null,
            is_pediatric: false,
            notes: '',
            source: null,
        })
        setOriginalFormData({ ...formData })
        setEditingDemand(null)
        setSkillsInput('')
        setShowEditArea(true)
        setError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (demand: DemandResponse) => {
        const initialData = {
            hospital_id: demand.hospital_id,
            job_id: demand.job_id,
            room: demand.room || '',
            start_time: demand.start_time ? isoToDatetimeLocal(demand.start_time) : '',
            end_time: demand.end_time ? isoToDatetimeLocal(demand.end_time) : '',
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
        setOriginalFormData(initialData)
        setEditingDemand(demand)
        setSkillsInput((demand.skills || []).join(', '))
        setShowEditArea(true)
        setError(null)
    }

    // Cancelar edição
    const handleCancel = () => {
        setFormData({
            hospital_id: null,
            job_id: null,
            room: '',
            start_time: '',
            end_time: '',
            procedure: '',
            anesthesia_type: '',
            complexity: '',
            skills: [],
            priority: null,
            is_pediatric: false,
            notes: '',
            source: null,
        })
        setOriginalFormData({ ...formData })
        setEditingDemand(null)
        setSkillsInput('')
        setShowEditArea(false)
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

        const startIso = datetimeLocalToIso(formData.start_time)
        const endIso = datetimeLocalToIso(formData.end_time)

        if (new Date(endIso) <= new Date(startIso)) {
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
                    throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
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
                    throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
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

    // Deletar demandas selecionadas
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
                    const errorData = await response.json().catch(() => ({
                        detail: `Erro HTTP ${response.status}`,
                    }))
                    throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
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
                    : 'Erro ao deletar demandas. Tente novamente.'
            )
        } finally {
            setDeleting(false)
        }
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 min-w-0">
            <div className="mb-4 sm:mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">Demandas</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Gerencie as demandas cirúrgicas
                    </p>
                </div>
                <button
                    onClick={handleCreateClick}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                    Criar Demanda
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
                                <label htmlFor="start_time" className="block text-sm font-medium text-gray-700 mb-2">
                                    Data/Hora Início <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="datetime-local"
                                    id="start_time"
                                    value={formData.start_time}
                                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    required
                                    disabled={submitting}
                                />
                            </div>
                            <div>
                                <label htmlFor="end_time" className="block text-sm font-medium text-gray-700 mb-2">
                                    Data/Hora Fim <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="datetime-local"
                                    id="end_time"
                                    value={formData.end_time}
                                    onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    required
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
            )}

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    <p className="mt-2 text-sm text-gray-600">Carregando demandas...</p>
                </div>
            ) : demands.length === 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                    <p className="text-gray-600">Nenhuma demanda cadastrada ainda.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {demands.map((demand) => {
                        const isSelected = selectedDemands.has(demand.id)
                        const hospital = hospitals.find((h) => h.id === demand.hospital_id)
                        return (
                            <div
                                key={demand.id}
                                className={`group rounded-xl border p-4 min-w-0 transition-all duration-200 ${
                                    isSelected
                                        ? 'border-red-300 ring-2 ring-red-200 bg-red-50'
                                        : 'border-slate-400 bg-white hover:border-slate-500'
                                }`}
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
                                            className={`text-sm font-semibold truncate flex-1 ${isSelected ? 'text-red-900' : 'text-gray-900'}`}
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
                                                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                                                        demand.priority === 'Urgente'
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
                                        <span className={`text-xs truncate ${isSelected ? 'text-red-900' : 'text-slate-500'}`}>
                                            {settings
                                                ? formatDateTime(demand.created_at || demand.start_time, settings)
                                                : new Date(demand.created_at || demand.start_time).toLocaleDateString('pt-BR', {
                                                    day: '2-digit',
                                                    month: '2-digit',
                                                    year: 'numeric',
                                                })}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1 shrink-0">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                toggleDemandSelection(demand.id)
                                            }}
                                            disabled={deleting}
                                            className={`shrink-0 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                                                isSelected
                                                    ? 'text-red-700 bg-red-100 opacity-100'
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
                                            onClick={() => handleEditClick(demand)}
                                            className="shrink-0 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                            title="Editar demanda"
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
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            <BottomActionBarSpacer />

            <BottomActionBar
                leftContent={
                    <div className="text-sm text-gray-600">
                        Total de demandas: <span className="font-medium">{demands.length}</span>
                        {selectedDemands.size > 0 && (
                            <span className="ml-2 sm:ml-4 text-red-600">
                                {selectedDemands.size} marcada{selectedDemands.size > 1 ? 's' : ''} para exclusão
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
                            disabled: submitting,
                            loading: submitting,
                        })
                    }
                    if (selectedDemands.size > 0) {
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
