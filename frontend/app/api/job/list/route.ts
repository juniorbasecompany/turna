import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/job/list
 *
 * Lista todos os jobs do tenant atual.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const { searchParams } = new URL(request.url)

    const result = await backendFetch('/job/list', {
        token: auth.token,
        params: {
            job_type: searchParams.get('job_type'),
            status: searchParams.get('status'),
            limit: searchParams.get('limit'),
            offset: searchParams.get('offset'),
        },
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
