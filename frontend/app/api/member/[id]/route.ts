import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/member/[id]
 *
 * Obtém detalhes de um member específico.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/member/${params.id}`, {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}

/**
 * PUT /api/member/[id]
 *
 * Atualiza um member (apenas admin).
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

    const result = await backendFetch(`/member/${params.id}`, {
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
 * DELETE /api/member/[id]
 *
 * Remove um member (apenas admin).
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/member/${params.id}`, {
        method: 'DELETE',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
