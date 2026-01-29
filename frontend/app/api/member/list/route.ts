import { backendFetch, requireToken } from '@/lib/backend-fetch'
import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/member/list
 *
 * Lista todos os members do tenant atual.
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

    const result = await backendFetch('/member/list', {
        token: auth.token,
        params,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
