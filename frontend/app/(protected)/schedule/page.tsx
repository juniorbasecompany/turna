'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterButtons, FilterDateRange, FilterInput, FilterPanel, FilterSelect } from '@/components/filter'
import type { FilterOption } from '@/components/filter'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { useEntityPage } from '@/hooks/useEntityPage'
import { protectedFetch } from '@/lib/api'
import { getCardInfoTextClasses, getCardTextClasses } from '@/lib/cardStyles'
import { formatDateTime, localDateToUtcEndExclusive, localDateToUtcStart } from '@/lib/tenantFormat'
import {
    HospitalListResponse,
    HospitalResponse,
    ScheduleCreateRequest,
    ScheduleGenerateFromDemandsRequest,
    ScheduleGenerateFromDemandsResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
} from '@/types/api'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type ScheduleFormData = {
    hospital_id: number | null
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

    // Estados auxiliares - Hospitais
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [filterHospitalId, setFilterHospitalId] = useState<number | null>(null)

    // Estados auxiliares
    const [filterName, setFilterName] = useState('')
    const [generating, setGenerating] = useState(false)
    const [filterStartFlash, setFilterStartFlash] = useState(false)
    const [filterEndFlash, setFilterEndFlash] = useState(false)

    // Ref para AbortController do SSE (permite cancelar ao sair da página)
    const sseAbortControllerRef = useRef<AbortController | null>(null)

    // Filtros usando hook reutilizável
    const statusFilters = useEntityFilters<string>({
        allFilters: ALL_STATUS_FILTERS,
        initialFilters: new Set(ALL_STATUS_FILTERS),
    })

    // Filtros de período usando TenantDateTimePicker (Date objects com hora)
    // "Desde" inicia com a data/hora atual, "Até" inicia vazio
    const [filterStartDate, setFilterStartDate] = useState<Date | null>(() => new Date())
    const [filterEndDate, setFilterEndDate] = useState<Date | null>(null)

    // Configuração inicial
    const initialFormData: ScheduleFormData = {
        hospital_id: null,
        name: '',
        period_start_at: null,
        period_end_at: null,
        version_number: 1,
        status: 'DRAFT',
    }

    // Mapeamentos
    const mapEntityToFormData = (schedule: ScheduleResponse): ScheduleFormData => {
        return {
            hospital_id: schedule.hospital_id,
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
            hospital_id: formData.hospital_id!,
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
        if (!formData.hospital_id) {
            return 'Hospital é obrigatório'
        }

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
            formData.hospital_id === null &&
            formData.name.trim() === '' &&
            formData.period_start_at === null &&
            formData.period_end_at === null
        )
    }

    // Calcular additionalListParams reativo (apenas filtros suportados pela API)
    const additionalListParams = useMemo(() => {
        if (!settings) return undefined
        const params: Record<string, string | number | boolean | null> = {
            // Usar data/hora diretamente (ISO string) para filtro de período
            period_start_at: filterStartDate ? filterStartDate.toISOString() : null,
            period_end_at: filterEndDate ? filterEndDate.toISOString() : null,
        }

        // Status: passar apenas se exatamente 1 estiver selecionado
        if (statusFilters.selectedFilters.size === 1) {
            const status = Array.from(statusFilters.selectedFilters)[0]
            params.status = status
        }

        return params
    }, [filterStartDate, filterEndDate, statusFilters.selectedFilters, settings])

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
        toggleAll: toggleAllSchedules,
        selectedCount: selectedSchedulesCount,
        selectAllMode: selectAllSchedulesMode,
        pagination,
        total,
        paginationHandlers,
        handleSave,
        handleDeleteSelected,
        loadItems,
        actionBarErrorProps,
    } = useEntityPage<ScheduleFormData, ScheduleResponse, ScheduleCreateRequest, ScheduleUpdateRequest>({
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

    // Carregar hospitais para o seletor
    useEffect(() => {
        const loadHospitals = async () => {
            try {
                const response = await protectedFetch<HospitalListResponse>('/api/hospital?limit=100')
                setHospitals(response.items || [])
                // Se houver apenas um hospital, selecioná-lo automaticamente
                if (response.items?.length === 1) {
                    setFilterHospitalId(response.items[0].id)
                }
            } catch (err) {
                console.error('Erro ao carregar hospitais:', err)
            } finally {
                setLoadingHospitals(false)
            }
        }
        loadHospitals()
    }, [])

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

    // Handlers para mudança de data no filtro (com reset de paginação)
    const handleFilterStartDateChange = (date: Date | null) => {
        setFilterStartDate(date)
        paginationHandlers.onFirst()
    }

    const handleFilterEndDateChange = (date: Date | null) => {
        setFilterEndDate(date)
        paginationHandlers.onFirst()
    }

    // Cleanup: cancelar SSE ao desmontar componente
    useEffect(() => {
        return () => {
            if (sseAbortControllerRef.current) {
                sseAbortControllerRef.current.abort()
                sseAbortControllerRef.current = null
            }
        }
    }, [])

    // Função para disparar flash nos campos de período
    const triggerPeriodFlash = (isStartMissing: boolean, isEndMissing: boolean) => {
        setFilterStartFlash(isStartMissing)
        setFilterEndFlash(isEndMissing)
        // Remover o flash após 1 segundo
        setTimeout(() => {
            setFilterStartFlash(false)
            setFilterEndFlash(false)
        }, 1000)
    }

    // Função para aguardar conclusão do job via SSE
    const waitForJobCompletion = useCallback(async (jobId: number): Promise<void> => {
        // Cancelar SSE anterior se existir
        if (sseAbortControllerRef.current) {
            sseAbortControllerRef.current.abort()
        }

        // Criar novo AbortController
        const abortController = new AbortController()
        sseAbortControllerRef.current = abortController

        return new Promise((resolve, reject) => {
            // Usar fetch com streaming para receber SSE (suporta cookies)
            fetch(`/api/job/${jobId}/stream`, {
                credentials: 'include',
                signal: abortController.signal,
            })
                .then(async (response) => {
                    if (!response.ok) {
                        throw new Error(`Erro ao conectar com SSE: ${response.status}`)
                    }

                    const reader = response.body?.getReader()
                    if (!reader) {
                        throw new Error('Stream não disponível')
                    }

                    const decoder = new TextDecoder()
                    let buffer = ''

                    try {
                        while (true) {
                            const { done, value } = await reader.read()
                            if (done) break

                            buffer += decoder.decode(value, { stream: true })

                            // Parser SSE robusto: eventos são separados por \n\n
                            // Procurar por eventos completos no buffer
                            let eventEnd: number
                            while ((eventEnd = buffer.indexOf('\n\n')) !== -1) {
                                const eventBlock = buffer.slice(0, eventEnd)
                                buffer = buffer.slice(eventEnd + 2)

                                // Processar linhas do evento
                                let eventType = 'message'
                                let eventData = ''

                                for (const line of eventBlock.split('\n')) {
                                    if (line.startsWith('event: ')) {
                                        eventType = line.slice(7).trim()
                                    } else if (line.startsWith('data: ')) {
                                        eventData = line.slice(6)
                                    }
                                }

                                // Processar evento baseado no tipo
                                if (eventType === 'error' || eventType === 'timeout') {
                                    reject(new Error('Erro ou timeout aguardando job'))
                                    return
                                }

                                if (eventType === 'status' && eventData) {
                                    try {
                                        const data = JSON.parse(eventData)
                                        if (data.status === 'COMPLETED') {
                                            resolve()
                                            return
                                        }
                                        if (data.status === 'FAILED') {
                                            reject(new Error(data.result_data?.error || 'Job falhou'))
                                            return
                                        }
                                    } catch {
                                        // Ignorar dados que não são JSON válido
                                    }
                                }
                            }
                        }
                    } finally {
                        // Sempre liberar o reader
                        reader.releaseLock()
                    }
                })
                .catch((err) => {
                    // Ignorar erro de abort (usuário saiu da página)
                    if (err.name === 'AbortError') {
                        return
                    }
                    reject(err)
                })
        })
    }, [])

    // Handler para gerar escala (mesma ação do painel de demandas)
    const handleGenerateSchedule = async () => {
        // Hospital é obrigatório
        if (!filterHospitalId) {
            setError('Selecione um hospital')
            return
        }

        // Apenas período inicial é obrigatório
        if (!filterStartDate) {
            triggerPeriodFlash(true, false)
            setError('Informe o período inicial')
            return
        }

        if (!settings) {
            setError('Configurações não carregadas')
            return
        }

        // Validar que data final é maior que inicial (se informada)
        if (filterEndDate && filterStartDate > filterEndDate) {
            setError('Data final deve ser maior que a data inicial')
            return
        }

        try {
            setGenerating(true)
            setError(null)

            // Converter datas para UTC usando timezone do tenant
            const periodStartAt = localDateToUtcStart(filterStartDate, settings)
            // Se período final não informado, usar data muito futura (10 anos)
            const effectiveEndDate = filterEndDate || new Date(filterStartDate.getTime() + 10 * 365 * 24 * 60 * 60 * 1000)
            const periodEndAt = localDateToUtcEndExclusive(effectiveEndDate, settings)

            // Criar nome padrão baseado no período
            const selectedHospital = hospitals.find(h => h.id === filterHospitalId)
            const hospitalName = selectedHospital?.name || 'Hospital'
            const name = filterEndDate
                ? `${hospitalName} - ${filterStartDate.toLocaleDateString('pt-BR')} a ${filterEndDate.toLocaleDateString('pt-BR')}`
                : `${hospitalName} - a partir de ${filterStartDate.toLocaleDateString('pt-BR')}`

            const request: ScheduleGenerateFromDemandsRequest = {
                hospital_id: filterHospitalId,
                name,
                period_start_at: periodStartAt,
                period_end_at: periodEndAt,
                allocation_mode: 'greedy',
                version_number: 1,
            }

            // Envia requisição para criar o job
            const response = await protectedFetch<ScheduleGenerateFromDemandsResponse>(
                '/api/schedule/generate-from-demands',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(request),
                }
            )

            // Aguarda conclusão do job via SSE
            if (response.job_id) {
                await waitForJobCompletion(response.job_id)
            }

            // Recarregar a lista de escalas após job terminar
            loadItems()
        } catch (err) {
            let message = 'Erro ao gerar escala'
            if (err instanceof Error) {
                message = err.message
                // Melhorar mensagem para erro 405
                if (message.includes('405') || message.includes('Method Not Allowed')) {
                    message = 'Erro 405: Método HTTP não permitido. Verifique se o endpoint está configurado corretamente no backend.'
                }
                // Melhorar mensagem para erro 404
                if (message.includes('404') || message.includes('Not Found')) {
                    message = 'Erro 404: Endpoint não encontrado. Verifique se o backend está rodando e se a rota está correta.'
                }
            }
            setError(message)
            console.error('Erro ao gerar escala:', err)
        } finally {
            setGenerating(false)
        }
    }

    // Filtrar schedules por nome e status (filtro no frontend quando necessário)
    const filteredSchedules = useMemo(() => {
        let filtered = schedules

        // Filtro por nome (sempre no frontend, pois não é suportado pela API)
        if (filterName.trim()) {
            const filterLower = filterName.toLowerCase().trim()
            filtered = filtered.filter((schedule) => schedule.name.toLowerCase().includes(filterLower))
        }

        // Filtro por status (no frontend apenas quando múltiplos estão selecionados)
        if (needsFrontendFilter) {
            filtered = filtered.filter((schedule) => statusFilters.selectedFilters.has(schedule.status))
        }

        return filtered
    }, [schedules, filterName, statusFilters.selectedFilters, needsFrontendFilter])

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

    // Botões do ActionBar (com botão fixo "Calcular escala")
    const baseActionBarButtons = useActionBarButtons({
        isEditing,
        selectedCount: selectedSchedulesCount,
        hasChanges: hasChanges(),
        submitting,
        deleting,
        onCancel: handleCancel,
        onDelete: handleDeleteSelected,
        onSave: handleSave,
    })

    // Botão "Calcular" (oculto no modo edição) + botões do hook
    const actionBarButtons = useMemo(() => {
        // Ocultar botão no modo edição
        if (isEditing) {
            return baseActionBarButtons
        }
        const generateButton = {
            label: generating ? 'Calculando...' : 'Calcular',
            onClick: handleGenerateSchedule,
            variant: 'primary' as const,
            disabled: generating,
            loading: generating,
        }
        return [...baseActionBarButtons, generateButton]
    }, [baseActionBarButtons, generating, isEditing, handleGenerateSchedule])

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
                    <FormField label="Hospital" required>
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
                            <option value=""></option>
                            {hospitals.map((hospital) => (
                                <option key={hospital.id} value={hospital.id}>
                                    {hospital.name}
                                </option>
                            ))}
                        </select>
                    </FormField>

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
                        />
                        <TenantDateTimePicker
                            id="period_end_at"
                            label="Data/Hora Fim"
                            value={formData.period_end_at}
                            onChange={(date) => setFormData({ ...formData, period_end_at: date })}
                            disabled={submitting}
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
                    <CreateCard
                        label="Criar uma escala"
                        subtitle="Clique para adicionar uma nova escala"
                        onClick={handleCreateClick}
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
                                    label="Nome"
                                    value={filterName}
                                    onChange={setFilterName}
                                />
                            </FormFieldGrid>
                            <FormFieldGrid cols={1} smCols={2} gap={4}>
                                <FilterDateRange
                                    startValue={filterStartDate}
                                    endValue={filterEndDate}
                                    onStartChange={handleFilterStartDateChange}
                                    onEndChange={handleFilterEndDateChange}
                                    startId="filter_start_date"
                                    endId="filter_end_date"
                                    startShowFlash={filterStartFlash}
                                    endShowFlash={filterEndFlash}
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
                                    className="h-40 sm:h-48 rounded-lg flex items-center justify-center border border-blue-200"
                                    style={{ backgroundColor: schedule.hospital_color || '#eff6ff' }}
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
                                            className={`text-sm font-semibold text-center px-2 ${getCardTextClasses(isSelected)}`}
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
                                <p className={`${getCardInfoTextClasses(isSelected)}`}>
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
                                <p className={`${getCardInfoTextClasses(isSelected)}`}>
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
                                    <p className={`${getCardInfoTextClasses(isSelected)}`}>
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
                                    <p className={`${getCardInfoTextClasses(isSelected)}`}>
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
                selection={{
                    selectedCount: selectedSchedulesCount,
                    totalCount: filteredSchedules.length,
                    grandTotal: displayTotal,
                    selectAllMode: selectAllSchedulesMode,
                    onToggleAll: () => toggleAllSchedules(filteredSchedules.map((s) => s.id)),
                }}
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
