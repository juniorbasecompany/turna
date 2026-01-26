'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterButtons, FilterOption } from '@/components/FilterButtons'
import { FilterPanel } from '@/components/FilterPanel'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { TenantDatePicker } from '@/components/TenantDatePicker'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { useEntityPage } from '@/hooks/useEntityPage'
import { formatDateTime, localDateToUtcEndExclusive, localDateToUtcStart } from '@/lib/tenantFormat'
import {
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    ScheduleVersionResponse,
} from '@/types/api'
import { useEffect, useMemo, useState } from 'react'

type ScheduleFormData = {
    name: string
    period_start_at: Date | null
    period_end_at: Date | null
    version_number: number
    status: string
}

export default function SchedulePage() {
    const { settings } = useTenantSettings()

    // Constantes para filtros
    const ALL_STATUS_FILTERS: string[] = ['DRAFT', 'PUBLISHED', 'ARCHIVED']

    // Estados auxiliares
    const [nameFilter, setNameFilter] = useState('')

    // Filtros usando hook reutilizável
    const statusFilters = useEntityFilters<string>({
        allFilters: ALL_STATUS_FILTERS,
        initialFilters: new Set(ALL_STATUS_FILTERS),
    })

    // Filtros de período usando TenantDatePicker (Date objects)
    const [periodStartDate, setPeriodStartDate] = useState<Date | null>(null)
    const [periodEndDate, setPeriodEndDate] = useState<Date | null>(null)
    const [createCardFlash, setCreateCardFlash] = useState(false)
    const [periodStartFlash, setPeriodStartFlash] = useState(false)
    const [periodEndFlash, setPeriodEndFlash] = useState(false)

    // Configuração inicial
    const initialFormData: ScheduleFormData = {
        name: '',
        period_start_at: null,
        period_end_at: null,
        version_number: 1,
        status: 'DRAFT',
    }

    // Mapeamentos
    const mapEntityToFormData = (schedule: ScheduleVersionResponse): ScheduleFormData => {
        return {
            name: schedule.name,
            period_start_at: schedule.period_start_at ? new Date(schedule.period_start_at) : null,
            period_end_at: schedule.period_end_at ? new Date(schedule.period_end_at) : null,
            version_number: schedule.version_number,
            status: schedule.status,
        }
    }

    const mapFormDataToCreateRequest = (formData: ScheduleFormData): ScheduleCreateRequest => {
        const startIso = formData.period_start_at?.toISOString()
        const endIso = formData.period_end_at?.toISOString()

        return {
            name: formData.name.trim(),
            period_start_at: startIso!,
            period_end_at: endIso!,
            version_number: formData.version_number,
        }
    }

    const mapFormDataToUpdateRequest = (formData: ScheduleFormData): ScheduleUpdateRequest => {
        const startIso = formData.period_start_at?.toISOString()
        const endIso = formData.period_end_at?.toISOString()

        return {
            name: formData.name.trim(),
            period_start_at: startIso,
            period_end_at: endIso,
            version_number: formData.version_number,
            status: formData.status,
        }
    }

    // Validação
    const validateFormData = (formData: ScheduleFormData): string | null => {
        if (!formData.name.trim()) {
            return 'Nome é obrigatório'
        }

        if (!formData.period_start_at || !formData.period_end_at) {
            return 'Data/hora de início e fim são obrigatórias'
        }

        if (formData.period_end_at <= formData.period_start_at) {
            return 'Data/hora de fim deve ser maior que a de início'
        }

        if (formData.version_number < 1) {
            return 'Número da versão deve ser maior ou igual a 1'
        }

        return null
    }

    // isEmptyCheck
    const isEmptyCheck = (formData: ScheduleFormData): boolean => {
        return (
            formData.name.trim() === '' &&
            formData.period_start_at === null &&
            formData.period_end_at === null
        )
    }

    // Calcular additionalListParams reativo (apenas filtros suportados pela API)
    const additionalListParams = useMemo(() => {
        if (!settings) return undefined
        const params: Record<string, string | number | boolean | null> = {
            period_start_at: periodStartDate ? localDateToUtcStart(periodStartDate, settings) : null,
            period_end_at: periodEndDate ? localDateToUtcEndExclusive(periodEndDate, settings) : null,
        }

        // Status: passar apenas se exatamente 1 estiver selecionado
        if (statusFilters.selectedFilters.size === 1) {
            const status = Array.from(statusFilters.selectedFilters)[0]
            params.status = status
        }

        return params
    }, [periodStartDate, periodEndDate, statusFilters.selectedFilters, settings])

    // Verificar se precisa filtrar no frontend (quando múltiplos valores estão selecionados)
    const needsFrontendFilter = useMemo(() => {
        const allStatusSelected = statusFilters.selectedFilters.size === ALL_STATUS_FILTERS.length

        // Se todos estão selecionados, não precisa filtrar
        if (allStatusSelected) {
            return false
        }

        // Se apenas 1 está selecionado, backend filtra (não precisa filtrar no frontend)
        const singleStatusSelected = statusFilters.selectedFilters.size === 1

        if (singleStatusSelected) {
            return false
        }

        // Se múltiplos estão selecionados, precisa filtrar no frontend
        return true
    }, [statusFilters.selectedFilters])

    // useEntityPage
    const {
        items: schedules,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingSchedule,
        isEditing,
        hasChanges,
        handleCreateClick,
        handleEditClick,
        handleCancel,
        selectedItems: selectedSchedules,
        toggleSelection: toggleScheduleSelection,
        selectedCount: selectedSchedulesCount,
        pagination,
        total,
        paginationHandlers,
        handleSave,
        handleDeleteSelected,
        actionBarErrorProps,
    } = useEntityPage<ScheduleFormData, ScheduleVersionResponse, ScheduleCreateRequest, ScheduleUpdateRequest>({
        endpoint: '/api/schedule',
        entityName: 'escala',
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
        additionalListParams,
        listEnabled: !!settings,
    })

    const triggerPeriodFlash = (isStartMissing: boolean, isEndMissing: boolean) => {
        setCreateCardFlash(true)
        setPeriodStartFlash(isStartMissing)
        setPeriodEndFlash(isEndMissing)
        // Remover o flash após 1 segundo
        setTimeout(() => {
            setCreateCardFlash(false)
            setPeriodStartFlash(false)
            setPeriodEndFlash(false)
        }, 1000)
    }

    const handleCreateCardClick = () => {
        const isStartMissing = isEditing ? !formData.period_start_at : !periodStartDate
        const isEndMissing = isEditing ? !formData.period_end_at : !periodEndDate

        if (isStartMissing || isEndMissing) {
            triggerPeriodFlash(isStartMissing, isEndMissing)
            return
        }

        handleCreateClick()
    }

    // Validar intervalo de datas
    useEffect(() => {
        if (periodStartDate && periodEndDate && periodStartDate > periodEndDate) {
            setError('Data inicial deve ser menor ou igual à data final')
        } else {
            // Limpar erro de validação de datas quando as datas forem válidas
            if (error === 'Data inicial deve ser menor ou igual à data final') {
                setError(null)
            }
        }
    }, [periodStartDate, periodEndDate, setError, error])

    // Handlers para mudança de data no TenantDatePicker
    const handlePeriodStartDateChange = (date: Date | null) => {
        setPeriodStartDate(date)
        paginationHandlers.onFirst() // Resetar paginação ao mudar filtro
    }

    const handlePeriodEndDateChange = (date: Date | null) => {
        setPeriodEndDate(date)
        paginationHandlers.onFirst() // Resetar paginação ao mudar filtro
    }

    // Filtrar schedules por nome e status (filtro no frontend quando necessário)
    const filteredSchedules = useMemo(() => {
        let filtered = schedules

        // Filtro por nome (sempre no frontend, pois não é suportado pela API)
        if (nameFilter.trim()) {
            const filterLower = nameFilter.toLowerCase().trim()
            filtered = filtered.filter((schedule) => schedule.name.toLowerCase().includes(filterLower))
        }

        // Filtro por status (no frontend apenas quando múltiplos estão selecionados)
        if (needsFrontendFilter) {
            filtered = filtered.filter((schedule) => statusFilters.selectedFilters.has(schedule.status))
        }

        return filtered
    }, [schedules, nameFilter, statusFilters.selectedFilters, needsFrontendFilter])

    // Aplicar paginação no frontend quando há filtro no frontend
    const paginatedSchedules = useMemo(() => {
        if (!needsFrontendFilter) {
            return filteredSchedules  // Backend já paginou
        }
        // Paginar no frontend
        const start = pagination.offset
        const end = start + pagination.limit
        return filteredSchedules.slice(start, end)
    }, [filteredSchedules, needsFrontendFilter, pagination.offset, pagination.limit])

    // Ajustar total para refletir filtro de status
    const displayTotal = useMemo(() => {
        if (!needsFrontendFilter) {
            return total  // Usar total do backend
        }
        return filteredSchedules.length  // Total após filtro no frontend
    }, [filteredSchedules, needsFrontendFilter, total])

    // Resetar offset quando filtros mudarem
    useEffect(() => {
        paginationHandlers.onFirst()
    }, [statusFilters.selectedFilters])

    // Botões do ActionBar
    const actionBarButtons = useActionBarButtons({
        isEditing,
        selectedCount: selectedSchedulesCount,
        hasChanges: hasChanges(),
        submitting,
        deleting,
        onCancel: handleCancel,
        onDelete: handleDeleteSelected,
        onSave: handleSave,
    })

    // Função auxiliar para obter cor do status
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'DRAFT':
                return 'bg-gray-100 text-gray-800'
            case 'PUBLISHED':
                return 'bg-green-100 text-green-800'
            case 'ARCHIVED':
                return 'bg-yellow-100 text-yellow-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    // Função auxiliar para obter label do status
    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'DRAFT':
                return 'Rascunho'
            case 'PUBLISHED':
                return 'Publicada'
            case 'ARCHIVED':
                return 'Arquivada'
            default:
                return status
        }
    }

    // Opções para o filtro de status
    const statusOptions: FilterOption<string>[] = [
        { value: 'DRAFT', label: 'Rascunho', color: 'text-gray-600' },
        { value: 'PUBLISHED', label: 'Publicada', color: 'text-green-600' },
        { value: 'ARCHIVED', label: 'Arquivada', color: 'text-yellow-600' },
    ]

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Escala" isEditing={isEditing}>
                <div className="space-y-4">
                    <FormField label="Nome" required>
                        <input
                            type="text"
                            id="name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            required
                            disabled={submitting}
                        />
                    </FormField>

                    <FormFieldGrid cols={1} smCols={2} gap={4}>
                        <TenantDateTimePicker
                            id="period_start_at"
                            label="Data/Hora Início"
                            value={formData.period_start_at}
                            onChange={(date) => setFormData({ ...formData, period_start_at: date })}
                            disabled={submitting}
                            showFlash={periodStartFlash}
                        />
                        <TenantDateTimePicker
                            id="period_end_at"
                            label="Data/Hora Fim"
                            value={formData.period_end_at}
                            onChange={(date) => setFormData({ ...formData, period_end_at: date })}
                            disabled={submitting}
                            showFlash={periodEndFlash}
                        />
                    </FormFieldGrid>

                    <FormFieldGrid cols={1} smCols={2} gap={4}>
                        <FormField label="Versão">
                            <input
                                type="number"
                                id="version_number"
                                value={formData.version_number}
                                onChange={(e) =>
                                    setFormData({
                                        ...formData,
                                        version_number: parseInt(e.target.value) || 1,
                                    })
                                }
                                min="1"
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            />
                        </FormField>
                        <FormField label="Status">
                            <select
                                id="status"
                                value={formData.status}
                                onChange={(e) =>
                                    setFormData({
                                        ...formData,
                                        status: e.target.value,
                                    })
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            >
                                <option value="DRAFT">Rascunho</option>
                                <option value="PUBLISHED">Publicada</option>
                                <option value="ARCHIVED">Arquivada</option>
                            </select>
                        </FormField>
                    </FormFieldGrid>
                </div>
            </EditForm>

            <CardPanel
                title="Escalas"
                description="Gerencie as escalas cirúrgicas"
                totalCount={filteredSchedules.length}
                selectedCount={selectedSchedules.size}
                loading={loading}
                loadingMessage="Carregando escalas..."
                emptyMessage="Nenhuma escala cadastrada ainda."
                error={(() => {
                    // Mostra erro no CardPanel apenas se não houver botões de ação
                    const hasButtons = isEditing || selectedSchedulesCount > 0
                    return hasButtons ? null : error
                })()}
                createCard={
                    <>
                        <CreateCard
                            label="Criar uma escala"
                            subtitle="Clique para adicionar uma nova escala"
                            onClick={handleCreateClick}
                        />
                        <CreateCard
                            label="Calcular a escala"
                            subtitle="Clique para calcular a escala do período"
                            onClick={handleCreateCardClick}
                            showFlash={createCardFlash}
                            flashMessage="Informe o período inicial e final"
                            disabled={isEditing}
                            customIcon={
                                <svg
                                    className="w-full h-full"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    {/* Corpo do Calendário */}
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M16 20H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v9"
                                    />
                                    {/* Argolas do topo */}
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M16 2v4"
                                    />
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M8 2v4"
                                    />
                                    {/* Linha horizontal do cabeçalho */}
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M3 10h18"
                                    />
                                    {/* Linhas de conteúdo interno */}
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M6 13h6 M15 13h3 M7 16h3 M12 16h3"
                                    />
                                    {/* Sinal de mais (+) no canto inferior direito */}
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M21 18v4"
                                    />
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M19 20h4"
                                    />
                                </svg>
                            }
                        />
                    </>
                }
                filterContent={
                    !isEditing ? (
                        <FilterPanel>
                            <FormFieldGrid cols={1} smCols={3} gap={4}>
                                <FormField label="Nome">
                                    <input
                                        type="text"
                                        value={nameFilter}
                                        onChange={(e) => setNameFilter(e.target.value)}
                                        placeholder="Filtrar por nome..."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </FormField>
                                <TenantDatePicker
                                    label="Período início"
                                    value={periodStartDate}
                                    onChange={handlePeriodStartDateChange}
                                    id="period_start_at_filter"
                                    name="period_start_at_filter"
                                    showFlash={periodStartFlash}
                                />
                                <TenantDatePicker
                                    label="Período fim"
                                    value={periodEndDate}
                                    onChange={handlePeriodEndDateChange}
                                    id="period_end_at_filter"
                                    name="period_end_at_filter"
                                    showFlash={periodEndFlash}
                                />
                            </FormFieldGrid>
                            <FilterButtons
                                title="Situação"
                                options={statusOptions}
                                selectedValues={statusFilters.selectedFilters}
                                onToggle={statusFilters.toggleFilter}
                                onToggleAll={statusFilters.toggleAll}
                            />
                        </FilterPanel>
                    ) : undefined
                }
            >
                {(needsFrontendFilter ? paginatedSchedules : filteredSchedules).map((schedule) => {
                    const isSelected = selectedSchedules.has(schedule.id)
                    return (
                        <EntityCard
                            key={schedule.id}
                            id={schedule.id}
                            isSelected={isSelected}
                            footer={
                                <CardFooter
                                    isSelected={isSelected}
                                    date={schedule.created_at || schedule.period_start_at}
                                    settings={settings}
                                    onToggleSelection={(e) => {
                                        e.stopPropagation()
                                        toggleScheduleSelection(schedule.id)
                                    }}
                                    onEdit={() => handleEditClick(schedule)}
                                    disabled={deleting}
                                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                    editTitle="Editar escala"
                                />
                            }
                        >
                            {/* Corpo - Nome principal */}
                            <div className="mb-3">
                                <div
                                    className="h-40 sm:h-48 rounded-lg flex items-center justify-center border border-blue-200 bg-blue-50"
                                >
                                    <div className="flex flex-col items-center justify-center text-blue-500">
                                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                                            <svg
                                                className="w-full h-full"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                {/* Corpo do Calendário */}
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"
                                                />
                                                {/* Argolas do topo */}
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M16 2v4"
                                                />
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M8 2v4"
                                                />
                                                {/* Linha horizontal do cabeçalho */}
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M3 10h18"
                                                />
                                                {/* Linhas de conteúdo interno */}
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M6 13h6 M15 13h3 M7 16h3 M12 16h3"
                                                />
                                            </svg>
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                }`}
                                            title={schedule.name}
                                        >
                                            {schedule.name}
                                        </h3>
                                        <div className="mt-2 flex flex-wrap gap-1 justify-center px-2">
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${getStatusColor(schedule.status)}`}>
                                                {getStatusLabel(schedule.status)}
                                            </span>
                                            {schedule.version_number > 1 && (
                                                <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                                                    v{schedule.version_number}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Detalhes adicionais */}
                            <div className="mb-3 space-y-1 text-sm">
                                <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                    <span className="font-medium">Início:</span>{' '}
                                    {settings
                                        ? formatDateTime(schedule.period_start_at, settings)
                                        : new Date(schedule.period_start_at).toLocaleString('pt-BR', {
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
                                        ? formatDateTime(schedule.period_end_at, settings)
                                        : new Date(schedule.period_end_at).toLocaleString('pt-BR', {
                                            day: '2-digit',
                                            month: '2-digit',
                                            year: 'numeric',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        })}
                                </p>
                                {schedule.generated_at && (
                                    <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                        <span className="font-medium">Gerada em:</span>{' '}
                                        {settings
                                            ? formatDateTime(schedule.generated_at, settings)
                                            : new Date(schedule.generated_at).toLocaleString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                    </p>
                                )}
                                {schedule.published_at && (
                                    <p className={`${isSelected ? 'text-red-800' : 'text-gray-600'}`}>
                                        <span className="font-medium">Publicada em:</span>{' '}
                                        {settings
                                            ? formatDateTime(schedule.published_at, settings)
                                            : new Date(schedule.published_at).toLocaleString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
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
                    displayTotal > 0 ? (
                        <Pagination
                            offset={pagination.offset}
                            limit={pagination.limit}
                            total={displayTotal}
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
