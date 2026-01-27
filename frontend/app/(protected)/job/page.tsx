'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { EntityCard } from '@/components/EntityCard'
import { FilterButtons, FilterOption } from '@/components/FilterButtons'
import { FilterPanel } from '@/components/FilterPanel'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { useEntityPage } from '@/hooks/useEntityPage'
import { protectedFetch } from '@/lib/api'
import { getCardInfoTextClasses, getCardTextClasses } from '@/lib/cardStyles'
import { formatDateTime } from '@/lib/tenantFormat'
import { JobResponse } from '@/types/api'
import { useEffect, useMemo, useState } from 'react'

// Tipo vazio para formulário (jobs não são editáveis)
type JobFormData = Record<string, never>

// Tipos vazios para requests (jobs não são criados/editados via UI)
type JobCreateRequest = Record<string, never>
type JobUpdateRequest = Record<string, never>

export default function JobPage() {
    const { settings } = useTenantSettings()

    // Constantes para filtros
    const ALL_JOB_TYPE_FILTERS: string[] = ['PING', 'EXTRACT_DEMAND', 'GENERATE_SCHEDULE', 'GENERATE_THUMBNAIL']
    const ALL_STATUS_FILTERS: string[] = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']

    // Filtros usando hook reutilizável
    const jobTypeFilters = useEntityFilters<string>({
        allFilters: ALL_JOB_TYPE_FILTERS,
        initialFilters: new Set(ALL_JOB_TYPE_FILTERS),
    })

    const statusFilters = useEntityFilters<string>({
        allFilters: ALL_STATUS_FILTERS,
        initialFilters: new Set(ALL_STATUS_FILTERS),
    })

    // Filtros de período de início (started_at)
    // "Desde" inicia vazio, "Até" inicia vazio
    const [startedAtFrom, setStartedAtFrom] = useState<Date | null>(null)
    const [startedAtTo, setStartedAtTo] = useState<Date | null>(null)

    // Configuração inicial (vazio, pois jobs não são editáveis)
    const initialFormData: JobFormData = {}

    // Mapeamentos (vazios, pois jobs não são editáveis)
    const mapEntityToFormData = (job: JobResponse): JobFormData => {
        return {}
    }

    const mapFormDataToCreateRequest = (formData: JobFormData): JobCreateRequest => {
        return {}
    }

    const mapFormDataToUpdateRequest = (formData: JobFormData): JobUpdateRequest => {
        return {}
    }

    // Validação (sempre válido, pois não há formulário)
    const validateFormData = (formData: JobFormData): string | null => {
        return null
    }

    // isEmptyCheck (sempre true, pois não há formulário)
    const isEmptyCheck = (formData: JobFormData): boolean => {
        return true
    }

    // Calcular additionalListParams reativo (apenas filtros suportados pela API)
    const additionalListParams = useMemo(() => {
        const params: Record<string, string | number | boolean | null> = {}

        // Job type: passar apenas se exatamente 1 estiver selecionado
        if (jobTypeFilters.selectedFilters.size === 1) {
            const jobType = Array.from(jobTypeFilters.selectedFilters)[0]
            params.job_type = jobType
        }

        // Status: passar apenas se exatamente 1 estiver selecionado
        if (statusFilters.selectedFilters.size === 1) {
            const status = Array.from(statusFilters.selectedFilters)[0]
            params.status = status
        }

        // Nota: filtros de data (started_at) são aplicados no frontend para evitar problemas de timezone

        return Object.keys(params).length > 0 ? params : undefined
    }, [jobTypeFilters.selectedFilters, statusFilters.selectedFilters])

    // Verificar se precisa filtrar no frontend (quando múltiplos valores estão selecionados ou há filtros de data)
    const needsFrontendFilter = useMemo(() => {
        // Se há filtros de data, sempre filtra no frontend (para evitar problemas de timezone)
        if (startedAtFrom || startedAtTo) {
            return true
        }

        const allJobTypesSelected = jobTypeFilters.selectedFilters.size === ALL_JOB_TYPE_FILTERS.length
        const allStatusSelected = statusFilters.selectedFilters.size === ALL_STATUS_FILTERS.length

        // Se todos estão selecionados, não precisa filtrar
        if (allJobTypesSelected && allStatusSelected) {
            return false
        }

        // Se apenas 1 de cada está selecionado, backend filtra (não precisa filtrar no frontend)
        const singleJobTypeSelected = jobTypeFilters.selectedFilters.size === 1
        const singleStatusSelected = statusFilters.selectedFilters.size === 1

        if (singleJobTypeSelected && singleStatusSelected) {
            return false
        }

        // Se múltiplos estão selecionados, precisa filtrar no frontend
        return true
    }, [jobTypeFilters.selectedFilters, statusFilters.selectedFilters, startedAtFrom, startedAtTo])

    // Estado para controlar interrupção e exclusão customizada
    const [interrupting, setInterrupting] = useState(false)
    const [deletingJobs, setDeletingJobs] = useState(false)

    // useEntityPage
    const {
        items: jobs,
        loading,
        error,
        setError,
        selectedItems: selectedJobs,
        toggleSelection: toggleJobSelection,
        clearSelection: clearJobSelection,
        toggleAll: toggleAllJobs,
        selectedCount: selectedJobsCount,
        selectAllMode: selectAllJobsMode,
        pagination,
        total,
        paginationHandlers,
        loadItems,
        actionBarErrorProps,
    } = useEntityPage<JobFormData, JobResponse, JobCreateRequest, JobUpdateRequest>({
        endpoint: '/api/job',
        entityName: 'job',
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
        additionalListParams,
        listEnabled: !!settings,
    })

    // Verificar se há jobs interrompíveis (PENDING ou RUNNING) selecionados
    const hasInterruptableJobs = useMemo(() => {
        if (selectedJobs.size === 0) return false
        const selectedJobsList = jobs.filter((job) => selectedJobs.has(job.id))
        return selectedJobsList.some(
            (job) => job.status === 'PENDING' || job.status === 'RUNNING'
        )
    }, [selectedJobs, jobs])

    // Verificar se há jobs excluíveis (COMPLETED ou FAILED) selecionados
    const hasDeletableJobs = useMemo(() => {
        if (selectedJobs.size === 0) return false
        const selectedJobsList = jobs.filter((job) => selectedJobs.has(job.id))
        return selectedJobsList.some(
            (job) => job.status === 'COMPLETED' || job.status === 'FAILED'
        )
    }, [selectedJobs, jobs])

    // Handler para interromper jobs selecionados
    const handleInterruptSelected = async () => {
        if (selectedJobs.size === 0) return

        setInterrupting(true)
        setError(null)

        try {
            // Verificar diretamente o selectAllMode para evitar stale closure
            let jobsToProcess: JobResponse[]

            if (selectAllJobsMode) {
                // Modo "todos": buscar todos os jobs que atendem aos filtros atuais
                // Buscar em batches de 100 (limite máximo da API)
                const BATCH_SIZE = 100
                jobsToProcess = []
                let offset = 0
                let hasMore = true

                while (hasMore) {
                    const params = new URLSearchParams()
                    params.set('limit', String(BATCH_SIZE))
                    params.set('offset', String(offset))

                    if (additionalListParams) {
                        Object.entries(additionalListParams).forEach(([key, value]) => {
                            if (value !== null && value !== undefined) {
                                params.set(key, String(value))
                            }
                        })
                    }

                    const response = await protectedFetch<{ items: JobResponse[]; total: number }>(
                        `/api/job/list?${params.toString()}`
                    )
                    jobsToProcess.push(...response.items)

                    offset += BATCH_SIZE
                    hasMore = offset < response.total
                }
            } else {
                // Usar apenas os jobs selecionados
                jobsToProcess = jobs.filter((job) => selectedJobs.has(job.id))
            }

            // Filtrar apenas jobs que podem ser interrompidos
            const jobsToInterrupt = jobsToProcess.filter(
                (job) => job.status === 'PENDING' || job.status === 'RUNNING'
            )

            if (jobsToInterrupt.length === 0) {
                throw new Error('Nenhum job pode ser interrompido')
            }

            // Chamar API para interromper
            const interruptPromises = jobsToInterrupt.map(async (job) => {
                await protectedFetch(`/api/job/${job.id}/cancel`, {
                    method: 'POST',
                })
            })

            await Promise.all(interruptPromises)

            // Recarregar lista para atualizar os cards
            await loadItems()

            // Limpar seleção
            clearJobSelection()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao interromper jobs'
            setError(message)
            console.error('Erro ao interromper jobs:', err)
        } finally {
            setInterrupting(false)
        }
    }

    // Handler customizado para excluir jobs (apenas COMPLETED e FAILED)
    const handleDeleteJobsSelected = async () => {
        if (selectedJobs.size === 0) return

        setDeletingJobs(true)
        setError(null)

        try {
            let jobsToProcess: JobResponse[]

            if (selectAllJobsMode) {
                // Modo "todos": buscar todos os jobs que atendem aos filtros atuais
                // Buscar em batches de 100 (limite máximo da API)
                const BATCH_SIZE = 100
                jobsToProcess = []
                let offset = 0
                let hasMore = true

                while (hasMore) {
                    const params = new URLSearchParams()
                    params.set('limit', String(BATCH_SIZE))
                    params.set('offset', String(offset))

                    if (additionalListParams) {
                        Object.entries(additionalListParams).forEach(([key, value]) => {
                            if (value !== null && value !== undefined) {
                                params.set(key, String(value))
                            }
                        })
                    }

                    const response = await protectedFetch<{ items: JobResponse[]; total: number }>(
                        `/api/job/list?${params.toString()}`
                    )
                    jobsToProcess.push(...response.items)

                    offset += BATCH_SIZE
                    hasMore = offset < response.total
                }
            } else {
                // Usar apenas os jobs selecionados
                jobsToProcess = jobs.filter((job) => selectedJobs.has(job.id))
            }

            // Filtrar apenas jobs que podem ser excluídos (COMPLETED ou FAILED)
            const jobsToDelete = jobsToProcess.filter(
                (job) => job.status === 'COMPLETED' || job.status === 'FAILED'
            )

            if (jobsToDelete.length === 0) {
                throw new Error('Nenhum job pode ser excluído')
            }

            // Chamar API para excluir
            const deletePromises = jobsToDelete.map(async (job) => {
                await protectedFetch(`/api/job/${job.id}`, {
                    method: 'DELETE',
                })
            })

            await Promise.all(deletePromises)

            // Recarregar lista para atualizar os cards
            await loadItems()

            // Limpar seleção
            clearJobSelection()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao excluir jobs'
            setError(message)
            console.error('Erro ao excluir jobs:', err)
        } finally {
            setDeletingJobs(false)
        }
    }

    // Filtrar jobs no frontend quando necessário
    const filteredJobs = useMemo(() => {
        let filtered = jobs

        // Filtro por job type (no frontend apenas quando múltiplos estão selecionados)
        if (needsFrontendFilter) {
            if (jobTypeFilters.selectedFilters.size < ALL_JOB_TYPE_FILTERS.length) {
                filtered = filtered.filter((job) => jobTypeFilters.selectedFilters.has(job.job_type))
            }
        }

        // Filtro por status (no frontend apenas quando múltiplos estão selecionados)
        if (needsFrontendFilter) {
            if (statusFilters.selectedFilters.size < ALL_STATUS_FILTERS.length) {
                filtered = filtered.filter((job) => statusFilters.selectedFilters.has(job.status))
            }
        }

        // Filtro por período: started_at >= "Desde" e started_at <= "Até"
        if (startedAtFrom) {
            filtered = filtered.filter((job) => {
                if (!job.started_at) return false
                const jobStarted = new Date(job.started_at)
                return jobStarted >= startedAtFrom
            })
        }

        if (startedAtTo) {
            filtered = filtered.filter((job) => {
                if (!job.started_at) return false
                const jobStarted = new Date(job.started_at)
                return jobStarted <= startedAtTo
            })
        }

        return filtered
    }, [jobs, jobTypeFilters.selectedFilters, statusFilters.selectedFilters, needsFrontendFilter, startedAtFrom, startedAtTo])

    // Aplicar paginação no frontend quando há filtro no frontend
    const paginatedJobs = useMemo(() => {
        if (!needsFrontendFilter) {
            return filteredJobs // Backend já paginou
        }
        // Paginar no frontend
        const start = pagination.offset
        const end = start + pagination.limit
        return filteredJobs.slice(start, end)
    }, [filteredJobs, needsFrontendFilter, pagination.offset, pagination.limit])

    // Ajustar total para refletir filtros
    const displayTotal = useMemo(() => {
        if (!needsFrontendFilter) {
            return total // Usar total do backend
        }
        return filteredJobs.length // Total após filtro no frontend
    }, [filteredJobs, needsFrontendFilter, total])

    // Resetar offset quando filtros mudarem
    useEffect(() => {
        paginationHandlers.onFirst()
    }, [jobTypeFilters.selectedFilters, statusFilters.selectedFilters, startedAtFrom, startedAtTo])

    // Função auxiliar para obter cor do status
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'bg-yellow-100 text-yellow-800'
            case 'RUNNING':
                return 'bg-blue-100 text-blue-800'
            case 'COMPLETED':
                return 'bg-green-100 text-green-800'
            case 'FAILED':
                return 'bg-red-100 text-red-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    // Função auxiliar para obter label do status
    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'Pendente'
            case 'RUNNING':
                return 'Em execução'
            case 'COMPLETED':
                return 'Concluído'
            case 'FAILED':
                return 'Falhou'
            default:
                return status
        }
    }

    // Função auxiliar para obter label do tipo
    const getJobTypeLabel = (jobType: string) => {
        switch (jobType) {
            case 'PING':
                return 'Ping'
            case 'EXTRACT_DEMAND':
                return 'Extrair Demanda'
            case 'GENERATE_SCHEDULE':
                return 'Gerar Escala'
            case 'GENERATE_THUMBNAIL':
                return 'Gerar Miniatura'
            default:
                return jobType
        }
    }

    // Função auxiliar para obter cor de fundo para o ícone (padrão do painel de arquivos)
    const getStatusBackgroundColor = (status: string) => {
        switch (status) {
            case 'PENDING':
                return '#FCD34D' // yellow-300
            case 'RUNNING':
                return '#60A5FA' // blue-400
            case 'COMPLETED':
                return '#34D399' // green-400
            case 'FAILED':
                return '#F87171' // red-400
            default:
                return '#94A3B8' // slate-400
        }
    }

    // Função auxiliar para obter ícone do status (padrão do painel de arquivos)
    const getStatusIcon = (status: string) => {
        const iconClass = "w-full h-full"
        const statusColor = getStatusBackgroundColor(status)

        switch (status) {
            case 'PENDING':
                return (
                    <svg
                        className={iconClass}
                        fill="none"
                        stroke={statusColor}
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                )
            case 'RUNNING':
                return (
                    <svg
                        className={iconClass}
                        fill="none"
                        stroke={statusColor}
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                        />
                    </svg>
                )
            case 'COMPLETED':
                return (
                    <svg
                        className={iconClass}
                        fill="none"
                        stroke={statusColor}
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M5 13l4 4L19 7"
                        />
                    </svg>
                )
            case 'FAILED':
                return (
                    <svg
                        className={iconClass}
                        fill="none"
                        stroke={statusColor}
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M6 18L18 6M6 6l12 12"
                        />
                    </svg>
                )
            default:
                return (
                    <svg
                        className={iconClass}
                        fill="none"
                        stroke={statusColor}
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                    </svg>
                )
        }
    }

    // Opções para os filtros
    const jobTypeOptions: FilterOption<string>[] = [
        { value: 'PING', label: 'Ping', color: 'text-gray-600' },
        { value: 'EXTRACT_DEMAND', label: 'Extrair Demanda', color: 'text-blue-600' },
        { value: 'GENERATE_SCHEDULE', label: 'Gerar Escala', color: 'text-green-600' },
        { value: 'GENERATE_THUMBNAIL', label: 'Gerar Miniatura', color: 'text-purple-600' },
    ]

    const statusOptions: FilterOption<string>[] = [
        { value: 'PENDING', label: 'Pendente', color: 'text-yellow-600' },
        { value: 'RUNNING', label: 'Em execução', color: 'text-blue-600' },
        { value: 'COMPLETED', label: 'Concluído', color: 'text-green-600' },
        { value: 'FAILED', label: 'Falhou', color: 'text-red-600' },
    ]

    // Botões do ActionBar
    // Comportamento: mostra "Excluir" se houver jobs excluíveis (COMPLETED/FAILED)
    // Mostra "Interromper" se houver jobs interrompíveis (PENDING/RUNNING)
    // Regra de negócio: PENDING/RUNNING só podem ser interrompidos, COMPLETED/FAILED só podem ser excluídos
    const actionBarButtons = useActionBarButtons({
        isEditing: false,
        selectedCount: hasDeletableJobs ? selectedJobsCount : 0, // Botão "Excluir" só aparece se houver excluíveis
        hasChanges: false,
        submitting: false,
        deleting: deletingJobs,
        onCancel: clearJobSelection,
        onDelete: handleDeleteJobsSelected, // Handler customizado que exclui apenas COMPLETED/FAILED
        onSave: async () => { },
        // Usar additionalSelectedCount para fazer o botão "Cancelar" aparecer mesmo quando não há excluíveis
        additionalSelectedCount: hasInterruptableJobs && !hasDeletableJobs ? selectedJobsCount : 0,
        customActions: hasInterruptableJobs
            ? [
                // Botão "Interromper" aparece quando há jobs interrompíveis selecionados
                {
                    label: 'Interromper',
                    onClick: handleInterruptSelected,
                    disabled: interrupting || deletingJobs,
                    loading: interrupting,
                },
            ]
            : [],
    })

    return (
        <>
            <CardPanel
                title="Jobs"
                description="Visualize os jobs do sistema"
                totalCount={filteredJobs.length}
                selectedCount={selectedJobs.size}
                loading={loading}
                loadingMessage="Carregando jobs..."
                emptyMessage="Nenhum job encontrado."
                error={error}
                filterContent={
                    <FilterPanel>
                        <FormFieldGrid cols={1} smCols={2} gap={4}>
                            <TenantDateTimePicker
                                label="Iniciado desde"
                                value={startedAtFrom}
                                onChange={setStartedAtFrom}
                                id="started_at_from_filter"
                            />
                            <TenantDateTimePicker
                                label="Iniciado até"
                                value={startedAtTo}
                                onChange={setStartedAtTo}
                                id="started_at_to_filter"
                            />
                        </FormFieldGrid>
                        <FilterButtons
                            title="Tipo"
                            options={jobTypeOptions}
                            selectedValues={jobTypeFilters.selectedFilters}
                            onToggle={jobTypeFilters.toggleFilter}
                            onToggleAll={jobTypeFilters.toggleAll}
                        />
                        <FilterButtons
                            title="Situação"
                            options={statusOptions}
                            selectedValues={statusFilters.selectedFilters}
                            onToggle={statusFilters.toggleFilter}
                            onToggleAll={statusFilters.toggleAll}
                        />
                    </FilterPanel>
                }
            >
                {(needsFrontendFilter ? paginatedJobs : filteredJobs).map((job) => {
                    const isSelected = selectedJobs.has(job.id)
                    return (
                        <EntityCard
                            key={job.id}
                            id={job.id}
                            isSelected={isSelected}
                            footer={
                                <CardFooter
                                    isSelected={isSelected}
                                    date={job.created_at}
                                    settings={settings}
                                    onToggleSelection={(e) => {
                                        e.stopPropagation()
                                        toggleJobSelection(job.id)
                                    }}
                                    onEdit={() => { }} // Função vazia (não usada)
                                    disabled={false}
                                    deleteTitle={isSelected ? 'Desmarcar' : 'Marcar'}
                                    showEdit={false} // Ocultar botão de editar
                                />
                            }
                        >
                            {/* Corpo - Tipo, Status, Datas e Erro */}
                            <div className="mb-3">
                                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                    <div className="flex flex-col items-center justify-center text-gray-500 mb-4">
                                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                                            {getStatusIcon(job.status)}
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${getCardTextClasses(isSelected)}`}
                                            title={getJobTypeLabel(job.job_type)}
                                        >
                                            {getJobTypeLabel(job.job_type)}
                                        </h3>
                                        <div className="mt-2 flex flex-wrap gap-1 justify-center px-2">
                                            <span
                                                className={`px-2 py-0.5 text-xs font-medium rounded ${getStatusColor(job.status)} flex items-center gap-2`}
                                            >
                                                {getStatusLabel(job.status)}
                                                {(job.status === 'RUNNING' || job.status === 'PENDING') && <LoadingSpinner />}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Detalhes adicionais */}
                                    <div className="space-y-1 text-sm">
                                        {job.started_at && (
                                            <p className={`${getCardInfoTextClasses(isSelected)}`}>
                                                <span className="font-medium">Iniciado em:</span>{' '}
                                                {settings
                                                    ? formatDateTime(job.started_at, settings)
                                                    : new Date(job.started_at).toLocaleString('pt-BR', {
                                                        day: '2-digit',
                                                        month: '2-digit',
                                                        year: 'numeric',
                                                        hour: '2-digit',
                                                        minute: '2-digit',
                                                    })}
                                            </p>
                                        )}
                                        {job.completed_at && (
                                            <p className={`${getCardInfoTextClasses(isSelected)}`}>
                                                <span className="font-medium">Concluído em:</span>{' '}
                                                {settings
                                                    ? formatDateTime(job.completed_at, settings)
                                                    : new Date(job.completed_at).toLocaleString('pt-BR', {
                                                        day: '2-digit',
                                                        month: '2-digit',
                                                        year: 'numeric',
                                                        hour: '2-digit',
                                                        minute: '2-digit',
                                                    })}
                                            </p>
                                        )}
                                        {job.error_message && (
                                            <div className={`mt-2 p-2 rounded bg-red-50 border border-red-200`}>
                                                <p className={`text-xs font-medium text-red-800`}>
                                                    <span className="font-semibold">Erro:</span> {job.error_message}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </EntityCard>
                    )
                })}
            </CardPanel>

            <ActionBarSpacer />

            <ActionBar
                selection={{
                    selectedCount: selectedJobsCount,
                    totalCount: filteredJobs.length,
                    grandTotal: displayTotal,
                    selectAllMode: selectAllJobsMode,
                    onToggleAll: () => toggleAllJobs(filteredJobs.map((j) => j.id)),
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
