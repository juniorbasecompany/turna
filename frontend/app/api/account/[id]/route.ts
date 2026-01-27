import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * PUT /api/account/[id]
 *
 * Atualiza um account (apenas admin).
 */
export async function PUT(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json()

    const result = await backendFetch(`/account/${params.id}`, {
        method: 'PUT',
        token: auth.token,
        body,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}

/**
 * DELETE /api/account/[id]
 *
 * Remove um account do tenant atual (apenas admin).
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/account/${params.id}`, {
        method: 'DELETE',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
