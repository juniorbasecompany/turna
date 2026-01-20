/**
 * Cliente HTTP para comunicação com a API backend
 *
 * Usa fetch nativo com credentials: "include" para cookies httpOnly.
 * Tratamento centralizado de erros (401 → redirect login, 403 → mensagem).
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public data?: unknown
    ) {
        super(message)
        this.name = 'ApiError'
    }
}

/**
 * Extrai a mensagem de erro de um objeto de erro do backend.
 * Suporta múltiplos formatos de resposta de erro.
 */
export function extractErrorMessage(errorData: unknown, defaultMessage = 'Erro desconhecido'): string {
    if (!errorData || typeof errorData !== 'object') {
        return defaultMessage
    }

    const data = errorData as Record<string, unknown>

    // Debug: log do objeto de erro para entender o formato
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
        console.log('Error data received:', JSON.stringify(data, null, 2))
    }

    // Formato FastAPI padrão: { detail: "..." }
    if (typeof data.detail === 'string') {
        return data.detail
    }

    // Formato normalizado: { error: { code: "...", message: "..." } }
    if (data.error && typeof data.error === 'object') {
        const error = data.error as Record<string, unknown>
        if (typeof error.message === 'string') {
            // Retorna apenas a mensagem (sem incluir o código HTTP_500, etc)
            return error.message
        }
    }

    // Formato alternativo: { message: "..." }
    if (typeof data.message === 'string') {
        return data.message
    }

    // Se não encontrou nenhum formato conhecido, retorna o default
    // mas também tenta stringificar o objeto para debug
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
        console.warn('Could not extract error message from:', data)
    }

    return defaultMessage
}

/**
 * Fetch protegido para páginas protegidas.
 * Trata 401 automaticamente e padroniza mensagens de erro.
 *
 * Esta função deve ser usada em todas as páginas protegidas para garantir
 * que erros 401 sempre retornem a mensagem padronizada e sejam exibidos no ActionBar.
 *
 * @param url - URL da API (relativa, ex: '/api/profile/list')
 * @param options - Opções do fetch (method, headers, body, etc)
 * @returns Promise com os dados da resposta
 * @throws Error com mensagem padronizada (401 sempre retorna "Sessão expirada...")
 *
 * @example
 * ```typescript
 * try {
 *   const data = await protectedFetch<ProfileListResponse>('/api/profile/list')
 *   setProfiles(data.items)
 * } catch (err) {
 *   setError(err instanceof Error ? err.message : 'Erro desconhecido')
 * }
 * ```
 */
export async function protectedFetch<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const response = await fetch(url, {
        ...options,
        credentials: 'include',
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))

        // SEMPRE tratar 401 primeiro, antes de extractErrorMessage
        // Isso garante que a mensagem seja sempre padronizada
        if (response.status === 401) {
            throw new Error('Sessão expirada. Por favor, faça login novamente.')
        }

        // Outros erros usam extractErrorMessage
        throw new Error(extractErrorMessage(errorData, `Erro HTTP ${response.status}`))
    }

    // Resposta vazia (204 No Content)
    if (response.status === 204) {
        return undefined as T
    }

    return await response.json() as T
}

interface RequestOptions extends RequestInit {
    params?: Record<string, string | number | boolean | null | undefined>
}

/**
 * Função única para chamadas à API
 */
