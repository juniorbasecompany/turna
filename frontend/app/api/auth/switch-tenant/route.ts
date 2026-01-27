import { NextRequest } from 'next/server'
import { backendFetch, errorResponse, requireToken, successWithCookie } from '@/lib/backend-fetch'

/**
 * Handler Next.js para trocar de tenant (quando já autenticado)
 *
 * Recebe tenant_id, chama backend POST /auth/switch-tenant,
 * e atualiza cookie com novo JWT.
 * Não requer id_token do Google - funciona apenas com cookie de autenticação.
 */
export async function POST(request: NextRequest) {
    const body = await request.json()

    if (!body.tenant_id) {
        return errorResponse('tenant_id é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch<{ access_token: string }>('/auth/switch-tenant', {
        method: 'POST',
        token: auth.token,
        body: { tenant_id: body.tenant_id },
    })

    if (!result.ok) {
        return result.error
    }

    return successWithCookie(result.data, 'access_token', result.data.access_token)
}
