import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, errorResponse, requireToken } from '@/lib/backend-fetch'

/**
 * GET /api/file/[id]
 *
 * Obtém informações do arquivo e URL presignada.
 * Para download, use /api/file/[id]/proxy
 */
export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> | { id: string } }
) {
    // Lidar com params síncrono (Next.js 13/14) ou assíncrono (Next.js 15+)
    const resolvedParams = params instanceof Promise ? await params : params
    const fileId = resolvedParams.id

    if (!fileId) {
        return errorResponse('ID do arquivo é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/file/${fileId}`, {
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}

/**
 * DELETE /api/file/[id]
 *
 * Exclui arquivo do backend e do S3/MinIO.
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> | { id: string } }
) {
    // Lidar com params síncrono (Next.js 13/14) ou assíncrono (Next.js 15+)
    const resolvedParams = params instanceof Promise ? await params : params
    const fileId = resolvedParams.id

    if (!fileId) {
        return errorResponse('ID do arquivo é obrigatório', 400)
    }

    const fileIdNum = parseInt(fileId, 10)
    if (isNaN(fileIdNum)) {
        return errorResponse('ID do arquivo deve ser um número válido', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/file/${fileIdNum}`, {
        method: 'DELETE',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
