import { backendFetch, requireToken } from '@/lib/backend-fetch'
import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/account/list
 *
 * Lista todos os account list do tenant atual.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch('/account/list', {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
