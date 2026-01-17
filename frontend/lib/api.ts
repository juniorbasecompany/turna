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
                if (!path.startsWith('/login') && !path.startsWith('/select-tenant') && !path.startsWith('/dashboard') && !path.startsWith('/file')) {
                    window.location.href = '/login'
                }
            }
            throw new ApiError('Não autenticado', 401)
        }

        if (response.status === 403) {
            // Acesso negado → mensagem clara
            const errorData = await response.json().catch(() => ({}))
            throw new ApiError(
                errorData.detail || 'Acesso negado a este recurso',
                403,
                errorData
            )
        }

        if (!response.ok) {
            // Outros erros HTTP
            const errorData = await response.json().catch(() => ({}))
            throw new ApiError(
                errorData.detail || `Erro HTTP ${response.status}`,
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
