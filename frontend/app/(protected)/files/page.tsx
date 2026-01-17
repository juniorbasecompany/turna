'use client'

import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
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
 * Formata data ISO 8601 para formato brasileiro (ex: "17/01/2026 14:30")
 * Converte de UTC para timezone local do navegador
 */
function formatDate(isoString: string): string {
    const date = new Date(isoString)
    const day = String(date.getDate()).padStart(2, '0')
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const year = date.getFullYear()
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    return `${day}/${month}/${year} ${hours}:${minutes}`
}

/**
 * Obtém início do dia atual em UTC (00:00:00)
 */
function getStartOfTodayUTC(): string {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()
    const day = now.getDate()
    const startOfDay = new Date(year, month, day, 0, 0, 0, 0)
    // Retorna em ISO 8601 com timezone (UTC)
    return startOfDay.toISOString()
}

/**
 * Obtém fim do dia atual em UTC (23:59:59.999)
 */
function getEndOfTodayUTC(): string {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()
    const day = now.getDate()
    const endOfDay = new Date(year, month, day, 23, 59, 59, 999)
    // Retorna em ISO 8601 com timezone (UTC)
    return endOfDay.toISOString()
}

export default function FilesPage() {
    const [files, setFiles] = useState<FileResponse[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [selectedFiles, setSelectedFiles] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)

    // Filtros de período (padrão: dia atual)
    const [startAt, setStartAt] = useState<string>(() => getStartOfTodayUTC())
    const [endAt, setEndAt] = useState<string>(() => getEndOfTodayUTC())

    // Paginação
    const [limit] = useState(21) // Limite padrão
    const [offset, setOffset] = useState(0)

    // Carregar arquivos
    useEffect(() => {
        async function loadFiles() {
            setLoading(true)
            setError(null)

            try {
                // Validar intervalo
                if (startAt && endAt && new Date(startAt) > new Date(endAt)) {
                    setError('Data inicial deve ser menor ou igual à data final')
                    setLoading(false)
                    return
                }

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
    }, [startAt, endAt, limit, offset])

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

    // Handler para mudança de filtro de data
    const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.value) {
            const date = new Date(e.target.value)
            date.setHours(0, 0, 0, 0)
            setStartAt(date.toISOString())
        } else {
            setStartAt('')
        }
        setOffset(0) // Resetar paginação ao mudar filtro
    }

    const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.value) {
            const date = new Date(e.target.value)
            date.setHours(23, 59, 59, 999)
            setEndAt(date.toISOString())
        } else {
            setEndAt('')
        }
        setOffset(0) // Resetar paginação ao mudar filtro
    }

    // Converter ISO para formato de input date (YYYY-MM-DD)
    const formatDateForInput = (isoString: string): string => {
        const date = new Date(isoString)
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
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
        <div className="p-8">
            <div className="mb-6">
                <h1 className="text-2xl font-semibold text-gray-900">Arquivos</h1>
                <p className="mt-1 text-sm text-gray-600">
                    Gerencie e visualize seus arquivos importados
                </p>
            </div>

            {/* Filtro por período */}
            <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Filtro por Período</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="start_at" className="block text-sm font-medium text-gray-700 mb-2">
                            Data de Início
                        </label>
                        <input
                            type="date"
                            id="start_at"
                            value={startAt ? formatDateForInput(startAt) : ''}
                            onChange={handleStartDateChange}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label htmlFor="end_at" className="block text-sm font-medium text-gray-700 mb-2">
                            Data de Fim
                        </label>
                        <input
                            type="date"
                            id="end_at"
                            value={endAt ? formatDateForInput(endAt) : ''}
                            onChange={handleEndDateChange}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                </div>
                {startAt && endAt && new Date(startAt) > new Date(endAt) && (
                    <p className="mt-2 text-sm text-red-600">
                        Data inicial deve ser menor ou igual à data final
                    </p>
                )}
            </div>

            {/* Mensagem de erro */}
            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
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
                    <div className="mb-4 flex items-center justify-between">
                        <div className="text-sm text-gray-600">
                            Total de arquivos: <span className="font-medium">{total}</span>
                            {selectedFiles.size > 0 && (
                                <span className="ml-4 text-red-600">
                                    {selectedFiles.size} marcado{selectedFiles.size > 1 ? 's' : ''} para exclusão
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Cards de arquivos */}
                    {files.length === 0 ? (
                        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                            <p className="text-gray-600">Nenhum arquivo encontrado no período selecionado.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                            {files.map((file) => (
                                <div
                                    key={file.id}
                                    className={`rounded-lg border p-6 hover:shadow-md transition-shadow ${selectedFiles.has(file.id)
                                        ? 'bg-red-50 border-red-300 ring-2 ring-red-200'
                                        : 'bg-white border-gray-200'
                                        }`}
                                >
                                    <div className="mb-4 flex items-start justify-between">
                                        <h3
                                            className={`text-lg font-medium truncate flex-1 ${selectedFiles.has(file.id) ? 'text-red-900' : 'text-gray-900'}`}
                                            title={file.filename}
                                        >
                                            {file.filename}
                                        </h3>
                                        {file.can_delete && (
                                            <button
                                                onClick={() => toggleFileSelection(file.id)}
                                                disabled={deleting}
                                                className={`ml-2 p-1.5 rounded hover:bg-opacity-80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${selectedFiles.has(file.id)
                                                        ? 'text-red-700 bg-red-100 hover:bg-red-200'
                                                        : 'text-gray-400 hover:bg-gray-100'
                                                    }`}
                                                title={selectedFiles.has(file.id) ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                            >
                                                <svg
                                                    className="w-5 h-5"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    viewBox="0 0 24 24"
                                                    xmlns="http://www.w3.org/2000/svg"
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
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Tipo:</span>
                                            <span className="text-gray-900 font-medium">{file.content_type}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Tamanho:</span>
                                            <span className="text-gray-900 font-medium">
                                                {formatFileSize(file.file_size)}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Criado em:</span>
                                            <span className="text-gray-900 font-medium">
                                                {formatDate(file.created_at)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Paginação */}
                    {total > limit && (
                        <div className="flex items-center justify-between bg-white rounded-lg border border-gray-200 px-6 py-4">
                            <div className="text-sm text-gray-700">
                                Página {currentPage} de {totalPages} ({total} arquivos)
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={goToPreviousPage}
                                    disabled={offset === 0}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Anterior
                                </button>
                                <button
                                    onClick={goToNextPage}
                                    disabled={offset + limit >= total}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Próxima
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            {selectedFiles.size > 0 && <BottomActionBarSpacer />}

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