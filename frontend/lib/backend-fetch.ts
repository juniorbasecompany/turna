import { NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Resultado de uma chamada ao backend.
 * Pode ser uma resposta de sucesso ou erro.
 */
export type BackendResult<T> =
    | { ok: true; data: T; response: Response }
    | { ok: false; error: NextResponse }

/**
 * Opções para chamada ao backend.
 */
interface BackendFetchOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
    body?: unknown
    headers?: Record<string, string>
    /** Token de autenticação (será adicionado como Bearer) */
    token?: string
    /** Query params para adicionar à URL */
    params?: Record<string, string | number | boolean | null | undefined>
}

/**
 * Verifica se é erro de conexão (backend indisponível).
 */
function isConnectionError(error: unknown): boolean {
    if (error instanceof TypeError) {
        return true
    }
    if (error instanceof Error) {
        const msg = error.message.toLowerCase()
        return msg.includes('fetch') || msg.includes('network') || msg.includes('econnrefused')
    }
    return false
}

/**
 * Fetch centralizado para chamadas ao backend.
 *
 * Trata automaticamente:
 * - Erros de conexão (503 - Servidor indisponível)
 * - Parsing de JSON
 * - Headers de autenticação
 *
 * @param endpoint - Endpoint do backend (ex: '/auth/google', '/hospital/list')
 * @param options - Opções da requisição
 * @returns BackendResult com dados ou erro
 *
 * @example
 * ```typescript
 * const result = await backendFetch<AuthResponse>('/auth/google', {
 *     method: 'POST',
 *     body: { id_token: token },
 * })
 *
 * if (!result.ok) {
 *     return result.error // NextResponse já formatado
 * }
 *
 * const data = result.data // Tipado como AuthResponse
 * ```
 */
export async function backendFetch<T>(
    endpoint: string,
    options: BackendFetchOptions = {}
): Promise<BackendResult<T>> {
    const { method = 'GET', body, headers = {}, token, params } = options

    try {
        const requestHeaders: Record<string, string> = {
            'Content-Type': 'application/json',
            ...headers,
        }

        if (token) {
            requestHeaders['Authorization'] = `Bearer ${token}`
        }

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

        const response = await fetch(url, {
            method,
            headers: requestHeaders,
            body: body ? JSON.stringify(body) : undefined,
        })

        // Tentar fazer parse do JSON (mesmo em erros, o backend retorna JSON)
        let data: T
        try {
            data = await response.json()
        } catch {
            // Se não conseguir fazer parse, criar objeto vazio
            data = {} as T
        }

        if (!response.ok) {
            // Propagar erro do backend com status original
            return {
                ok: false,
                error: NextResponse.json(data, { status: response.status }),
            }
        }

        return { ok: true, data, response }
    } catch (error) {
        console.error(`[backendFetch] Erro ao chamar ${endpoint}:`, error)

        // Erro de conexão (backend indisponível)
        if (isConnectionError(error)) {
            return {
                ok: false,
                error: NextResponse.json(
                    { detail: 'Servidor indisponível. Verifique sua conexão e tente novamente.' },
                    { status: 503 }
                ),
            }
        }

        // Outros erros
        return {
            ok: false,
            error: NextResponse.json(
                { detail: 'Erro interno do servidor' },
                { status: 500 }
            ),
        }
    }
}

/**
 * Faz fetch ao backend e retorna a resposta bruta (para PDF/binário).
 * Usado pelas rotas de relatório que repassam o stream do backend.
 */
export async function backendFetchPdf(
    endpoint: string,
    token: string,
    params?: Record<string, string | number | boolean | null | undefined>
): Promise<NextResponse> {
    let url = `${API_URL}${endpoint}`
    if (params) {
        const searchParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                searchParams.append(key, String(value))
            }
        })
        const qs = searchParams.toString()
        if (qs) url += `?${qs}`
    }
    const response = await fetch(url, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
        const text = await response.text()
        let detail: string = 'Erro ao gerar relatório'
        try {
            const data = JSON.parse(text) as { detail?: string | unknown; error?: { message?: string } }
            const d = data.detail ?? data.error?.message
            if (typeof d === 'string') detail = d
            else if (Array.isArray(d) && d.length > 0) detail = (d[0] as { msg?: string })?.msg ?? String(d[0])
            else if (d != null) detail = String(d)
        } catch {
            if (text.length > 0) detail = text.slice(0, 500)
        }
        return NextResponse.json({ detail }, { status: response.status })
    }
    const contentType = response.headers.get('Content-Type') || 'application/pdf'
    const contentDisposition = response.headers.get('Content-Disposition') || 'attachment; filename="relatorio.pdf"'
    return new NextResponse(response.body, {
        status: 200,
        headers: {
            'Content-Type': contentType,
            'Content-Disposition': contentDisposition,
        },
    })
}

/**
 * Helper para criar resposta de erro padronizada.
 */
export function errorResponse(message: string, status: number = 400): NextResponse {
    return NextResponse.json({ detail: message }, { status })
}

/**
 * Helper para verificar token de autenticação.
 * Retorna o token se existir, ou uma resposta 401 se não existir.
 */
export function requireToken(request: { cookies: { get: (name: string) => { value: string } | undefined } }): { ok: true; token: string } | { ok: false; error: NextResponse } {
    const token = request.cookies.get('access_token')?.value
    if (!token) {
        return {
            ok: false,
            error: NextResponse.json({ detail: 'Não autenticado' }, { status: 401 }),
        }
    }
    return { ok: true, token }
}

/**
 * Helper para criar resposta de sucesso com cookie.
 */
export function successWithCookie<T>(
    data: T,
    cookieName: string,
    cookieValue: string,
    options: { maxAge?: number } = {}
): NextResponse {
    const response = NextResponse.json(data)

    response.cookies.set(cookieName, cookieValue, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: options.maxAge ?? 60 * 60 * 24 * 7, // 7 dias por padrão
        path: '/',
    })

    return response
}
