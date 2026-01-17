'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import { TenantDatePicker } from '@/components/TenantDatePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { formatDateTime, localDateToUtcEndExclusive, localDateToUtcStart } from '@/lib/tenantFormat'
import { useCallback, useEffect, useRef, useState } from 'react'

interface FileResponse {
    id: number
    filename: string
    content_type: string
    file_size: number
    created_at: string
    can_delete: boolean
    job_status: string | null
}

interface FileListResponse {
    items: FileResponse[]
    total: number
}

type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

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
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
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
 */
function FileThumbnail({ file, onClick }: { file: FileResponse; onClick?: () => void }) {
    const [imageUrl, setImageUrl] = useState<string | null>(null)
    const [loadingImage, setLoadingImage] = useState(false)

    // Carregar URL da imagem se for imagem
    useEffect(() => {
        if (isImage(file.content_type) && !imageUrl && !loadingImage) {
            setLoadingImage(true)
            // Usar proxy diretamente para imagens
            const proxyUrl = `/api/file/${file.id}/proxy`
            setImageUrl(proxyUrl)
            setLoadingImage(false)
        }
    }, [file.id, file.content_type, imageUrl, loadingImage])

    const fileTypeInfo = getFileTypeInfo(file.content_type)

    return (
        <div className="relative w-full h-40 sm:h-48 bg-slate-50 rounded-lg overflow-hidden group">
            <button
                onClick={onClick}
                className="w-full h-full flex items-center justify-center cursor-pointer transition-all duration-200"
                title="Clique para marcar para leitura"
            >
                {isImage(file.content_type) && imageUrl ? (
                    <img
                        src={imageUrl}
                        alt={file.filename}
                        className="w-full h-full object-cover rounded-lg"
                        onError={() => {
                            setImageUrl(null)
                        }}
                    />
                ) : (
                    <div className={`flex flex-col items-center justify-center ${fileTypeInfo.colorClass}`}>
                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                            {file.content_type === 'application/pdf' ? (
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
                                        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                                    />
                                </svg>
                            ) : (
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
                                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                    />
                                </svg>
                            )}
                        </div>
                        <span className="text-xs font-medium">
                            {file.content_type === 'application/pdf'
                                ? 'PDF'
                                : file.content_type.split('/')[1]?.toUpperCase() || 'DOCUMENTO'}
                        </span>
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
    const [files, setFiles] = useState<FileResponse[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [selectedFiles, setSelectedFiles] = useState<Set<number>>(new Set())
    const [selectedFilesForReading, setSelectedFilesForReading] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [reading, setReading] = useState(false)
    const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
    const [uploading, setUploading] = useState(false)
    const pollingIntervals = useRef<Map<number, NodeJS.Timeout>>(new Map())
    const [refreshKey, setRefreshKey] = useState(0)

    // Filtros de período usando TenantDatePicker (Date objects)
    // Inicializar com data de hoje
    const [startDate, setStartDate] = useState<Date | null>(() => {
        const today = new Date()
        return new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0, 0)
    })

    const [endDate, setEndDate] = useState<Date | null>(() => {
        const today = new Date()
        return new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0, 0)
    })

    // Paginação
    const [limit] = useState(19) // Limite padrão
    const [offset, setOffset] = useState(0)

    // Carregar arquivos
    useEffect(() => {
        async function loadFiles() {
            if (!settings) {
                // Aguardar settings carregar
                return
            }

            setLoading(true)
            setError(null)

            try {
                // Validar intervalo (se ambas as datas estão selecionadas)
                if (startDate && endDate && startDate > endDate) {
                    setError('Data inicial deve ser menor ou igual à data final')
                    setLoading(false)
                    return
                }

                // Converter Date objects para UTC strings (ISO 8601) antes de enviar à API
                const startAt = startDate ? localDateToUtcStart(startDate, settings) : ''
                const endAt = endDate ? localDateToUtcEndExclusive(endDate, settings) : ''

                // Construir URL com query params
                const url = new URL('/api/file/list', window.location.origin)
                if (startAt) url.searchParams.set('start_at', startAt)
                if (endAt) url.searchParams.set('end_at', endAt)
                url.searchParams.set('limit', String(limit))
                url.searchParams.set('offset', String(offset))

                try {
                    const response = await fetch(url.toString(), {
                        credentials: 'include',
                    })

                    if (response.ok) {
                        const data: FileListResponse = await response.json()
                        setFiles(data.items)
                        setTotal(data.total)
                        setLoading(false)
                        return
                    }
                    // Se não ok, não fazer nada aqui - deixar para o catch externo
                } catch (err) {
                    // Se a API falhar, ignorar (não setar erro aqui)
                    // Erro será setado no catch externo se necessário
                }

                // Se chegou aqui, não foi possível carregar os dados
                setError('Não foi possível carregar os arquivos. Por favor, tente novamente.')
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message || 'Erro ao carregar arquivos')
                } else {
                    setError('Erro desconhecido ao carregar arquivos')
                }
            } finally {
                setLoading(false)
            }
        }

        loadFiles()
    }, [startDate, endDate, settings, limit, offset, refreshKey])

    // Calcular página atual e total de páginas
    const currentPage = Math.floor(offset / limit) + 1
    const totalPages = Math.ceil(total / limit)

    // Navegar para página anterior
    const goToPreviousPage = () => {
        if (offset > 0) {
            setOffset(Math.max(0, offset - limit))
        }
    }

    // Navegar para próxima página
    const goToNextPage = () => {
        if (offset + limit < total) {
            setOffset(offset + limit)
        }
    }

    // Handlers para mudança de data no TenantDatePicker
    const handleStartDateChange = (date: Date | null) => {
        setStartDate(date)
        setOffset(0) // Resetar paginação ao mudar filtro
    }

    const handleEndDateChange = (date: Date | null) => {
        setEndDate(date)
        setOffset(0) // Resetar paginação ao mudar filtro
    }

    // Toggle seleção de arquivo para exclusão
    const toggleFileSelection = (fileId: number) => {
        setSelectedFiles((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(fileId)) {
                newSet.delete(fileId)
            } else {
                newSet.add(fileId)
            }
            return newSet
        })
        // Ao selecionar para exclusão, remover da seleção de leitura
        setSelectedFilesForReading((prev) => {
            const newSet = new Set(prev)
            newSet.delete(fileId)
            return newSet
        })
    }

    // Toggle seleção de arquivo para leitura
    const toggleFileSelectionForReading = (fileId: number) => {
        setSelectedFilesForReading((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(fileId)) {
                newSet.delete(fileId)
            } else {
                newSet.add(fileId)
            }
            return newSet
        })
        // Ao selecionar para leitura, remover da seleção de exclusão
        setSelectedFiles((prev) => {
            const newSet = new Set(prev)
            newSet.delete(fileId)
            return newSet
        })
    }

    // Polling do status do job
    const pollJobStatus = useCallback(async (jobId: number, fileIndex: number) => {
        try {
            const response = await fetch(`/api/job/${jobId}`, {
                credentials: 'include',
            })

            if (!response.ok) {
                throw new Error(`Erro ao verificar status do job: ${response.status}`)
            }

            const job: JobResponse = await response.json()

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
            const formData = new FormData()
            formData.append('file', pendingFile.file)

            const uploadResponse = await fetch('/api/file/upload', {
                method: 'POST',
                body: formData,
                credentials: 'include',
            })

            if (!uploadResponse.ok) {
                if (uploadResponse.status === 401) {
                    throw new Error('Sessão expirada. Por favor, faça login novamente.')
                }
                const errorData = await uploadResponse.json().catch(() => ({}))
                throw new Error(errorData.detail || `Erro ao fazer upload: ${uploadResponse.status}`)
            }

            const uploadData: FileUploadResponse = await uploadResponse.json()

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
    }, [])

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
        fileInputRef.current?.click()
    }, [])


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
                    setRefreshKey((prev) => prev + 1)
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
        const hasPendingOrRunningJobs = files.some(
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
                const response = await fetch('/api/job/list?job_type=EXTRACT_DEMAND&limit=100', {
                    credentials: 'include',
                })

                if (response.ok) {
                    const data = await response.json()
                    const allJobs = data.items || []

                    // Criar map de file_id -> job_status (usando o job mais recente para cada file_id)
                    const fileIdToJobStatus = new Map<number, string>()
                    for (const job of allJobs) {
                        if (job.input_data && job.input_data.file_id) {
                            const fileId = typeof job.input_data.file_id === 'string'
                                ? parseInt(job.input_data.file_id, 10)
                                : job.input_data.file_id
                            if (!isNaN(fileId)) {
                                // Só atualizar se ainda não tiver um status para este file_id
                                // (jobs estão ordenados por created_at desc, então o primeiro é o mais recente)
                                if (!fileIdToJobStatus.has(fileId)) {
                                    fileIdToJobStatus.set(fileId, job.status)
                                }
                            }
                        }
                    }

                    // Atualizar apenas os arquivos que estão sendo rastreados ou têm mudança de status
                    setFiles((prevFiles) => {
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
                }
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
    }, [files])

    // Limpar polling ao desmontar
    useEffect(() => {
        return () => {
            pollingIntervals.current.forEach((interval) => clearInterval(interval))
            pollingIntervals.current.clear()
        }
    }, [])

    // Ler conteúdo dos arquivos selecionados
    const handleReadSelected = async () => {
        if (selectedFilesForReading.size === 0) return

        setReading(true)
        setError(null)

        try {
            // Processar cada arquivo selecionado para leitura
            const fileIds = Array.from(selectedFilesForReading)

            for (const fileId of fileIds) {
                try {
                    // Criar job de extração
                    const jobResponse = await fetch('/api/job/extract', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ file_id: fileId }),
                        credentials: 'include',
                    })

                    if (!jobResponse.ok) {
                        if (jobResponse.status === 401) {
                            throw new Error('Sessão expirada. Por favor, faça login novamente.')
                        }
                        const errorData = await jobResponse.json().catch(() => ({}))
                        throw new Error(errorData.detail || `Erro ao criar job: ${jobResponse.status}`)
                    }

                    // Job criado com sucesso - o worker processará em background
                } catch (err) {
                    // Se um arquivo falhar, continuar com os outros
                    console.error(`Erro ao processar arquivo ${fileId}:`, err)
                }
            }

            // Recarregar lista de arquivos para atualizar o status
            setRefreshKey((prev) => prev + 1)

            // Limpar seleção após iniciar leitura
            setSelectedFilesForReading(new Set())
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

    // Deletar arquivos selecionados
    const handleDeleteSelected = async () => {
        if (selectedFiles.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            // Deletar todos os arquivos selecionados em paralelo
            const deletePromises = Array.from(selectedFiles).map(async (fileId) => {
                const response = await fetch(`/api/file/${fileId}`, {
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

                return fileId
            })

            await Promise.all(deletePromises)

            // Remover arquivos deletados da lista
            setFiles(files.filter((file) => !selectedFiles.has(file.id)))
            setTotal(total - selectedFiles.size)
            setSelectedFiles(new Set())
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao deletar arquivos. Tente novamente.'
            )
        } finally {
            setDeleting(false)
        }
    }

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

            {/* Filtro por período */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6 mb-4 sm:mb-6">
                <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 flex-1">
                        <TenantDatePicker
                            label="Cadastrados deste"
                            value={startDate}
                            onChange={handleStartDateChange}
                            id="start_at"
                            name="start_at"
                        />
                        <TenantDatePicker
                            label="Cadastrados até"
                            value={endDate}
                            onChange={handleEndDateChange}
                            id="end_at"
                            name="end_at"
                        />
                    </div>
                </div>
                {startDate && endDate && startDate > endDate && (
                    <p className="mt-2 text-sm text-red-600">
                        Data inicial deve ser menor ou igual à data final
                    </p>
                )}
            </div>


            {/* Mensagem de erro */}
            {error && (
                <div className="mb-4 sm:mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800">{error}</p>
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                </div>
            )}

            {/* Lista de arquivos */}
            {!loading && !error && (
                <>
                    {/* Cards de arquivos */}
                    {files.length === 0 && pendingFiles.length === 0 ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-8 sm:p-12 text-center">
                            <p className="text-gray-600">Nenhum arquivo encontrado no período selecionado.</p>
                        </div>
                    ) : (
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
                            <div
                                onClick={handleUploadCardClick}
                                onDragEnter={handleDragEnter}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                className={`group rounded-xl border-2 border-dashed bg-white p-4 min-w-0 cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[200px] ${isDragging
                                    ? 'border-blue-500 bg-blue-50'
                                    : 'border-slate-300'
                                    }`}
                            >
                                <div className="flex flex-col items-center justify-center text-center px-2">
                                    <svg
                                        className={`w-12 h-12 mb-3 ${isDragging ? 'text-blue-600' : 'text-slate-400'}`}
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
                                    <p className={`text-sm font-medium mb-1 ${isDragging ? 'text-blue-600' : 'text-slate-700'}`}>
                                        {isDragging ? 'Solte os arquivos aqui' : 'Adicionar um ou mais arquivos'}
                                    </p>
                                    <p className="text-xs text-slate-500 mb-2">
                                        Clique ou arraste e solte
                                    </p>
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
                            </div>

                            {/* Renderizar arquivos pendentes primeiro - filtrar aqueles que já estão em files */}
                            {pendingFiles
                                .filter((pendingFile) => {
                                    // Se o arquivo já tem fileId e está na lista de files, não mostrar
                                    if (pendingFile.fileId) {
                                        return !files.some((f) => f.id === pendingFile.fileId)
                                    }
                                    // Verificar se já está na lista de files comparando nome e tamanho
                                    const fileName = pendingFile.file.name
                                    const fileSize = pendingFile.file.size
                                    const alreadyInFiles = files.some(
                                        (f) => f.filename === fileName && f.file_size === fileSize
                                    )
                                    // Se já está em files, não mostrar como pendente
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
                                                        <span className="shrink-0 text-slate-500">•</span>
                                                        <span className="truncate text-slate-400">Enviando...</span>
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
                            {files.map((file) => {
                                const fileTypeInfo = getFileTypeInfo(file.content_type)
                                const isSelected = selectedFiles.has(file.id)
                                return (
                                    <div
                                        key={file.id}
                                        className={`group rounded-xl border bg-white p-4 min-w-0 transition-all duration-200 ${isSelected
                                            ? 'border-red-300 ring-2 ring-red-200 bg-red-50'
                                            : selectedFilesForReading.has(file.id)
                                                ? 'border-blue-300 ring-2 ring-blue-200 bg-blue-50'
                                                : 'border-slate-200'
                                            }`}
                                    >
                                        {/* 1. Topo - Identidade do arquivo */}
                                        <div className="mb-3 flex items-start gap-2 min-w-0">
                                            <div className={`shrink-0 ${fileTypeInfo.colorClass}`}>
                                                {fileTypeInfo.icon}
                                            </div>
                                            <h3
                                                className={`text-sm font-semibold truncate min-w-0 flex-1 ${isSelected ? 'text-red-900' : selectedFilesForReading.has(file.id) ? 'text-blue-900' : 'text-gray-900'
                                                    }`}
                                                title={file.filename}
                                            >
                                                {file.filename}
                                            </h3>
                                        </div>

                                        {/* 2. Corpo - Preview */}
                                        <div className="mb-3">
                                            <FileThumbnail
                                                file={file}
                                                onClick={() => toggleFileSelectionForReading(file.id)}
                                            />
                                        </div>

                                        {/* 3. Rodapé - Metadados à esquerda, ações à direita */}
                                        <div className="flex items-center justify-between gap-2">
                                            {/* Metadados à esquerda */}
                                            <div className="flex flex-col min-w-0 flex-1">
                                                <span className="text-xs text-slate-400 truncate mb-0.5">
                                                    {file.job_status === 'PENDING' ? 'Na fila para ser lido' :
                                                        file.job_status === 'RUNNING' ? 'Lendo o conteúdo do arquivo' :
                                                            file.job_status === 'COMPLETED' ? 'Conteúdo lido' :
                                                                file.job_status === 'FAILED' ? 'Não foi possível ler o conteúdo' :
                                                                    'Pronto para ser lido'}
                                                </span>
                                                <span className="text-sm text-slate-500 truncate">
                                                    {settings
                                                        ? formatDateTime(file.created_at, settings)
                                                        : new Date(file.created_at).toLocaleString()}
                                                </span>
                                                <span className="text-xs text-slate-400 truncate">{formatFileSize(file.file_size)}</span>
                                            </div>
                                            {/* Ações à direita */}
                                            <div className="flex items-center gap-1 shrink-0">
                                                {/* Ícone para exclusão */}
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        toggleFileSelection(file.id)
                                                    }}
                                                    disabled={deleting}
                                                    className={`shrink-0 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${isSelected
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
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* Paginação */}
                    {total > limit && (
                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-0 bg-white rounded-lg border border-gray-200 px-4 sm:px-6 py-4">
                            <div className="text-sm text-gray-700 text-center sm:text-left">
                                Página {currentPage} de {totalPages} ({total} arquivos)
                            </div>
                            <div className="flex gap-2 justify-center sm:justify-end">
                                <button
                                    onClick={goToPreviousPage}
                                    disabled={offset === 0}
                                    className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Anterior
                                </button>
                                <button
                                    onClick={goToNextPage}
                                    disabled={offset + limit >= total}
                                    className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Próxima
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <BottomActionBarSpacer />

            {/* Barra inferior fixa com ações */}
            <BottomActionBar
                leftContent={
                    <div className="text-sm text-gray-600">
                        Total de arquivos: <span className="font-medium">{total}</span>
                        {selectedFilesForReading.size > 0 && (
                            <span className="ml-2 sm:ml-4 text-blue-600">
                                {selectedFilesForReading.size} marcado{selectedFilesForReading.size > 1 ? 's' : ''} para leitura
                            </span>
                        )}
                        {selectedFiles.size > 0 && (
                            <span className="ml-2 sm:ml-4 text-red-600">
                                {selectedFiles.size} marcado{selectedFiles.size > 1 ? 's' : ''} para exclusão
                            </span>
                        )}
                    </div>
                }
                buttons={(() => {
                    const buttons = []
                    // Adicionar botão "Excluir" se houver arquivos marcados para exclusão
                    if (selectedFiles.size > 0) {
                        buttons.push({
                            label: 'Excluir',
                            onClick: handleDeleteSelected,
                            variant: 'primary' as const,
                            disabled: deleting,
                            loading: deleting,
                        })
                    }
                    // Adicionar botão "Ler conteúdo" se houver arquivos marcados para leitura
                    if (selectedFilesForReading.size > 0) {
                        buttons.push({
                            label: 'Ler conteúdo',
                            onClick: handleReadSelected,
                            variant: 'primary' as const,
                            disabled: reading,
                            loading: reading,
                        })
                    }
                    return buttons
                })()}
            />
        </div>
    )
}