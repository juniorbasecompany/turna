'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterButtons, FilterPanel, FilterSelect } from '@/components/filter'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { JsonEditor } from '@/components/JsonEditor'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { Pagination } from '@/components/Pagination'
import { TenantDateTimePicker } from '@/components/TenantDateTimePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useActionBarRightButtons } from '@/hooks/useActionBarRightButtons'
import { useEntityFilters } from '@/hooks/useEntityFilters'
import { useEntityPage } from '@/hooks/useEntityPage'
import { useReportButton } from '@/hooks/useReportButton'
import { protectedFetch } from '@/lib/api'
import { getCardSecondaryTextClasses, getCardTextClasses } from '@/lib/cardStyles'
import { getActionBarErrorProps } from '@/lib/entityUtils'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

interface FileResponse {
    id: number
    filename: string
    content_type: string
    file_size: number
    created_at: string
    hospital_id: number
    hospital_name: string
    hospital_color: string | null
    can_delete: boolean
    job_status: string | null
}

interface Hospital {
    id: number
    tenant_id: number
    name: string
    prompt: string
    created_at: string
    updated_at: string
}

interface HospitalListResponse {
    items: Hospital[]
    total: number
}

interface FileListResponse {
    items: FileResponse[]
    total: number
}

type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

// Tipos para useEntityPage (simplificados, pois File não tem formulário tradicional)
type FileFormData = Record<string, never> // Objeto vazio, pois não há formulário tradicional

interface FileCreateRequest {
    // Não será usado para upload, mas necessário para o hook
    [key: string]: never
}

interface FileUpdateRequest {
    // Não será usado, mas necessário para o hook
    [key: string]: never
}

interface PendingFile {
    file: File
    fileId?: number
    jobId?: number
    jobStatus?: JobStatus
    error?: string
    uploading?: boolean
}

interface FileUploadResponse {
    file_id: number
    filename: string
    content_type: string
    file_size: number
    s3_url: string
    presigned_url: string
}

interface JobExtractResponse {
    job_id: number
}

interface JobResponse {
    id: number
    tenant_id: number
    job_type: string
    status: JobStatus
    input_data: Record<string, unknown> | null
    result_data: Record<string, unknown> | null
    error_message: string | null
    created_at: string
    updated_at: string
    started_at: string | null
    completed_at: string | null
}

/**
 * Formata bytes para formato legível (ex: "1.5 MB")
 */
function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}


/**
 * Verifica se o tipo de arquivo é uma imagem
 */
function isImage(contentType: string): boolean {
    return contentType.startsWith('image/')
}

/**
 * Obtém informações de ícone e cor por tipo de arquivo
 */
function getFileTypeInfo(contentType: string): { icon: JSX.Element; colorClass: string } {
    if (contentType === 'application/pdf') {
        return {
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
            ),
            colorClass: 'text-red-500'
        }
    }
    if (isImage(contentType)) {
        return {
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
            ),
            colorClass: 'text-blue-500'
        }
    }
    if (contentType.includes('spreadsheet') || contentType.includes('excel') || contentType.includes('csv')) {
        return {
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            ),
            colorClass: 'text-green-500'
        }
    }
    // Outros tipos
    return {
        icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
        ),
        colorClass: 'text-slate-500'
    }
}

/**
 * Obtém classes de cor para o card baseado no status do job
 */
function getJobStatusCardClasses(jobStatus: string | null): { border: string; bg: string; text: string; borderColor: string } {
    switch (jobStatus) {
        case 'PENDING':
            return {
                border: 'border-yellow-300',
                bg: 'bg-yellow-50',
                text: 'text-yellow-900',
                borderColor: '#FCD34D' // yellow-300
            }
        case 'RUNNING':
            return {
                border: 'border-blue-300',
                bg: 'bg-blue-50',
                text: 'text-blue-900',
                borderColor: '#93C5FD' // blue-300
            }
        case 'COMPLETED':
            return {
                border: 'border-green-300',
                bg: 'bg-green-50',
                text: 'text-green-900',
                borderColor: '#86EFAC' // green-300
            }
        case 'FAILED':
            return {
                border: 'border-red-300',
                bg: 'bg-red-50',
                text: 'text-red-900',
                borderColor: '#FCA5A5' // red-300
            }
        default:
            return {
                border: 'border-slate-200',
                bg: 'bg-white',
                text: 'text-gray-900',
                borderColor: '#E2E8F0' // slate-200
            }
    }
}

/**
 * Obtém o texto descritivo do status do job
 */
function getJobStatusText(jobStatus: string | null): string {
    switch (jobStatus) {
        case 'PENDING':
            return 'Na fila para ser lido'
        case 'RUNNING':
            return 'Lendo o conteúdo do arquivo'
        case 'COMPLETED':
            return 'Conteúdo lido'
        case 'FAILED':
            return 'Não foi possível ler o conteúdo'
        default:
            return 'Pronto para ser lido'
    }
}

/**
 * Obtém a cor de fundo para o campo de status
 */
