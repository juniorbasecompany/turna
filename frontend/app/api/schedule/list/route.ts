import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/schedule/list
 *
 * Lista escalas do tenant atual, com filtros opcionais e paginação.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    // Passar todos os query params para o backend
    const { searchParams } = new URL(request.url)
    const params: Record<string, string> = {}
    searchParams.forEach((value, key) => {
        params[key] = value
    })

    const result = await backendFetch('/schedule/list', {
        token: auth.token,
        params,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
