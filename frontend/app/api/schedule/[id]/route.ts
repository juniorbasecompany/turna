import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/schedule/[id]
 *
 * Obtém detalhes de uma escala específica.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/schedule/${params.id}`, {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}

/**
 * PUT /api/schedule/[id]
 *
 * Atualiza uma escala.
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

    const result = await backendFetch(`/schedule/${params.id}`, {
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
 * DELETE /api/schedule/[id]
 *
 * Exclui uma escala.
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/schedule/${params.id}`, {
        method: 'DELETE',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
