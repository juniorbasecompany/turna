import { NextRequest, NextResponse } from 'next/server'
import { errorResponse, requireToken } from '@/lib/backend-fetch'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/file/[id]/thumbnail
 *
 * Proxy para obter thumbnail do arquivo do backend.
 * Retorna thumbnail WebP 500x500 ou 404 se não encontrado.
 * 
 * Nota: Esta rota não usa backendFetch pois retorna blob, não JSON.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const fileId = params.id

    if (!fileId) {
        return errorResponse('ID do arquivo é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    try {
        const thumbnailResponse = await fetch(`${API_URL}/file/${fileId}/thumbnail`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${auth.token}`,
            },
        })

        if (!thumbnailResponse.ok) {
            const errorData = await thumbnailResponse.text().catch(() => 'Erro desconhecido')
            try {
                const jsonError = JSON.parse(errorData)
                return NextResponse.json(jsonError, { status: thumbnailResponse.status })
            } catch {
                return NextResponse.json(
                    { detail: errorData || `Erro HTTP ${thumbnailResponse.status}` },
                    { status: thumbnailResponse.status }
                )
            }
        }

        const blob = await thumbnailResponse.blob()
        const contentType = thumbnailResponse.headers.get('content-type') || 'image/webp'

        return new NextResponse(blob, {
            headers: {
                'Content-Type': contentType,
                'Cache-Control': 'private, max-age=3600',
            },
        })
    } catch (error) {
        const isConnectionError = error instanceof TypeError || 
            (error instanceof Error && error.message.includes('fetch'))
        
        return NextResponse.json(
            { detail: isConnectionError 
                ? 'Servidor indisponível. Verifique sua conexão e tente novamente.'
                : (error instanceof Error ? error.message : 'Erro desconhecido ao obter thumbnail')
            },
            { status: isConnectionError ? 503 : 500 }
        )
    }
}
