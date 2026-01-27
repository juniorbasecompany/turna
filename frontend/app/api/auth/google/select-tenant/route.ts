import { GoogleSelectTenantRequest, TokenResponse } from '@/types/api'
import { backendFetch, errorResponse, successWithCookie } from '@/lib/backend-fetch'
import { NextRequest } from 'next/server'

/**
 * Handler Next.js para seleção de tenant
 *
 * Recebe id_token + tenant_id, chama backend POST /auth/google/select-tenant,
 * e atualiza cookie com novo JWT.
 */
export async function POST(request: NextRequest) {
    const body: GoogleSelectTenantRequest = await request.json()

    if (!body.id_token || !body.tenant_id) {
        return errorResponse('id_token e tenant_id são obrigatórios', 400)
    }

    // Chamar backend (tratamento de erros centralizado)
    const result = await backendFetch<TokenResponse>('/auth/google/select-tenant', {
        method: 'POST',
        body: {
            id_token: body.id_token,
            tenant_id: body.tenant_id,
        },
    })

    if (!result.ok) {
        return result.error
    }

    // Atualizar cookie com novo JWT
    return successWithCookie(result.data, 'access_token', result.data.access_token)
}
