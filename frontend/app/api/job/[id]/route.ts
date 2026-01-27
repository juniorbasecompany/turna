import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, errorResponse, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/job/[id]
 *
 * Obtém o status e resultado de um job específico.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    if (!params.id) {
        return errorResponse('ID do job é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/job/${params.id}`, {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}

/**
 * PUT /api/job/[id]
 *
 * Atualiza um job específico (apenas result_data).
 */
export async function PUT(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    if (!params.id) {
        return errorResponse('ID do job é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json()

    const result = await backendFetch(`/job/${params.id}`, {
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
 * DELETE /api/job/[id]
 *
 * Exclui um job que está COMPLETED ou FAILED.
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    if (!params.id) {
        return errorResponse('ID do job é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/job/${params.id}`, {
        method: 'DELETE',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
