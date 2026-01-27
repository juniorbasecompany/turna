import { AuthResponse, GoogleTokenRequest } from '@/types/api'
import { backendFetch, errorResponse, successWithCookie } from '@/lib/backend-fetch'
import { NextRequest, NextResponse } from 'next/server'

/**
 * Handler Next.js para cadastro com Google
 *
 * Recebe id_token do frontend, chama backend POST /auth/google/register,
 * e grava JWT em cookie httpOnly.
 */
export async function POST(request: NextRequest) {
    const body: GoogleTokenRequest = await request.json()

    if (!body.id_token) {
        return errorResponse('id_token é obrigatório', 400)
    }

    // Chamar backend (tratamento de erros centralizado)
    const result = await backendFetch<AuthResponse>('/auth/google/register', {
        method: 'POST',
        body: { id_token: body.id_token },
    })

    if (!result.ok) {
        return result.error
    }

    const data = result.data

    // Verificar requires_tenant_selection PRIMEIRO
    // Se exige seleção de tenant, retornar resposta sem gravar cookie
    if (data.requires_tenant_selection) {
        return NextResponse.json(data)
    }

    // Se temos access_token, gravar em cookie httpOnly
    if (data.access_token) {
        return successWithCookie(data, 'access_token', data.access_token)
    }

    // Sem token e sem requires_tenant_selection (resposta inesperada)
    return NextResponse.json(data)
}
