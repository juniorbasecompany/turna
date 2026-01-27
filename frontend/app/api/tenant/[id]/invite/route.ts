import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * POST /api/tenant/[id]/invite
 *
 * Cria/atualiza um convite (Member PENDING) para um email no tenant (apenas admin).
 */
export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json()

    const result = await backendFetch(`/tenant/${params.id}/invite`, {
        method: 'POST',
        token: auth.token,
        body,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
