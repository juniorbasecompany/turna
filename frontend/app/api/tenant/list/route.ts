import { backendFetch, requireToken } from '@/lib/backend-fetch'
import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/tenant/list
 *
 * Lista todos os tenants (apenas admin).
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const { searchParams } = new URL(request.url)
    const params: Record<string, string> = {}
    searchParams.forEach((value, key) => {
        params[key] = value
    })

    const result = await backendFetch('/tenant/list', {
        token: auth.token,
        params,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
