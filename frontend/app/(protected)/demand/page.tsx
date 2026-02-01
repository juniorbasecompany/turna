'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterDateRange, FilterInput, FilterPanel, FilterSelect } from '@/components/filter'
import { FormInput, FormSelect, FormTextarea } from '@/components/form'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarRightButtons } from '@/hooks/useActionBarRightButtons'
import { useEntityPage } from '@/hooks/useEntityPage'
import { useReportButton } from '@/hooks/useReportButton'
import { protectedFetch } from '@/lib/api'
import { getCardInfoTextClasses, getCardTertiaryTextClasses, getCardTextClasses } from '@/lib/cardStyles'
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
}

export default function DemandPage() {
    const { settings } = useTenantSettings()

    // Estados auxiliares (não gerenciados por useEntityPage)
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [filterHospitalId, setFilterHospitalId] = useState<number | null>(null)
    const [filterProcedure, setFilterProcedure] = useState('')
    const [skillsInput, setSkillsInput] = useState('')

    const [filterStartDate, setFilterStartDate] = useState<Date | null>(() => new Date())
    const [filterEndDate, setFilterEndDate] = useState<Date | null>(null)

    const FILTER_HOSPITAL_LABEL = 'Hospital'
    const FILTER_PROCEDURE_LABEL = 'Procedimento'
    const FILTER_START_LABEL = 'Desde'
    const FILTER_END_LABEL = 'Até'

    const additionalListParams = useMemo(() => {
        const params: Record<string, string | number | null> = {}
        if (filterStartDate) params.start_at = filterStartDate.toISOString()
        if (filterEndDate) params.end_at = filterEndDate.toISOString()
        if (filterHospitalId !== null) params.hospital_id = filterHospitalId
        if (filterProcedure.trim()) params.procedure = filterProcedure.trim()
        return Object.keys(params).length ? params : undefined
    }, [filterStartDate, filterEndDate, filterHospitalId, filterProcedure])

    const reportFilters = useMemo((): { label: string; value: string }[] => {
        const list: { label: string; value: string }[] = []
        if (filterHospitalId != null) {
            const hospital = hospitals.find((h) => h.id === filterHospitalId)
            list.push({
                label: FILTER_HOSPITAL_LABEL,
                value: hospital?.name ?? String(filterHospitalId),
            })
        }
        if (filterProcedure.trim()) {
            list.push({ label: FILTER_PROCEDURE_LABEL, value: filterProcedure.trim() })
        }
        if (filterStartDate) {
            list.push({
                label: FILTER_START_LABEL,
                value: filterStartDate.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }),
            })
        }
        if (filterEndDate) {
            list.push({
                label: FILTER_END_LABEL,
                value: filterEndDate.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }),
            })
        }
        return list
    }, [filterHospitalId, filterProcedure, filterStartDate, filterEndDate, hospitals])

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
        }
    }

    const mapFormDataToCreateRequest = (formData: DemandFormData): DemandCreateRequest => {
        const startIso = formData.start_time?.toISOString()
        const endIso = formData.end_time?.toISOString()

        return {
            hospital_id: formData.hospital_id!,
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
        }
    }

    // Validação
    const validateFormData = (formData: DemandFormData): string | null => {
        if (formData.hospital_id === null) {
            return 'Hospital é obrigatório'
        }

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
        items: demandList,
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
        toggleAll: toggleAllDemands,
        selectedCount: selectedDemandsCount,
        selectAllMode: selectAllDemandsMode,
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
        additionalListParams,
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

    useEffect(() => {
        paginationHandlers.onFirst()
        // eslint-disable-next-line react-hooks/exhaustive-deps -- resetar página ao mudar filtros
    }, [additionalListParams])

    // Validar intervalo de datas
    useEffect(() => {
        if (filterStartDate && filterEndDate && filterStartDate > filterEndDate) {
            setError('Data inicial deve ser menor ou igual à data final')
        } else {
            // Limpar erro de validação de datas quando as datas forem válidas
            if (error === 'Data inicial deve ser menor ou igual à data final') {
                setError(null)
            }
        }
    }, [filterStartDate, filterEndDate, setError, error])

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

    // Listagem já filtrada pelo backend via additionalListParams
    const filteredDemands = demandList

    // Atualizar skills a partir do input
    const updateSkills = (input: string) => {
        setSkillsInput(input)
        const skillsArray = input
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        setFormData({ ...formData, skills: skillsArray })
    }

    const { leftButtons: reportLeftButtons, reportError } = useReportButton({
        apiPath: '/api/demand/report',
        params: additionalListParams ?? undefined,
        reportFilters,
    })

    // Botões do ActionBar customizados (para usar handleCancelCustom)
    const actionBarButtons = useActionBarRightButtons({
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
                        <FormSelect
                            label="Hospital"
                            value={formData.hospital_id}
                            onChange={(value) => setFormData({ ...formData, hospital_id: value })}
                            options={hospitals.map((h) => ({ value: h.id, label: h.name }))}
                            id="hospital_id"
                            required
                            disabled={submitting}
                            loading={loadingHospitals}
                        />
                        <FormInput
                            label="Procedimento"
                            value={formData.procedure}
                            onChange={(value) => setFormData({ ...formData, procedure: value })}
                            id="procedure"
                            required
                            disabled={submitting}
                        />
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
                        <FormInput
                            label="Sala/Quarto"
                            value={formData.room}
                            onChange={(value) => setFormData({ ...formData, room: value })}
                            id="room"
                            disabled={submitting}
                        />
                        <FormSelect
                            label="Prioridade"
                            value={formData.priority}
                            onChange={(value) => setFormData({ ...formData, priority: value })}
                            options={[
                                { value: 'Urgente', label: 'Urgente' },
                                { value: 'Emergência', label: 'Emergência' },
                            ]}
                            emptyLabel="Nenhuma"
                            id="priority"
                            disabled={submitting}
                        />
                    </FormFieldGrid>

                    <FormFieldGrid cols={1} smCols={2} gap={4}>
                        <FormInput
                            label="Tipo de Anestesia"
                            value={formData.anesthesia_type}
                            onChange={(value) => setFormData({ ...formData, anesthesia_type: value })}
                            id="anesthesia_type"
                            disabled={submitting}
                        />
                        <FormInput
                            label="Complexidade"
                            value={formData.complexity}
                            onChange={(value) => setFormData({ ...formData, complexity: value })}
                            id="complexity"
                            disabled={submitting}
                        />
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

                    <FormTextarea
                        label="Observações"
                        value={formData.notes}
                        onChange={(value) => setFormData({ ...formData, notes: value })}
                        id="notes"
                        rows={3}
                        disabled={submitting}
                    />
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
                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <FilterSelect
                                    label="Hospital"
                                    value={filterHospitalId}
                                    onChange={setFilterHospitalId}
                                    options={hospitals.map((h) => ({ value: h.id, label: h.name }))}
                                    disabled={loadingHospitals}
                                />
                                <FilterInput
                                    label={FILTER_PROCEDURE_LABEL}
                                    value={filterProcedure}
                                    onChange={setFilterProcedure}
                                />
                            </FormFieldGrid>
                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <FilterDateRange
                                    startValue={filterStartDate}
                                    endValue={filterEndDate}
                                    onStartChange={setFilterStartDate}
                                    onEndChange={setFilterEndDate}
                                    startId="filter_start_date"
                                    endId="filter_end_date"
                                />
                            </FormFieldGrid>
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
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
                                                <rect x="4" y="4" width="16" height="3" fill="currentColor" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 3v18M12 4v16" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 11h16M4 16h16M4" />
                                            </svg>
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${getCardTextClasses(isSelected)}`}
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
                                    <p className={`${getCardInfoTextClasses(isSelected)}`}>
                                        <span className="font-medium">Sala:</span> {demand.room}
                                    </p>
                                )}
                                <p className={`${getCardInfoTextClasses(isSelected)}`}>
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
                                <p className={`${getCardInfoTextClasses(isSelected)}`}>
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
                                    <p className={`${getCardInfoTextClasses(isSelected)}`}>
                                        <span className="font-medium">Anestesia:</span> {demand.anesthesia_type}
                                    </p>
                                )}
                                {demand.complexity && (
                                    <p className={`${getCardInfoTextClasses(isSelected)}`}>
                                        <span className="font-medium">Complexidade:</span> {demand.complexity}
                                    </p>
                                )}
                                {demand.skills && demand.skills.length > 0 && (
                                    <p className={`${getCardInfoTextClasses(isSelected)}`}>
                                        <span className="font-medium">Habilidades:</span> {demand.skills.join(', ')}
                                    </p>
                                )}
                                {demand.notes && (
                                    <p className={`text-xs ${getCardTertiaryTextClasses(isSelected)} line-clamp-2`}>
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
                selection={{
                    selectedCount: selectedDemandsCount,
                    totalCount: filteredDemands.length,
                    grandTotal: total,
                    selectAllMode: selectAllDemandsMode,
                    onToggleAll: () => toggleAllDemands(filteredDemands.map((d) => d.id)),
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
                buttons={actionBarButtons}
            />
        </>
    )
}
