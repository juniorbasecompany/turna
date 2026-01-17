'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // XLSX
  'application/vnd.ms-excel', // XLS
  'text/csv',
]

const ALLOWED_EXTENSIONS = ['.pdf', '.jpeg', '.jpg', '.png', '.xlsx', '.xls', '.csv']

type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

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

export default function ImportPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [jobId, setJobId] = useState<number | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<string>('')

  // Polling do status do job
  const pollJobStatus = useCallback(
    async (id: number) => {
      try {
        const response = await fetch(`/api/job/${id}`, {
          credentials: 'include',
        })

        if (!response.ok) {
          if (response.status === 401) {
            router.push('/login')
            return
          }
          throw new Error(`Erro ao verificar status do job: ${response.status}`)
        }

        const job: JobResponse = await response.json()
        setJobStatus(job.status)

        // Se ainda está processando, continuar polling
        if (job.status === 'PENDING' || job.status === 'RUNNING') {
          setTimeout(() => pollJobStatus(id), 2000) // Poll a cada 2 segundos
        } else if (job.status === 'FAILED') {
          setProcessing(false)
          setError(job.error_message || 'Erro desconhecido ao processar arquivo')
        } else if (job.status === 'COMPLETED') {
          setProcessing(false)
          setUploadProgress('Processamento concluído com sucesso!')
        }
      } catch (err) {
        setProcessing(false)
        setError(
          err instanceof Error
            ? err.message
            : 'Erro ao verificar status do job'
        )
      }
    },
    [router]
  )

  // Validar tipo de arquivo
  const validateFile = useCallback((file: File): boolean => {
    // Verificar extensão
    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setError(
        `Tipo de arquivo não permitido. Use: ${ALLOWED_EXTENSIONS.join(', ')}`
      )
      return false
    }

    // Verificar MIME type (opcional, pode ser inexato)
    if (file.type && !ALLOWED_TYPES.includes(file.type)) {
      // Não bloqueia se a extensão estiver correta
      console.warn(`MIME type não reconhecido: ${file.type}, mas extensão OK`)
    }

    return true
  }, [])

  // Upload do arquivo
  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return

      setError(null)
      setUploadProgress('')

      if (!validateFile(file)) {
        return
      }

      setSelectedFile(file)
    },
    [validateFile]
  )

  // Upload e criação do job
  const handleUpload = useCallback(async () => {
    if (!selectedFile) return

    setError(null)
    setUploading(true)
    setUploadProgress('Enviando arquivo...')

    try {
      // 1. Upload do arquivo
      const formData = new FormData()
      formData.append('file', selectedFile)

      const uploadResponse = await fetch('/api/file/upload', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!uploadResponse.ok) {
        if (uploadResponse.status === 401) {
          router.push('/login')
          return
        }
        const errorData = await uploadResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || `Erro ao fazer upload: ${uploadResponse.status}`)
      }

      const uploadData: FileUploadResponse = await uploadResponse.json()
      setUploadProgress(`Arquivo enviado (ID: ${uploadData.file_id}). Criando job...`)

      // 2. Criar job de extração
      const jobResponse = await fetch('/api/job/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_id: uploadData.file_id }),
        credentials: 'include',
      })

      if (!jobResponse.ok) {
        if (jobResponse.status === 401) {
          router.push('/login')
          return
        }
        const errorData = await jobResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || `Erro ao criar job: ${jobResponse.status}`)
      }

      const jobData: JobExtractResponse = await jobResponse.json()
      setJobId(jobData.job_id)
      setUploading(false)
      setProcessing(true)
      setUploadProgress('Job criado. Processando arquivo...')

      // 3. Iniciar polling do status
      pollJobStatus(jobData.job_id)
    } catch (err) {
      setUploading(false)
      setProcessing(false)
      setError(
        err instanceof Error ? err.message : 'Erro desconhecido ao processar arquivo'
      )
    }
  }, [selectedFile, router, pollJobStatus])

  // Reset do formulário
  const handleReset = useCallback(() => {
    setSelectedFile(null)
    setUploading(false)
    setProcessing(false)
    setJobId(null)
    setJobStatus(null)
    setError(null)
    setUploadProgress('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [])

  // Limpar estados ao desmontar
  useEffect(() => {
    return () => {
      setJobId(null)
      setJobStatus(null)
    }
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Nova Importação</h1>
        <p className="mt-2 text-gray-600">
          Envie arquivos para processar e extrair demandas
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        {/* Upload de arquivo */}
        <div className="mb-6">
          <label
            htmlFor="file-upload"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Selecionar arquivo
          </label>
          <div className="mt-1 flex items-center">
            <input
              ref={fileInputRef}
              id="file-upload"
              type="file"
              accept={ALLOWED_EXTENSIONS.join(',')}
              onChange={handleFileSelect}
              disabled={uploading || processing}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Formatos permitidos: PDF, JPEG, PNG, XLSX, XLS, CSV
          </p>
        </div>

        {selectedFile && (
          <div className="mb-6 p-4 bg-gray-50 rounded-md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              {!uploading && !processing && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFile(null)
                    if (fileInputRef.current) {
                      fileInputRef.current.value = ''
                    }
                  }}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Remover
                </button>
              )}
            </div>
          </div>
        )}

        {/* Mensagens de progresso */}
        {uploadProgress && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-800">{uploadProgress}</p>
          </div>
        )}

        {/* Status do job */}
        {jobStatus && (
          <div className="mb-6">
            <div className="flex items-center space-x-2">
              {jobStatus === 'PENDING' && (
                <div className="flex items-center">
                  <svg
                    className="animate-spin h-5 w-5 text-blue-600"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <span className="ml-2 text-sm text-blue-600">Aguardando processamento</span>
                </div>
              )}
              {jobStatus === 'RUNNING' && (
                <div className="flex items-center">
                  <svg
                    className="animate-spin h-5 w-5 text-green-600"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <span className="ml-2 text-sm text-green-600">Processando...</span>
                </div>
              )}
              {jobStatus === 'COMPLETED' && (
                <div className="flex items-center">
                  <svg
                    className="h-5 w-5 text-green-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="ml-2 text-sm text-green-600">Concluído com sucesso!</span>
                </div>
              )}
              {jobStatus === 'FAILED' && (
                <div className="flex items-center">
                  <svg
                    className="h-5 w-5 text-red-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  <span className="ml-2 text-sm text-red-600">Falha no processamento</span>
                </div>
              )}
            </div>
            {jobId && (
              <p className="mt-1 text-xs text-gray-500">Job ID: {jobId}</p>
            )}
          </div>
        )}

        {/* Mensagens de erro */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Botões de ação */}
        <div className="flex items-center space-x-4">
          <button
            type="button"
            onClick={handleUpload}
            disabled={!selectedFile || uploading || processing}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'Enviando...' : processing ? 'Processando...' : 'Enviar e Processar'}
          </button>

          {(jobStatus === 'COMPLETED' || jobStatus === 'FAILED' || error) && (
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Novo Upload
            </button>
          )}
        </div>
      </div>
    </div>
  )
}