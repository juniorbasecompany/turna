import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * POST /api/tenant
 *
 * Cria um novo tenant (apenas admin).
 */
export async function POST(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json()

    const result = await backendFetch('/tenant', {
        method: 'POST',
        token: auth.token,
        body,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
