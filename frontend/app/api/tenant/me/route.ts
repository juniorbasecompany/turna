import { TenantResponse } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * Handler Next.js para obter informações do tenant atual
 *
 * Chama GET /tenant/me no backend.
 * Requer autenticação via cookie httpOnly.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch<TenantResponse>('/tenant/me', {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
