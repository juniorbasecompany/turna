'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterPanel } from '@/components/FilterPanel'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useEntityPage } from '@/hooks/useEntityPage'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { protectedFetch } from '@/lib/api'
import { formatDateTime } from '@/lib/tenantFormat'
import {
    DemandCreateRequest,
    DemandResponse,
    DemandUpdateRequest,
    HospitalListResponse,
    HospitalResponse,
} from '@/types/api'
import { useEffect, useMemo, useState } from 'react'

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

export default function DemandPage() {
    const { settings } = useTenantSettings()
    
    // Estados auxiliares (não gerenciados por useEntityPage)
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [procedureFilter, setProcedureFilter] = useState('')
    const [skillsInput, setSkillsInput] = useState('')

    // Configuração inicial
    const initialFormData: DemandFormData = {
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

    // Mapeamentos
    const mapEntityToFormData = (demand: DemandResponse): DemandFormData => {
        return {
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
    }

    const mapFormDataToCreateRequest = (formData: DemandFormData): DemandCreateRequest => {
        const startIso = formData.start_time?.toISOString()
        const endIso = formData.end_time?.toISOString()
        
        return {
            hospital_id: formData.hospital_id,
            job_id: formData.job_id,
            room: formData.room.trim() || null,
            start_time: startIso!,
            end_time: endIso!,
            procedure: formData.procedure.trim(),
            anesthesia_type: formData.anesthesia_type.trim() || null,
            complexity: formData.complexity.trim() || null,
            skills: formData.skills.length > 0 ? formData.skills : null,
            priority: formData.priority || null,
            is_pediatric: formData.is_pediatric,
            notes: formData.notes.trim() || null,
            source: formData.source,
        }
    }

    const mapFormDataToUpdateRequest = (formData: DemandFormData): DemandUpdateRequest => {
        const startIso = formData.start_time?.toISOString()
        const endIso = formData.end_time?.toISOString()
        
        return {
            hospital_id: formData.hospital_id,
            job_id: formData.job_id,
            room: formData.room.trim() || null,
            start_time: startIso!,
            end_time: endIso!,
            procedure: formData.procedure.trim(),
            anesthesia_type: formData.anesthesia_type.trim() || null,
            complexity: formData.complexity.trim() || null,
            skills: formData.skills.length > 0 ? formData.skills : null,
            priority: formData.priority || null,
            is_pediatric: formData.is_pediatric,
            notes: formData.notes.trim() || null,
            source: formData.source,
        }
    }

    // Validação
    const validateFormData = (formData: DemandFormData): string | null => {
        if (!formData.procedure.trim()) {
            return 'Procedimento é obrigatório'
        }
        
        if (!formData.start_time || !formData.end_time) {
            return 'Data/hora de início e fim são obrigatórias'
        }
        
        if (formData.end_time <= formData.start_time) {
            return 'Data/hora de fim deve ser maior que a de início'
        }
        
        return null
    }

    // isEmptyCheck
    const isEmptyCheck = (formData: DemandFormData): boolean => {
        return (
            formData.procedure.trim() === '' &&
            formData.start_time === null &&
            formData.end_time === null &&
            formData.hospital_id === null &&
            formData.room.trim() === ''
        )
    }

    // useEntityPage
    const {
        items: demands,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingDemand,
        isEditing,
        hasChanges,
        handleCreateClick,
        handleEditClick,
        handleCancel,
        selectedItems: selectedDemands,
        toggleSelection: toggleDemandSelection,
        selectedCount: selectedDemandsCount,
        pagination,
        total,
        paginationHandlers,
        handleSave,
        handleDeleteSelected,
        actionBarErrorProps,
    } = useEntityPage<DemandFormData, DemandResponse, DemandCreateRequest, DemandUpdateRequest>({
        endpoint: '/api/demand',
        entityName: 'demanda',
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
    })

    // Carregar lista de hospitais (mantido separado)
    const loadHospitals = async () => {
        try {
            setLoadingHospitals(true)
            const data = await protectedFetch<HospitalListResponse>('/api/hospital/list')
            setHospitals(data.items)
        } catch (err) {
            // Exibir erro no ActionBar
            const message = err instanceof Error ? err.message : 'Erro ao carregar hospitais'
            setError(message)
            console.error('Erro ao carregar hospitais:', err)
        } finally {
            setLoadingHospitals(false)
        }
    }

    useEffect(() => {
        loadHospitals()
    }, [])

    // Wrappers customizados para skillsInput
    const handleCreateClickCustom = () => {
        handleCreateClick()
        setSkillsInput('')
    }

    const handleEditClickCustom = (demand: DemandResponse) => {
        handleEditClick(demand)
        setSkillsInput((demand.skills || []).join(', '))
    }

    const handleCancelCustom = () => {
        handleCancel()
        setSkillsInput('')
    }

    // Filtrar demandas por procedimento (filtro no frontend)
    const filteredDemands = useMemo(() => {
        if (!procedureFilter.trim()) {
            return demands
        }
        const filterLower = procedureFilter.toLowerCase().trim()
        return demands.filter((demand) => demand.procedure.toLowerCase().includes(filterLower))
    }, [demands, procedureFilter])

    // Atualizar skills a partir do input
    const updateSkills = (input: string) => {
        setSkillsInput(input)
        const skillsArray = input
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        setFormData({ ...formData, skills: skillsArray })
    }

    // Botões do ActionBar customizados (para usar handleCancelCustom)
    const actionBarButtons = useActionBarButtons({
        isEditing,
        selectedCount: selectedDemandsCount,
        hasChanges: hasChanges(),
        submitting,
        deleting,
        onCancel: handleCancelCustom,
        onDelete: handleDeleteSelected,
        onSave: handleSave,
    })

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Demanda" isEditing={isEditing}>
                <div className="space-y-4">
                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <FormField label="Hospital">
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
                                </FormField>
                                <FormField label="Procedimento" required>
                                    <input
                                        type="text"
                                        id="procedure"
                                        value={formData.procedure}
                                        onChange={(e) => setFormData({ ...formData, procedure: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        required
                                        disabled={submitting}
                                    />
                                </FormField>
                            </FormFieldGrid>

                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <TenantDateTimePicker
                                    id="start_time"
                                    label="Data/Hora Início"
                                    value={formData.start_time}
                                    onChange={(date) => setFormData({ ...formData, start_time: date })}
                                    disabled={submitting}
                                />
                                <TenantDateTimePicker
                                    id="end_time"
                                    label="Data/Hora Fim"
                                    value={formData.end_time}
                                    onChange={(date) => setFormData({ ...formData, end_time: date })}
                                    disabled={submitting}
                                />
                            </FormFieldGrid>

                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <FormField label="Sala/Quarto">
                                    <input
                                        type="text"
                                        id="room"
                                        value={formData.room}
                                        onChange={(e) => setFormData({ ...formData, room: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </FormField>
                                <FormField label="Prioridade">
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
                                </FormField>
                            </FormFieldGrid>

                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <FormField label="Tipo de Anestesia">
                                    <input
                                        type="text"
                                        id="anesthesia_type"
                                        value={formData.anesthesia_type}
                                        onChange={(e) => setFormData({ ...formData, anesthesia_type: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </FormField>
                                <FormField label="Complexidade">
                                    <input
                                        type="text"
                                        id="complexity"
                                        value={formData.complexity}
                                        onChange={(e) => setFormData({ ...formData, complexity: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                        disabled={submitting}
                                    />
                                </FormField>
                            </FormFieldGrid>

                            <FormField
                                label="Habilidades (separadas por vírgula)"
                                helperText="Ex: Obstétrica, Cardíaca"
                            >
                                <input
                                    type="text"
                                    id="skills"
                                    value={skillsInput}
                                    onChange={(e) => updateSkills(e.target.value)}
                                    placeholder="Ex: Obstétrica, Cardíaca"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    disabled={submitting}
                                />
                            </FormField>

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

                            <FormField label="Observações">
                                <textarea
                                    id="notes"
                                    value={formData.notes}
                                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    disabled={submitting}
                                />
                            </FormField>
                        </div>
            </EditForm>

            <CardPanel
                title="Demandas"
                description="Gerencie as demandas cirúrgicas"
                totalCount={filteredDemands.length}
                selectedCount={selectedDemands.size}
                loading={loading}
                loadingMessage="Carregando demandas..."
                emptyMessage="Nenhuma demanda cadastrada ainda."
                error={(() => {
                    // Mostra erro no CardPanel apenas se não houver botões de ação
                    const hasButtons = isEditing || selectedDemandsCount > 0
                    return hasButtons ? null : error
                })()}
                createCard={
                    <CreateCard
                        label="Criar nova demanda"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClickCustom}
                    />
                }
                filterContent={
                    !isEditing ? (
                        <FilterPanel>
                            <FormField label="Procedimento">
                                <input
                                    type="text"
                                    value={procedureFilter}
                                    onChange={(e) => setProcedureFilter(e.target.value)}
                                    placeholder="Filtrar por procedimento..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                />
                            </FormField>
                        </FilterPanel>
                    ) : undefined
                }
            >
                {filteredDemands.map((demand) => {
                    const isSelected = selectedDemands.has(demand.id)
                    const hospital = hospitals.find((h) => h.id === demand.hospital_id)
                    return (
                        <EntityCard
                            key={demand.id}
                            id={demand.id}
                            isSelected={isSelected}
                            footer={
                                <CardFooter
                                    isSelected={isSelected}
                                    date={demand.created_at || demand.start_time}
                                    settings={settings}
                                    onToggleSelection={(e) => {
                                        e.stopPropagation()
                                        toggleDemandSelection(demand.id)
                                    }}
                                    onEdit={() => handleEditClickCustom(demand)}
                                    disabled={deleting}
                                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                    editTitle="Editar demanda"
                                />
                            }
                        >
                            {/* Corpo - Procedimento principal (similar ao Tenant) */}
                            <div className="mb-3">
                                <div
                                    className="h-40 sm:h-48 rounded-lg flex items-center justify-center border border-blue-200"
                                    style={{
                                        backgroundColor: hospital?.color || '#f1f5f9',
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
                                                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                                                />
                                            </svg>
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                }`}
                                            title={demand.procedure}
                                        >
                                            {demand.procedure}
                                        </h3>
                                        {hospital && (
                                            <p className="text-xs text-gray-600 mt-1">{hospital.name}</p>
                                        )}
                                        <div className="mt-2 flex flex-wrap gap-1 justify-center px-2">
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
                                </div>
                            </div>

                            {/* Detalhes adicionais */}
                            <div className="mb-3 space-y-1 text-sm">
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
                            onFirst={paginationHandlers.onFirst}
                            onPrevious={paginationHandlers.onPrevious}
                            onNext={paginationHandlers.onNext}
                            onLast={paginationHandlers.onLast}
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
