import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * POST /api/job/[id]/cancel
 *
 * Cancela um job, mudando seu status para FAILED.
 */
export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/job/${params.id}/cancel`, {
        method: 'POST',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
