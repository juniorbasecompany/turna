import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

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

    const result = await backendFetch('/member/list', {
        token: auth.token,
        params: {
            status: searchParams.get('status'),
            role: searchParams.get('role'),
            limit: searchParams.get('limit'),
            offset: searchParams.get('offset'),
        },
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
