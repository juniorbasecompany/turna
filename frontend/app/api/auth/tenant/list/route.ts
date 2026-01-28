import { backendFetch, requireToken } from '@/lib/backend-fetch'
import { TenantListResponse } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'

/**
 * Handler Next.js para listar tenants disponíveis
 *
 * Chama GET /auth/tenant/list no backend.
 * Requer autenticação via cookie httpOnly.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch<TenantListResponse>('/auth/tenant/list', {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
