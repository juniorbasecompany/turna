'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import { TenantDatePicker } from '@/components/TenantDatePicker'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { formatDateTime, localDateToUtcEndExclusive, localDateToUtcStart } from '@/lib/tenantFormat'
import { useEffect, useState } from 'react'

interface FileResponse {
    id: number
    filename: string
    content_type: string
    file_size: number
    created_at: string
    can_delete: boolean
}

interface FileListResponse {
    items: FileResponse[]
    total: number
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
 * Componente de thumbnail do arquivo (preview no corpo do card)
 */
function FileThumbnail({ file }: { file: FileResponse }) {
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
        <button
            onClick={() => handleFileDownload(file.id, file.filename)}
            className="w-full h-40 sm:h-48 bg-slate-50 rounded-lg flex items-center justify-center overflow-hidden cursor-pointer group transition-all duration-200 hover:bg-slate-100"
            title="Clique para baixar o arquivo"
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
    )
}

export default function FilesPage() {
    const { settings } = useTenantSettings()
    const [files, setFiles] = useState<FileResponse[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [selectedFiles, setSelectedFiles] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)

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
    const [limit] = useState(21) // Limite padrão
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
    }, [startDate, endDate, settings, limit, offset])

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

    // Toggle seleção de arquivo
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
        <div className="p-4 sm:p-6 lg:p-8 min-w-0">
            <div className="mb-4 sm:mb-6">
                <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">Arquivos</h1>
                <p className="mt-1 text-sm text-gray-600">
                    Gerencie e visualize seus arquivos importados
                </p>
            </div>

            {/* Filtro por período */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6 mb-4 sm:mb-6">
                <h2 className="text-base sm:text-lg font-medium text-gray-900 mb-3 sm:mb-4">Filtro por Período</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <TenantDatePicker
                        label="Data de Início"
                        value={startDate}
                        onChange={handleStartDateChange}
                        id="start_at"
                        name="start_at"
                    />
                    <TenantDatePicker
                        label="Data de Fim"
                        value={endDate}
                        onChange={handleEndDateChange}
                        id="end_at"
                        name="end_at"
                    />
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
                    {/* Barra de informações */}
                    <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div className="text-sm text-gray-600">
                            Total de arquivos: <span className="font-medium">{total}</span>
                            {selectedFiles.size > 0 && (
                                <span className="ml-2 sm:ml-4 text-red-600">
                                    {selectedFiles.size} marcado{selectedFiles.size > 1 ? 's' : ''} para exclusão
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Cards de arquivos */}
                    {files.length === 0 ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-8 sm:p-12 text-center">
                            <p className="text-gray-600">Nenhum arquivo encontrado no período selecionado.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-4 sm:mb-6">
                            {files.map((file) => {
                                const fileTypeInfo = getFileTypeInfo(file.content_type)
                                const isSelected = selectedFiles.has(file.id)
                                return (
                                    <div
                                        key={file.id}
                                        className={`group rounded-xl border bg-white p-4 min-w-0 cursor-pointer transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 ${isSelected
                                            ? 'border-red-300 ring-2 ring-red-200 bg-red-50'
                                            : 'border-slate-200 hover:border-slate-300'
                                            }`}
                                    >
                                        {/* 1. Topo - Identidade do arquivo */}
                                        <div className="mb-3 flex items-start justify-between gap-2 min-w-0">
                                            <div className="flex items-center gap-2 min-w-0 flex-1">
                                                <div className={`shrink-0 ${fileTypeInfo.colorClass}`}>
                                                    {fileTypeInfo.icon}
                                                </div>
                                                <h3
                                                    className={`text-sm font-semibold truncate min-w-0 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                        }`}
                                                    title={file.filename}
                                                >
                                                    {file.filename}
                                                </h3>
                                            </div>
                                            {file.can_delete && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        toggleFileSelection(file.id)
                                                    }}
                                                    disabled={deleting}
                                                    className={`shrink-0 p-1.5 rounded-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed opacity-0 group-hover:opacity-100 ${isSelected
                                                        ? 'text-red-700 bg-red-100 hover:bg-red-200 opacity-100'
                                                        : 'text-gray-400 hover:bg-gray-100'
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
                                            )}
                                        </div>

                                        {/* 2. Corpo - Preview */}
                                        <div className="mb-3">
                                            <FileThumbnail file={file} />
                                        </div>

                                        {/* 3. Rodapé - Metadados */}
                                        <div className="flex items-center justify-between gap-2 text-sm text-slate-500">
                                            <span className="truncate">{formatFileSize(file.file_size)}</span>
                                            <span className="shrink-0">•</span>
                                            <span className="truncate">
                                                {settings
                                                    ? formatDateTime(file.created_at, settings)
                                                    : new Date(file.created_at).toLocaleString()}
                                            </span>
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
                                    className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Anterior
                                </button>
                                <button
                                    onClick={goToNextPage}
                                    disabled={offset + limit >= total}
                                    className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
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
                buttons={
                    selectedFiles.size > 0
                        ? [
                            {
                                label: 'Salvar',
                                onClick: handleDeleteSelected,
                                variant: 'primary',
                                disabled: deleting,
                                loading: deleting,
                            },
                        ]
                        : []
                }
            />
        </div>
    )
}