export async function apiRequest<T>(
    endpoint: string,
    options: RequestOptions = {}
): Promise<T> {
    const { params, ...fetchOptions } = options

    // Construir URL com query params
    let url = `${API_URL}${endpoint}`
    if (params) {
        const searchParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                searchParams.append(key, String(value))
            }
        })
        const queryString = searchParams.toString()
        if (queryString) {
            url += `?${queryString}`
        }
    }

    // Configuração padrão: credentials para cookies httpOnly
    const defaultHeaders: HeadersInit = {
        'Content-Type': 'application/json',
    }

    const config: RequestInit = {
        ...fetchOptions,
        credentials: 'include', // Importante: permite cookies httpOnly
        headers: {
            ...defaultHeaders,
            ...fetchOptions.headers,
        },
    }

    try {
        const response = await fetch(url, config)

        // Tratamento centralizado de erros
        if (response.status === 401) {
            // Não autenticado → redirecionar para login (exceto se já estiver em páginas de autenticação ou páginas protegidas que gerenciam seu próprio erro)
            // Páginas protegidas devem decidir o que fazer com 401, não fazer redirecionamento automático
            if (typeof window !== 'undefined') {
                const path = window.location.pathname

                // Rotas de autenticação: não redirecionar
                const isAuthRoute = path.startsWith('/login') || path.startsWith('/select-tenant')

                // Rotas de API: não redirecionar (não são páginas)
                const isApiRoute = path.startsWith('/api')

                // Páginas protegidas: todas as outras rotas (exceto raiz) são assumidas como protegidas
                // Todas as páginas em app/(protected)/ seguem o padrão de usar fetch() direto
                // e gerenciam seus próprios erros 401, então não devem ser redirecionadas automaticamente
                const isProtectedRoute = path !== '/' && !isAuthRoute && !isApiRoute

                // Redirecionar apenas se não for rota de autenticação, API ou protegida
                if (!isAuthRoute && !isApiRoute && !isProtectedRoute) {
                    window.location.href = '/login'
                }
            }
            throw new ApiError('Não autenticado', 401)
        }

        if (response.status === 403) {
            // Acesso negado → mensagem clara
            const errorData = await response.json().catch(() => ({}))
            throw new ApiError(
                extractErrorMessage(errorData, 'Acesso negado a este recurso'),
                403,
                errorData
            )
        }

        if (!response.ok) {
            // Outros erros HTTP
            let errorData: unknown = {}
            try {
                const text = await response.text()
                if (text) {
                    try {
                        errorData = JSON.parse(text)
                        // Debug: log do erro parseado
                        if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
                            console.log('Parsed error data:', errorData)
                        }
                    } catch (parseError) {
                        // Se não conseguir fazer parse JSON, usa o texto como mensagem
                        console.warn('Failed to parse error response as JSON:', parseError, 'Text:', text)
                        errorData = { message: text }
                    }
                } else {
                    console.warn('Empty error response body')
                }
            } catch (textError) {
                // Se não conseguir ler o texto, usa mensagem padrão
                console.warn('Failed to read error response text:', textError)
                errorData = {}
            }

            const errorMessage = extractErrorMessage(errorData, `Erro HTTP ${response.status}`)

            // Debug: log da mensagem extraída
            if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
                console.log('Extracted error message:', errorMessage)
            }

            throw new ApiError(
                errorMessage,
                response.status,
                errorData
            )
        }

        // Resposta vazia (204 No Content)
        if (response.status === 204) {
            return undefined as T
        }

        // Parse JSON
        const data = await response.json()
        return data as T
    } catch (error) {
        // Re-throw ApiError
        if (error instanceof ApiError) {
            throw error
        }

        // Erros de rede ou outros
        if (error instanceof TypeError && error.message.includes('fetch')) {
            throw new ApiError('Erro de conexão com o servidor', 0)
        }

        throw new ApiError(
            error instanceof Error ? error.message : 'Erro desconhecido',
            0
        )
    }
}

/**
 * Helpers para métodos HTTP comuns
 */
export const api = {
    get: <T>(endpoint: string, options?: RequestOptions) =>
        apiRequest<T>(endpoint, { ...options, method: 'GET' }),

    post: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
        apiRequest<T>(endpoint, {
            ...options,
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined,
        }),

    put: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
        apiRequest<T>(endpoint, {
            ...options,
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined,
        }),

    patch: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
        apiRequest<T>(endpoint, {
            ...options,
            method: 'PATCH',
            body: data ? JSON.stringify(data) : undefined,
        }),

    delete: <T>(endpoint: string, options?: RequestOptions) =>
        apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),
}