function getStatusBackgroundColor(jobStatus: string | null): string {
    switch (jobStatus) {
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

/**
 * Obtém a cor do texto para o campo de status
 */
function getStatusTextColor(jobStatus: string | null): string {
    // Texto branco para todos os status para melhor contraste
    return '#FFFFFF'
}

/**
 * Obtém o ícone SVG para o status
 */
function getStatusIcon(jobStatus: string | null): JSX.Element {
    const iconClass = "w-10 h-10 shrink-0"
    const statusColor = getStatusBackgroundColor(jobStatus)

    switch (jobStatus) {
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

/**
 * Abre o arquivo em nova aba (visualização ou download se necessário)
 */
function handleFileDownload(fileId: number, filename: string) {
    const url = `/api/file/${fileId}/proxy`
    // Abrir em nova aba - o navegador decide se mostra ou faz download
    window.open(url, '_blank')
}

/**
 * Componente de thumbnail para arquivo pendente (imagem local)
 */
function PendingFileImageThumbnail({ file }: { file: File }) {
    const [objectUrl, setObjectUrl] = useState<string | null>(null)

    useEffect(() => {
        // Criar URL do objeto apenas uma vez
        const url = URL.createObjectURL(file)
        setObjectUrl(url)

        // Limpar URL quando componente desmontar
        return () => {
            URL.revokeObjectURL(url)
        }
    }, [file])

    if (!objectUrl) {
        return (
            <div className="w-full h-40 sm:h-48 bg-slate-50 rounded-lg flex items-center justify-center">
                <LoadingSpinner />
            </div>
        )
    }

    return (
        <div className="w-full h-40 sm:h-48 bg-slate-50 rounded-lg flex items-center justify-center overflow-hidden">
            <img
                src={objectUrl}
                alt={file.name}
                className="w-full h-full object-cover rounded-lg"
            />
        </div>
    )
}

/**
 * Componente de thumbnail do arquivo (preview no corpo do card)
 * Exibe thumbnail WebP se disponível, ou fundo branco com extensão do arquivo
 */
function FileThumbnail({ file, onClick }: { file: FileResponse; onClick?: () => void }) {
    // URL do endpoint de thumbnail
    const thumbnailUrl = `/api/file/${file.id}/thumbnail`
    const [imageError, setImageError] = useState(false)
    const [isLoading, setIsLoading] = useState(true)
    const [retryCount, setRetryCount] = useState(0)
    const [imageSrc, setImageSrc] = useState<string | null>(null)
    const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)
    const pollingRef = useRef(false)
    const retryCountRef = useRef(0)

    // Extrair extensão do arquivo
    const getFileExtension = (filename: string, contentType: string): string => {
        // Tentar extrair do filename primeiro
        const match = filename.match(/\.([^.]+)$/)
        if (match) {
            return match[1].toUpperCase()
        }
        // Fallback: extrair do content_type
        if (contentType === 'application/pdf') {
            return 'PDF'
        }
        const parts = contentType.split('/')
        if (parts.length > 1) {
            return parts[1].toUpperCase()
        }
        return 'FILE'
    }

    const fileExtension = getFileExtension(file.filename, file.content_type)

    // Verificar se thumbnail existe e fazer polling se necessário
    const checkThumbnail = useCallback(async () => {
        if (pollingRef.current) return // Evitar múltiplas verificações simultâneas

        try {
            pollingRef.current = true
            const response = await fetch(thumbnailUrl, {
                method: 'GET',
                credentials: 'include',
            })

            if (response.ok) {
                // Thumbnail existe, definir src para carregar
                setImageSrc(`${thumbnailUrl}?t=${Date.now()}`)
                setIsLoading(true)
                setImageError(false)
                setRetryCount(0)
                retryCountRef.current = 0
                pollingRef.current = false
            } else if (response.status === 404) {
                // Thumbnail ainda não existe, fazer retry (usar ref para evitar closure obsoleta)
                const currentRetry = retryCountRef.current

                // Se já tentamos muitas vezes (5 tentativas = ~15 segundos), mostrar fallback
                if (currentRetry >= 5) {
                    setIsLoading(false)
                    setImageError(true)
                    pollingRef.current = false
                    return
                }

                // Aguardar antes de tentar novamente (3 segundos)
                const delay = 3000

                retryTimeoutRef.current = setTimeout(() => {
                    retryCountRef.current += 1
                    setRetryCount((prev) => prev + 1)
                    pollingRef.current = false
                    checkThumbnail()
                }, delay)
            } else {
                // Outro erro
                setIsLoading(false)
                setImageError(true)
                pollingRef.current = false
            }
        } catch (error) {
            // Em caso de erro de rede, tentar carregar mesmo assim (pode ser CORS ou outro problema)
            setImageSrc(`${thumbnailUrl}?t=${Date.now()}`)
            setIsLoading(true)
            pollingRef.current = false
        }
    }, [file.id, thumbnailUrl])

    // Limpar timeout quando componente desmontar
    useEffect(() => {
        // Verificar thumbnail na montagem
        checkThumbnail()

        return () => {
            if (retryTimeoutRef.current) {
                clearTimeout(retryTimeoutRef.current)
            }
            pollingRef.current = false
        }
    }, [checkThumbnail])

    // Resetar retry count quando a imagem carregar com sucesso
    const handleImageLoad = useCallback(() => {
        setIsLoading(false)
        setImageError(false)
        setRetryCount(0)
        retryCountRef.current = 0
        if (retryTimeoutRef.current) {
            clearTimeout(retryTimeoutRef.current)
            retryTimeoutRef.current = null
        }
        pollingRef.current = false
    }, [file.id])

    // Handler para erro ao carregar imagem (mesmo após verificação HEAD)
    const handleImageError = useCallback(() => {
        setIsLoading(false)
        setImageError(true)
        pollingRef.current = false
    }, [file.id])

    return (
        <div className="relative w-full h-full bg-white rounded-lg overflow-hidden group">
            <button
                onClick={onClick}
                className="w-full h-full flex items-center justify-center cursor-pointer transition-all duration-200 relative"
                title="Clique para marcar para leitura"
            >
                {!imageError && imageSrc ? (
                    <img
                        key={imageSrc} // Forçar re-render quando imageSrc mudar
                        src={imageSrc || undefined}
                        alt={file.filename}
                        className="w-full h-full object-cover rounded-lg"
                        onLoad={handleImageLoad}
                        onError={handleImageError}
                        style={{ display: isLoading ? 'none' : 'block' }}
                    />
                ) : null}
                {(imageError || isLoading) && (
                    <div className="flex flex-col items-center justify-center w-full h-full bg-white absolute inset-0">
                        {isLoading ? (
                            <LoadingSpinner />
                        ) : (
                            <span className="text-2xl sm:text-3xl font-semibold text-gray-400">
                                {fileExtension}
                            </span>
                        )}
                    </div>
                )}
            </button>
            {/* Botão de lupa no canto superior direito */}
            <button
                onClick={(e) => {
                    e.stopPropagation()
                    handleFileDownload(file.id, file.filename)
                }}
                className="absolute top-2 right-2 p-2 bg-white/90 rounded-md shadow-md transition-all duration-200 cursor-pointer"
                title="Abrir arquivo em nova janela"
            >
                <svg
                    className="w-5 h-5 text-gray-700"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                </svg>
            </button>
        </div>
    )
}

export default function FilesPage() {
    const { settings } = useTenantSettings()
    const fileInputRef = useRef<HTMLInputElement>(null)
    const processingRef = useRef(false)
    const processedFilesRef = useRef<Set<string>>(new Set())
    const [bottomBarMessage, setBottomBarMessage] = useState<string | null>(null)
    const [reading, setReading] = useState(false)
    const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
    const [uploading, setUploading] = useState(false)
    const pollingIntervals = useRef<Map<number, NodeJS.Timeout>>(new Map())

    // Filtros de período usando TenantDateTimePicker (Date objects com hora)
    // Inicializar filterStartDate com primeiro dia da semana atual (segunda-feira) às 00:00, filterEndDate vazio
    const [filterStartDate, setFilterStartDate] = useState<Date | null>(() => {
        const today = new Date()
        const dayOfWeek = today.getDay() // 0=domingo, 1=segunda, ..., 6=sábado
        // Calcular quantos dias voltar para chegar na segunda-feira
        // Se hoje é domingo (0), volta 6 dias; se segunda (1), volta 0; se terça (2), volta 1, etc.
        const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1
        const monday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - daysToSubtract, 0, 0, 0, 0)
        return monday
    })

    const [filterEndDate, setFilterEndDate] = useState<Date | null>(null)

    // Títulos dos filtros: definidos uma vez, usados no painel e no cabeçalho do relatório
    const FILTER_HOSPITAL_LABEL = 'Hospital'
    const FILTER_START_DATE_LABEL = 'Cadastrados desde'
    const FILTER_END_DATE_LABEL = 'Cadastrados até'

    const [filterHospitalId, setFilterHospitalId] = useState<number | null>(null)
    const [hospitalList, setHospitalList] = useState<Hospital[]>([])
    const [loadingHospitalList, setLoadingHospitalList] = useState(true)

    // Filtro de status usando hook reutilizável (retorna array; array vazio = zero resultados)
    const ALL_STATUS_FILTERS: (JobStatus | null)[] = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', null]
    const statusFilters = useEntityFilters<JobStatus | null>({
        allFilters: ALL_STATUS_FILTERS,
    })

    // Configuração inicial para useEntityPage (simplificada, pois File não tem formulário tradicional)
    const initialFormData: FileFormData = {}

    // Mapeamentos (simplificados, pois File não tem formulário tradicional)
    const mapEntityToFormData = (file: FileResponse): FileFormData => {
        return {}
    }

    const mapFormDataToCreateRequest = (formData: FileFormData): FileCreateRequest => {
        return {}
    }

    const mapFormDataToUpdateRequest = (formData: FileFormData): FileUpdateRequest => {
        return {}
    }

    const validateFormData = (formData: FileFormData): string | null => {
        // Validação customizada é feita em handleSave para edição de JSON
        return null
    }

    const isEmptyCheck = (formData: FileFormData): boolean => {
        // Sempre retorna true, pois não há formulário tradicional
        return true
    }

    // Calcular additionalListParams reativo (apenas filtros suportados pela API)
    const additionalListParams = useMemo(() => {
        if (!settings) return undefined
        return {
            start_at: filterStartDate ? filterStartDate.toISOString() : null,
            end_at: filterEndDate ? filterEndDate.toISOString() : null,
            hospital_id: filterHospitalId || null,
        }
    }, [filterStartDate, filterEndDate, filterHospitalId, settings])

    const reportFilters = useMemo((): { label: string; value: string }[] => {
        const list: { label: string; value: string }[] = []
        if (filterHospitalId != null) {
            const hospital = hospitalList.find((h) => h.id === filterHospitalId)
            list.push({
                label: FILTER_HOSPITAL_LABEL,
                value: hospital?.name ?? String(filterHospitalId),
            })
        }
        if (filterStartDate) {
            list.push({
                label: FILTER_START_DATE_LABEL,
                value: filterStartDate.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }),
            })
        }
        if (filterEndDate) {
            list.push({
                label: FILTER_END_DATE_LABEL,
                value: filterEndDate.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }),
            })
        }
        return list
    }, [filterHospitalId, filterStartDate, filterEndDate, hospitalList])

    // useEntityPage
    const {
        items: files,
        loading,
        error,
        setError,
        deleting,
        selectedItems: selectedFiles,
        toggleSelection: toggleFileSelection,
        clearSelection,
        toggleAll: toggleAllFiles,
        selectedCount: selectedFilesCount,
        selectAllMode: selectAllFilesMode,
        getSelectedIdsForAction: getSelectedFileIdsForAction,
        pagination,
        total,
        paginationHandlers,
        handleDeleteSelected,
        loadItems,
    } = useEntityPage<FileFormData, FileResponse, FileCreateRequest, FileUpdateRequest>({
        endpoint: '/api/file',
        entityName: 'arquivo',
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
        additionalListParams,
        listEnabled: !!settings,
    })

    // Estado local para arquivos (permite atualização direta via polling)
    const [localFiles, setLocalFiles] = useState<FileResponse[]>(files)

    // Sincronizar localFiles com files quando files mudar (vindo do hook)
    useEffect(() => {
        setLocalFiles(files)
    }, [files])

    // Flash vermelho no card de upload quando não há hospital selecionado
    const [uploadCardFlash, setUploadCardFlash] = useState(false)
    // Flash vermelho no campo hospital quando não há hospital selecionado
    const [hospitalFieldFlash, setHospitalFieldFlash] = useState(false)

    // Estados para edição
    const [showEditArea, setShowEditArea] = useState(false)
    const [editingFile, setEditingFile] = useState<FileResponse | null>(null)
    const [editingJobId, setEditingJobId] = useState<number | null>(null)
    const [jsonContent, setJsonContent] = useState<string>('')
    const [originalJsonContent, setOriginalJsonContent] = useState<string>('')
    const [loadingJson, setLoadingJson] = useState(false)
    const [submitting, setSubmitting] = useState(false)

    // Carregar hospitais ao montar
    useEffect(() => {
        async function loadHospitalList() {
            try {
                setLoadingHospitalList(true)
                const data = await protectedFetch<HospitalListResponse>('/api/hospital/list')
                setHospitalList(data.items)
            } catch (err) {
                // Exibir erro no ActionBar
                const message = err instanceof Error ? err.message : 'Erro ao carregar hospitais'
                setError(message)
                console.error('Erro ao carregar hospitais:', err)
            } finally {
                setLoadingHospitalList(false)
            }
        }

        loadHospitalList()
    }, [])

    // Validar intervalo de datas
    useEffect(() => {
        if (filterStartDate && filterEndDate && filterStartDate > filterEndDate) {
            setError('Data inicial deve ser menor ou igual à data final')
        }
    }, [filterStartDate, filterEndDate, setError])

    // Resetar offset quando filtros mudarem
    useEffect(() => {
        paginationHandlers.onFirst()
        // eslint-disable-next-line react-hooks/exhaustive-deps -- resetar página ao mudar filtros
    }, [statusFilters.selectedValues])

    // Filtrar por status no frontend (API File não aceita status_list; job_status é derivado)
    const filteredFiles = useMemo(() => {
        if (!statusFilters.isFilterActive) return localFiles
        return localFiles.filter((file) => {
            const status = file.job_status === null ? null : (file.job_status as JobStatus)
            return statusFilters.selectedValues.includes(status)
        })
    }, [localFiles, statusFilters])

    const paginatedFiles = useMemo(() => {
        if (!statusFilters.isFilterActive) return filteredFiles
        return filteredFiles.slice(pagination.offset, pagination.offset + pagination.limit)
    }, [filteredFiles, statusFilters.selectedValues, statusFilters.isFilterActive, pagination.offset, pagination.limit])

    const displayTotal = statusFilters.isFilterActive ? filteredFiles.length : total

    // Handlers para mudança de data no TenantDateTimePicker
    const handleStartDateChange = (date: Date | null) => {
        setFilterStartDate(date)
        paginationHandlers.onFirst() // Resetar paginação ao mudar filtro
    }

    const handleEndDateChange = (date: Date | null) => {
        setFilterEndDate(date)
        paginationHandlers.onFirst() // Resetar paginação ao mudar filtro
    }

    const handleHospitalChange = (hospitalId: number | null) => {
        setFilterHospitalId(hospitalId)
        paginationHandlers.onFirst() // Resetar paginação ao mudar filtro
        setBottomBarMessage(null) // Limpar mensagem ao selecionar hospital
    }

    // Buscar JSON do arquivo através do job
    const fetchFileJson = useCallback(async (fileId: number): Promise<{ json: string; jobId: number | null }> => {
        try {
            // Buscar jobs do tipo extract_demand para este arquivo
            const jobsResponse = await protectedFetch<{ items: JobResponse[]; total: number }>(
                `/api/job/list?job_type=extract_demand&limit=100`
            )

            // Encontrar o job mais recente com status COMPLETED para este arquivo
            const completedJob = jobsResponse.items
                .filter(job => {
                    const inputData = job.input_data as { file_id?: number } | null
                    return inputData?.file_id === fileId && job.status === 'COMPLETED'
                })
                .sort((a, b) => {
                    const dateA = new Date(a.completed_at || a.created_at).getTime()
                    const dateB = new Date(b.completed_at || b.created_at).getTime()
                    return dateB - dateA
                })[0]

            if (completedJob && completedJob.result_data) {
                return { json: JSON.stringify(completedJob.result_data, null, 2), jobId: completedJob.id }
            }

            return { json: JSON.stringify({ meta: {}, demands: [] }, null, 2), jobId: null }
        } catch (err) {
            console.error('Erro ao buscar JSON do arquivo:', err)
            return { json: JSON.stringify({ error: 'Erro ao carregar dados do arquivo' }, null, 2), jobId: null }
        }
    }, [])

    // Abrir edição do arquivo
    const handleEditClick = useCallback(async (file: FileResponse) => {
        setEditingFile(file)
        setShowEditArea(true)
        setLoadingJson(true)
        setError(null)

        try {
            const { json, jobId } = await fetchFileJson(file.id)
            setJsonContent(json)
            setOriginalJsonContent(json)
            setEditingJobId(jobId)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Erro ao carregar JSON do arquivo')
            setJsonContent(JSON.stringify({ error: 'Erro ao carregar dados' }, null, 2))
            setOriginalJsonContent(JSON.stringify({ error: 'Erro ao carregar dados' }, null, 2))
            setEditingJobId(null)
        } finally {
            setLoadingJson(false)
        }
    }, [fetchFileJson])

    // Verificar se há mudanças
    const hasChanges = useCallback(() => {
        if (!showEditArea) return false
        return jsonContent !== originalJsonContent
    }, [showEditArea, jsonContent, originalJsonContent])

    // Salvar edição
    const handleSave = useCallback(async () => {
        if (!editingFile || !editingJobId) {
            setError('Job não encontrado para este arquivo')
            return
        }

        // Validar JSON
        let parsedJson: Record<string, unknown>
        try {
            parsedJson = JSON.parse(jsonContent)
        } catch (err) {
            setError('JSON inválido. Por favor, corrija o formato antes de salvar.')
            return
        }

        setSubmitting(true)
        setError(null)

        try {
            // Atualizar o job com o novo result_data
            await protectedFetch(`/api/job/${editingJobId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    result_data: parsedJson,
                }),
            } as RequestInit)

            // Atualizar o JSON original
            setOriginalJsonContent(jsonContent)

            // Fechar área de edição
            setShowEditArea(false)
            setEditingFile(null)
            setEditingJobId(null)
            setJsonContent('')
            setOriginalJsonContent('')

            // Recarregar lista de arquivos
            await loadItems()
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Erro ao salvar JSON do arquivo')
        } finally {
            setSubmitting(false)
        }
    }, [editingFile, editingJobId, jsonContent, loadItems])

    // Cancelar edição e limpar seleção
    const handleCancel = useCallback(() => {
        setShowEditArea(false)
        setEditingFile(null)
        setEditingJobId(null)
        setJsonContent('')
        setOriginalJsonContent('')
        setError(null)
        clearSelection()
    }, [clearSelection])

    // Polling do status do job
    const pollJobStatus = useCallback(async (jobId: number, fileIndex: number) => {
        try {
            const job = await protectedFetch<JobResponse>(`/api/job/${jobId}`)

            setPendingFiles((prev) => {
                const newPending = [...prev]
                if (newPending[fileIndex]) {
                    newPending[fileIndex] = {
                        ...newPending[fileIndex],
                        jobStatus: job.status,
                        error: job.error_message || undefined,
                    }
                }
                return newPending
            })

            // Se ainda está processando, continuar polling
            if (job.status === 'PENDING' || job.status === 'RUNNING') {
                const interval = setTimeout(() => pollJobStatus(jobId, fileIndex), 2000)
                pollingIntervals.current.set(jobId, interval)
            } else {
                // Limpar intervalo quando terminar
                const interval = pollingIntervals.current.get(jobId)
                if (interval) {
                    clearInterval(interval)
                    pollingIntervals.current.delete(jobId)
                }
            }
        } catch (err) {
            setPendingFiles((prev) => {
                const newPending = [...prev]
                if (newPending[fileIndex]) {
                    newPending[fileIndex] = {
                        ...newPending[fileIndex],
                        jobStatus: 'FAILED',
                        error: err instanceof Error ? err.message : 'Erro ao verificar status do job',
                    }
                }
                return newPending
            })

            // Limpar intervalo em caso de erro
            const interval = pollingIntervals.current.get(jobId)
            if (interval) {
                clearInterval(interval)
                pollingIntervals.current.delete(jobId)
            }
        }
    }, [])

    // Upload individual de arquivo
    const uploadSingleFile = useCallback(async (pendingFile: PendingFile, index: number) => {
        // Marcar como fazendo upload
        setPendingFiles((prev) => {
            const newPending = [...prev]
            if (newPending[index]) {
                newPending[index] = { ...newPending[index], uploading: true }
            }
            return newPending
        })

        try {
            // 1. Upload do arquivo
            // Validar que há hospital selecionado
            if (!filterHospitalId) {
                throw new Error('Selecione o hospital')
            }

            const formData = new FormData()
            formData.append('file', pendingFile.file)

            // Upload usa FormData - protectedFetch suporta FormData via options.body
            const uploadData = await protectedFetch<FileUploadResponse>(`/api/file/upload?hospital_id=${filterHospitalId}`, {
                method: 'POST',
                body: formData,
            })

            // Remover arquivo pendente após upload bem-sucedido
            setPendingFiles((prev) => {
                const newPending = [...prev]
                newPending.splice(index, 1)
                return newPending
            })
        } catch (err) {
            setPendingFiles((prev) => {
                const newPending = [...prev]
                if (newPending[index]) {
                    newPending[index] = {
                        ...newPending[index],
                        uploading: false,
                        error: err instanceof Error ? err.message : 'Erro desconhecido ao processar arquivo',
                    }
                }
                return newPending
            })
        }
    }, [filterHospitalId])

    // Função para adicionar arquivos à lista (usada tanto pelo input quanto pelo drag&drop)
    const addFilesToList = useCallback((files: File[]) => {
        if (files.length === 0) return

        setError(null)

        // Criar função para gerar chave única do arquivo
        const getFileKey = (file: File) => `${file.name}-${file.size}-${file.lastModified}`

        // Adicionar arquivos à lista de pendentes, filtrando duplicados
        setPendingFiles((prev) => {
            // Criar conjunto de chaves dos arquivos já pendentes
            const existingKeys = new Set(prev.map((pf) => getFileKey(pf.file)))

            // Filtrar arquivos que ainda não estão na lista
            const newFiles = files.filter((file) => !existingKeys.has(getFileKey(file)))

            if (newFiles.length === 0) {
                return prev // Retornar estado anterior se não houver novos arquivos
            }

            // Criar novos pendentes apenas dos arquivos novos
            const newPendingFiles: PendingFile[] = newFiles.map((file) => ({
                file,
                uploading: false,
            }))

            return [...prev, ...newPendingFiles]
        })
    }, [])

    // Seleção de arquivos para upload (via input)
    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = Array.from(e.target.files || [])
        addFilesToList(selected)

        // Limpar input
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }, [addFilesToList])

    // Handlers para drag & drop
    const [isDragging, setIsDragging] = useState(false)

    const handleDragEnter = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(true)
    }, [])

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
    }, [])

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)

        const files = Array.from(e.dataTransfer.files || [])
        if (files.length > 0) {
            addFilesToList(files)
        }
    }, [addFilesToList])

    // Abrir seletor de arquivos ao clicar no card
    const handleUploadCardClick = useCallback(() => {
        if (!filterHospitalId) {
            setUploadCardFlash(true)
            setHospitalFieldFlash(true)
            // Remover o flash após 1 segundo
            setTimeout(() => {
                setUploadCardFlash(false)
                setHospitalFieldFlash(false)
            }, 1000)
            return
        }
        setBottomBarMessage(null)
        fileInputRef.current?.click()
    }, [filterHospitalId])


    // Remover arquivo pendente
    const removePendingFile = useCallback((index: number) => {
        setPendingFiles((prev) => {
            const newPending = [...prev]
            const removed = newPending.splice(index, 1)[0]

            // Limpar polling se existir
            if (removed.jobId) {
                const interval = pollingIntervals.current.get(removed.jobId)
                if (interval) {
                    clearInterval(interval)
                    pollingIntervals.current.delete(removed.jobId)
                }
            }

            return newPending
        })
    }, [])

    // Processar automaticamente arquivos pendentes quando são adicionados
    useEffect(() => {
        if (processingRef.current) return

        // Função para gerar chave única do arquivo
        const getFileKey = (file: File) => `${file.name}-${file.size}-${file.lastModified}`

        // Buscar arquivos pendentes que ainda não foram processados
        const filesToProcess = pendingFiles.filter((pf) => {
            const key = getFileKey(pf.file)
            return !pf.fileId && !pf.uploading && !pf.error && !processedFilesRef.current.has(key)
        })

        if (filesToProcess.length === 0) return

        // Processar arquivos sequencialmente
        const processFiles = async () => {
            processingRef.current = true
            setUploading(true)
            setError(null)

            try {
                for (let i = 0; i < filesToProcess.length; i++) {
                    const pendingFile = filesToProcess[i]
                    const key = getFileKey(pendingFile.file)
                    // Marcar como processado antes de iniciar
                    processedFilesRef.current.add(key)

                    // Encontrar o índice real do arquivo na lista de pendingFiles
                    const realIndex = pendingFiles.findIndex((pf) => pf === pendingFile)
                    if (realIndex >= 0) {
                        await uploadSingleFile(pendingFile, realIndex)
                    }
                }

                // Recarregar lista de arquivos após upload de todos
                if (filesToProcess.length > 0) {
                    await loadItems()
                }
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Erro ao fazer upload dos arquivos. Tente novamente.'
                )
            } finally {
                setUploading(false)
                processingRef.current = false
            }
        }

        processFiles()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [pendingFiles.length]) // Executar apenas quando a quantidade de arquivos pendentes mudar

    // Polling para atualizar status de arquivos com jobs em andamento
    useEffect(() => {
        // Verificar se há arquivos com jobs em andamento
        const hasPendingOrRunningJobs = localFiles.some(
            (file) => file.job_status === 'PENDING' || file.job_status === 'RUNNING'
        )

        if (!hasPendingOrRunningJobs) {
            return // Não há jobs em andamento, não precisa fazer polling
        }

        // Função para atualizar status dos arquivos sem recarregar toda a lista
        const updateFileStatuses = async () => {
            try {
                // Buscar TODOS os jobs EXTRACT_DEMAND recentes (para pegar PENDING, RUNNING, COMPLETED e FAILED)
                // Buscamos apenas os mais recentes (limit=100) para não sobrecarregar
                const data = await protectedFetch<{ items: JobResponse[] }>('/api/job/list?job_type=EXTRACT_DEMAND&limit=100')
                const allJobs = data.items || []

                // Criar map de file_id -> job_status (usando o job mais recente para cada file_id)
                const fileIdToJobStatus = new Map<number, string>()
                for (const job of allJobs) {
                    if (job.input_data && job.input_data.file_id) {
                        const fileIdRaw = job.input_data.file_id
                        let fileId: number | null = null
                        if (typeof fileIdRaw === 'string') {
                            const parsed = parseInt(fileIdRaw, 10)
                            if (!isNaN(parsed)) fileId = parsed
                        } else if (typeof fileIdRaw === 'number') {
                            fileId = fileIdRaw
                        }
                        if (fileId !== null) {
                            // Só atualizar se ainda não tiver um status para este file_id
                            // (jobs estão ordenados por created_at desc, então o primeiro é o mais recente)
                            if (!fileIdToJobStatus.has(fileId)) {
                                fileIdToJobStatus.set(fileId, job.status)
                            }
                        }
                    }
                }

                // Atualizar apenas os arquivos que estão sendo rastreados ou têm mudança de status
                setLocalFiles((prevFiles) => {
                    return prevFiles.map((file) => {
                        const newStatus = fileIdToJobStatus.get(file.id)
                        // Atualizar se:
                        // 1. Há um novo status e é diferente do atual
                        // 2. O arquivo estava em processamento mas agora não tem mais status (raro, mas possível)
                        if (newStatus && file.job_status !== newStatus) {
                            return { ...file, job_status: newStatus }
                        }
                        // Se o arquivo estava em processamento mas não há mais job, manter o status atual
                        // (não limpar para evitar perder informação)
                        return file
                    })
                })
            } catch (err) {
                // Ignorar erros no polling - não queremos interromper a UI
                console.error('Erro ao atualizar status dos jobs:', err)
            }
        }

        // Polling a cada 2 segundos
        const interval = setInterval(updateFileStatuses, 2000)

        return () => {
            clearInterval(interval)
        }
    }, [localFiles])

    // Limpar polling ao desmontar
    useEffect(() => {
        return () => {
            pollingIntervals.current.forEach((interval) => clearInterval(interval))
            pollingIntervals.current.clear()
        }
    }, [])

    // Ler conteúdo dos arquivos selecionados
    const handleReadSelected = async () => {
        if (selectedFilesCount === 0) return

        setReading(true)
        setError(null)

        try {
            // Obter IDs para ação: null = todos (selectAllMode), array = IDs específicos
            const idsForAction = getSelectedFileIdsForAction()
            let fileIdsToRead: number[]

            if (idsForAction === null) {
                // Modo "todos": buscar todos os IDs que atendem aos filtros atuais
                const params = new URLSearchParams()
                params.set('limit', '10000')
                params.set('offset', '0')

                if (additionalListParams) {
                    Object.entries(additionalListParams).forEach(([key, value]) => {
                        if (value !== null && value !== undefined) {
                            params.set(key, String(value))
                        }
                    })
                }

                const response = await protectedFetch<{ items: FileResponse[]; total: number }>(
                    `/api/file/list?${params.toString()}`
                )
                fileIdsToRead = response.items.map((item) => item.id)
            } else {
                fileIdsToRead = idsForAction
            }

            if (fileIdsToRead.length === 0) {
                setError('Nenhum arquivo para ler')
                return
            }

            // Processar cada arquivo para leitura
            for (const fileId of fileIdsToRead) {
                try {
                    // Criar job de extração
                    await protectedFetch('/api/job/extract', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ file_id: fileId }),
                    })

                    // Job criado com sucesso - o worker processará em background
                } catch (err) {
                    // Se um arquivo falhar, continuar com os outros
                    console.error(`Erro ao processar arquivo ${fileId}:`, err)
                }
            }

            // Recarregar lista de arquivos para atualizar o status
            await loadItems()

            // Limpar seleção após iniciar leitura
            clearSelection()
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao iniciar leitura dos arquivos. Tente novamente.'
            )
        } finally {
            setReading(false)
        }
    }

    // handleDeleteSelected já vem do useEntityPage, não precisa reimplementar

    const { leftButtons: reportLeftButtons, reportError } = useReportButton({
        apiPath: '/api/file/report',
        params: additionalListParams ?? undefined,
        reportFilters,
    })

    // Botões do ActionBar usando hook reutilizável (com extensões para File)
    const actionBarButtons = useActionBarRightButtons({
        isEditing: false, // Não usado quando showEditArea é fornecido
        selectedCount: selectedFilesCount,
        hasChanges: hasChanges(),
        submitting,
        deleting,
        showEditArea, // Flag alternativa para File
        additionalStates: { reading },
        customActions:
            selectedFilesCount > 0
                ? [
                    {
                        label: 'Ler conteúdo',
                        onClick: handleReadSelected,
                        disabled: reading || submitting,
                        loading: reading,
                    },
                ]
                : [],
        onCancel: handleCancel,
        onDelete: handleDeleteSelected,
        onSave: handleSave,
    })

    // Props de erro do ActionBar usando função utilitária (ajustado para showEditArea)
    const actionBarErrorProps = getActionBarErrorProps(
        error,
        showEditArea, // File usa showEditArea em vez de isEditing
        selectedFilesCount
    )

    return (
        <div
            className="p-4 sm:p-6 lg:p-8 min-w-0"
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            <div className="mb-4 sm:mb-6">
                <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">Arquivos</h1>
                <p className="mt-1 text-sm text-gray-600">
                    Gerencie e visualize seus arquivos importados
                </p>
            </div>

            {/* Filtros ou Área de edição (nunca aparecem juntos) */}
            {!showEditArea ? (
                /* Filtro por período e hospital */
                <FilterPanel
                    validationErrors={
                        filterStartDate && filterEndDate && filterStartDate > filterEndDate ? (
                            <p className="mt-2 text-sm text-red-600">
                                Data inicial deve ser menor ou igual à data final
                            </p>
                        ) : undefined
                    }
                >
                    {/* Primeira linha: Hospital e Datas */}
                    <FormFieldGrid cols={1} smCols={3} gap={4}>
                        <FilterSelect
                            label={FILTER_HOSPITAL_LABEL}
                            value={filterHospitalId}
                            onChange={handleHospitalChange}
                            options={hospitalList.map((h) => ({ value: h.id, label: h.name }))}
                            loading={loadingHospitalList}
                            showFlash={hospitalFieldFlash}
                        />
                        <TenantDateTimePicker
                            label="Cadastrados desde"
                            value={filterStartDate}
                            onChange={handleStartDateChange}
                            id="filter_start_date"
                            name="filter_start_date"
                        />
                        <TenantDateTimePicker
                            label={FILTER_END_DATE_LABEL}
                            value={filterEndDate}
                            onChange={handleEndDateChange}
                            id="filter_end_date"
                            name="filter_end_date"
                        />
                    </FormFieldGrid>

                    {/* Segunda linha: Filtro de Status */}
                    <FilterButtons
                        title="Situação"
                        options={[
                            { value: null as JobStatus | null, label: 'Pronto para ser lido', color: 'text-gray-600' },
                            { value: 'PENDING' as JobStatus, label: 'Na fila para ser lido', color: 'text-yellow-600' },
                            { value: 'RUNNING' as JobStatus, label: 'Lendo o conteúdo', color: 'text-blue-600' },
                            { value: 'COMPLETED' as JobStatus, label: 'Conteúdo lido', color: 'text-green-600' },
                            { value: 'FAILED' as JobStatus, label: 'Não foi possível ler', color: 'text-red-600' },
                        ]}
                        selectedValues={statusFilters.selectedValues}
                        onToggle={statusFilters.toggleFilter}
                        onToggleAll={statusFilters.toggleAll}
                    />
                </FilterPanel>
            ) : (
                /* Área de edição */
                <EditForm
                    title="Arquivo"
                    editTitle="Editar arquivo"
                    isEditing={showEditArea}
                    noPadding
                >
                    {loadingJson ? (
                        <div className="flex justify-center items-center py-12">
                            <LoadingSpinner />
                        </div>
                    ) : (
                        <>
                            <FormField
                                label="JSON extraído"
                                helperText="Conteúdo JSON extraído do arquivo. Você pode editar este campo."
                            >
                                <JsonEditor
                                    id="json-content"
                                    value={jsonContent}
                                    on_change={(value) => {
                                        setJsonContent(value)
                                    }}
                                    is_disabled={submitting}
                                    height={400}
                                />
                            </FormField>
                        </>
                    )}
                </EditForm>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex justify-center items-center py-12">
                    <LoadingSpinner />
                </div>
            )}

            {/* Lista de arquivos */}
            {!loading && (
                <>
                    {/* Cards de arquivos */}
                    {/* Mensagem de erro (se houver) */}
                    {bottomBarMessage && (
                        <div className="mb-4 sm:mb-6">
                            <div className="text-sm text-red-600">
                                {bottomBarMessage}
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-4 sm:mb-6">
                        {/* Card de upload - sempre o primeiro */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.csv"
                            onChange={handleFileSelect}
                            className="hidden"
                            id="file-upload"
                        />
                        <CreateCard
                            label="Adicionar um ou mais arquivos"
                            subtitle="Clique ou arraste e solte"
                            onClick={handleUploadCardClick}
                            isDragging={isDragging}
                            showFlash={uploadCardFlash}
                            flashMessage="Selecione o hospital"
                            onDragEnter={handleDragEnter}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            customIcon={
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
                                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                                    />
                                </svg>
                            }
                        >
                            <div className="space-y-0.5">
                                <p className="text-xs text-slate-400 leading-tight">
                                    Documentos PDF
                                </p>
                                <p className="text-xs text-slate-400 leading-tight">
                                    Planilhas XLSX ou XLS
                                </p>
                                <p className="text-xs text-slate-400 leading-tight">
                                    Imagens JPG ou PNG
                                </p>
                                <p className="text-xs text-slate-400 leading-tight">
                                    Texto CSV
                                </p>
                            </div>
                        </CreateCard>

                        {/* Renderizar arquivos pendentes primeiro - filtrar aqueles que já estão em localFiles */}
                        {pendingFiles
                            .filter((pendingFile) => {
                                // Se o arquivo já tem fileId e está na lista de localFiles, não mostrar
                                if (pendingFile.fileId) {
                                    return !localFiles.some((f) => f.id === pendingFile.fileId)
                                }
                                // Verificar se já está na lista de localFiles comparando nome e tamanho
                                const fileName = pendingFile.file.name
                                const fileSize = pendingFile.file.size
                                const alreadyInFiles = localFiles.some(
                                    (f) => f.filename === fileName && f.file_size === fileSize
                                )
                                // Se já está em localFiles, não mostrar como pendente
                                return !alreadyInFiles
                            })
                            .map((pendingFile, filteredIndex) => {
                                // Usar índice original de pendingFiles para remover corretamente
                                const originalIndex = pendingFiles.findIndex((pf) => pf === pendingFile)
                                const fileTypeInfo = getFileTypeInfo(pendingFile.file.type || 'application/octet-stream')

                                return (
                                    <div
                                        key={`pending-${originalIndex}-${pendingFile.file.name}`}
                                        className="group rounded-xl border bg-white p-4 min-w-0 transition-all duration-200 border-blue-200"
                                    >
                                        {/* 1. Topo - Identidade do arquivo */}
                                        <div className="mb-3 flex items-start justify-between gap-2 min-w-0">
                                            <div className="flex items-center gap-2 min-w-0 flex-1">
                                                <div className={`shrink-0 ${fileTypeInfo.colorClass}`}>
                                                    {fileTypeInfo.icon}
                                                </div>
                                                <h3
                                                    className="text-sm font-semibold truncate min-w-0 text-gray-900"
                                                    title={pendingFile.file.name}
                                                >
                                                    {pendingFile.file.name}
                                                </h3>
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    removePendingFile(originalIndex)
                                                }}
                                                className="shrink-0 p-1.5 rounded-md transition-all duration-200 text-gray-400"
                                                title="Remover arquivo"
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
                                                        d="M6 18L18 6M6 6l12 12"
                                                    />
                                                </svg>
                                            </button>
                                        </div>

                                        {/* 2. Corpo - Preview */}
                                        <div className="mb-3">
                                            {isImage(pendingFile.file.type || '') ? (
                                                <PendingFileImageThumbnail file={pendingFile.file} />
                                            ) : (
                                                // Para outros tipos, mostrar ícone
                                                <div className="h-40 sm:h-48 bg-slate-50 rounded-lg flex items-center justify-center">
                                                    <div className={`flex flex-col items-center justify-center ${fileTypeInfo.colorClass}`}>
                                                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                                                            {fileTypeInfo.icon}
                                                        </div>
                                                        <span className="text-xs font-medium">
                                                            {pendingFile.file.type?.split('/')[1]?.toUpperCase() || 'ARQUIVO'}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        {/* 3. Rodapé - Status */}
                                        <div className="flex items-center gap-2 text-sm">
                                            <span className="truncate text-slate-500">{formatFileSize(pendingFile.file.size)}</span>
                                            {pendingFile.uploading && (
                                                <>
                                                    <LoadingSpinner />
                                                </>
                                            )}
                                            {pendingFile.error && (
                                                <>
                                                    <span className="shrink-0 text-slate-500">•</span>
                                                    <span className="truncate text-red-600">Erro</span>
                                                </>
                                            )}
                                        </div>
                                        {pendingFile.error && (
                                            <p className="mt-2 text-xs text-red-600 truncate" title={pendingFile.error}>
                                                {pendingFile.error}
                                            </p>
                                        )}
                                    </div>
                                )
                            })}

                        {/* Renderizar arquivos existentes */}
                        {paginatedFiles.map((file) => {
                            const fileTypeInfo = getFileTypeInfo(file.content_type)
                            const isSelected = selectedFiles.has(file.id)
                            const jobStatusClasses = getJobStatusCardClasses(file.job_status)

                            // Calcular cor do hospital (com fallback para branco se não houver cor)
                            const hospitalColor = file.hospital_color || '#FFFFFF'
                            const hospitalBorderColor = file.hospital_color || '#E2E8F0' // slate-200 como fallback

                            return (
                                <EntityCard
                                    key={file.id}
                                    id={file.id}
                                    isSelected={isSelected}
                                    className="flex flex-col"
                                    footer={
                                        <CardFooter
                                            isSelected={isSelected}
                                            date={file.created_at}
                                            settings={settings}
                                            secondaryText={formatFileSize(file.file_size)}
                                            onToggleSelection={(e) => {
                                                e.stopPropagation()
                                                toggleFileSelection(file.id)
                                            }}
                                            onEdit={() => handleEditClick(file)}
                                            disabled={deleting || reading}
                                            deleteTitle={isSelected ? 'Desmarcar' : 'Marcar'}
                                            editTitle="Editar arquivo"
                                        />
                                    }
                                >
                                    {/* 1. Container padronizado - Topo + Preview */}
                                    <div className="mb-3">
                                        <div
                                            className="h-40 sm:h-48 rounded-lg flex flex-col border border-blue-200 overflow-hidden"
                                            style={{ backgroundColor: hospitalColor || '#f1f5f9' }}
                                        >
                                            {/* Topo - Identidade do arquivo */}
                                            <div className="flex flex-col gap-1 min-w-0 px-4 pt-4 flex-shrink-0">
                                                <span className={`text-xs truncate ${getCardSecondaryTextClasses(isSelected)}`}>
                                                    {file.hospital_name}
                                                </span>
                                                <div className="flex items-start gap-2 min-w-0">
                                                    <div className={`shrink-0 ${fileTypeInfo.colorClass}`}>
                                                        {fileTypeInfo.icon}
                                                    </div>
                                                    <h3
                                                        className={`text-sm font-semibold truncate min-w-0 flex-1 ${getCardTextClasses(isSelected)}`}
                                                        title={file.filename}
                                                    >
                                                        {file.filename}
                                                    </h3>
                                                </div>
                                            </div>

                                            {/* Preview - Thumbnail */}
                                            <div className="flex-1 min-h-0 relative">
                                                <FileThumbnail
                                                    file={file}
                                                    onClick={() => toggleFileSelection(file.id)}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* 3. Compartimento para status - ícone e texto */}
                                    <div
                                        className="mb-3 h-14 flex items-center justify-start rounded-lg py-2 bg-gray-50 px-4 gap-3 border-b-4 cursor-pointer"
                                        style={{ borderBottomColor: getStatusBackgroundColor(file.job_status) }}
                                        onClick={() => toggleFileSelection(file.id)}
                                        title={isSelected ? 'Desmarcar' : 'Marcar'}
                                    >
                                        {getStatusIcon(file.job_status)}
                                        <span className="text-base font-normal text-gray-900 flex items-center gap-2">
                                            {getJobStatusText(file.job_status)}
                                            {(file.job_status === 'RUNNING' || file.job_status === 'PENDING') && <LoadingSpinner />}
                                        </span>
                                    </div>
                                </EntityCard>
                            )
                        })}
                    </div>
                </>
            )}

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <ActionBarSpacer />

            {/* Barra inferior fixa com ações */}
            <ActionBar
                selection={{
                    selectedCount: selectedFilesCount,
                    totalCount: filteredFiles.length,
                    grandTotal: displayTotal,
                    selectAllMode: selectAllFilesMode,
                    onToggleAll: () => toggleAllFiles(filteredFiles.map((f) => f.id)),
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
                error={reportError ?? actionBarErrorProps.error}
                message={actionBarErrorProps.message}
                messageType={actionBarErrorProps.messageType}
                leftButtons={reportLeftButtons}
                buttons={actionBarButtons}
            />
        </div>
    )
}