import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * PUT /api/tenant/[id]
 *
 * Atualiza um tenant (apenas admin).
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

    const result = await backendFetch(`/tenant/${params.id}`, {
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
 * DELETE /api/tenant/[id]
 *
 * Remove um tenant (apenas admin).
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/tenant/${params.id}`, {
        method: 'DELETE',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
