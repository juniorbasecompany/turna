import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/demand/procedure/list
 *
 * Lista procedimentos distintos das demandas do tenant atual.
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

    const result = await backendFetch('/demand/procedure/list', {
        token: auth.token,
        params,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
