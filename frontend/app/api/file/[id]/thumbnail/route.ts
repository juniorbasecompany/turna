import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/file/[id]/thumbnail
 *
 * Proxy para obter thumbnail do arquivo do backend.
 * Retorna thumbnail WebP 500x500 ou 404 se não encontrado.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const fileId = params.id

        if (!fileId) {
            return NextResponse.json(
                { detail: 'ID do arquivo é obrigatório' },
                { status: 400 }
            )
        }

        // Obter access_token do cookie
        const accessToken = request.cookies.get('access_token')?.value
        console.log(`[THUMBNAIL-FRONTEND] Buscando thumbnail para file_id=${fileId}, hasToken=${!!accessToken}`)

        // Chamar endpoint do backend que serve o thumbnail
        const thumbnailResponse = await fetch(`${API_URL}/file/${fileId}/thumbnail`, {
            method: 'GET',
            headers: {
                ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
            },
            credentials: 'include',
        })

        console.log(`[THUMBNAIL-FRONTEND] Response status: ${thumbnailResponse.status}, contentType: ${thumbnailResponse.headers.get('content-type')}`)

        if (!thumbnailResponse.ok) {
            const errorData = await thumbnailResponse.text().catch(() => 'Erro desconhecido')
            console.error(`[THUMBNAIL-FRONTEND] Erro ao obter thumbnail: status=${thumbnailResponse.status}, body=${errorData.substring(0, 200)}`)
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

        // Retornar o thumbnail com headers apropriados
        return new NextResponse(blob, {
            headers: {
                'Content-Type': contentType,
                'Cache-Control': 'private, max-age=3600',
            },
        })
    } catch (error) {
        console.error('Erro ao fazer proxy do thumbnail:', error)
        return NextResponse.json(
            {
                detail:
                    error instanceof Error
                        ? error.message
                        : 'Erro desconhecido ao obter thumbnail',
            },
            { status: 500 }
        )
    }
}
