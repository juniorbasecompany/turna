import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/hospital/list
 *
 * Lista todos os hospitais do tenant atual.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch('/hospital/list', {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
