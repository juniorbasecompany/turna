import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/file/list
 *
 * Lista arquivos do tenant atual com paginação e filtros por período.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const { searchParams } = new URL(request.url)

    const result = await backendFetch('/file/list', {
        token: auth.token,
        params: {
            start_at: searchParams.get('start_at'),
            end_at: searchParams.get('end_at'),
            hospital_id: searchParams.get('hospital_id'),
            limit: searchParams.get('limit') || '19',
            offset: searchParams.get('offset') || '0',
        },
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
