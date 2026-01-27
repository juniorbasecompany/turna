import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * POST /api/schedule/generate-from-demands
 *
 * Gera escala a partir de demandas da tabela demand.
 */
export async function POST(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json()

    const result = await backendFetch('/schedule/generate-from-demands', {
        method: 'POST',
        token: auth.token,
        body,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data, { status: 201 })
}
