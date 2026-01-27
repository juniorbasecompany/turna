import { GoogleTokenRequest, TokenResponse } from '@/types/api'
import { backendFetch, errorResponse, successWithCookie } from '@/lib/backend-fetch'
import { NextRequest } from 'next/server'

/**
 * Handler Next.js para criação automática de tenant
 *
 * Recebe id_token do Google, chama backend POST /auth/google/create-tenant,
 * e atualiza cookie com novo JWT.
 */
export async function POST(request: NextRequest) {
    const body: GoogleTokenRequest = await request.json()

    if (!body.id_token) {
        return errorResponse('id_token é obrigatório', 400)
    }

    // Chamar backend (tratamento de erros centralizado)
    const result = await backendFetch<TokenResponse>('/auth/google/create-tenant', {
        method: 'POST',
        body: { id_token: body.id_token },
    })

    if (!result.ok) {
        return result.error
    }

    // Atualizar cookie com novo JWT
    return successWithCookie(result.data, 'access_token', result.data.access_token)
}
