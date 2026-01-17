import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/file/[id]/proxy
 *
 * Proxy para obter arquivo do MinIO e servir ao cliente.
 * Resolve o problema de URLs do MinIO não serem acessíveis do navegador.
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

        // Usar endpoint do backend que serve o arquivo diretamente do MinIO
        const downloadResponse = await fetch(`${API_URL}/file/${fileId}/download`, {
            method: 'GET',
            headers: {
                ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
            },
            credentials: 'include',
        })

        if (!downloadResponse.ok) {
            const errorData = await downloadResponse.text().catch(() => 'Erro desconhecido')
            try {
                const jsonError = JSON.parse(errorData)
                return NextResponse.json(jsonError, { status: downloadResponse.status })
            } catch {
                return NextResponse.json(
                    { detail: errorData || `Erro HTTP ${downloadResponse.status}` },
                    { status: downloadResponse.status }
                )
            }
        }

        const blob = await downloadResponse.blob()
        const contentType = downloadResponse.headers.get('content-type') || 'application/octet-stream'

        // Retornar o arquivo com headers apropriados
        // Usar inline para permitir visualização no navegador quando possível
        const contentDisposition = downloadResponse.headers.get('content-disposition') || `inline; filename="file"`

        return new NextResponse(blob, {
            headers: {
                'Content-Type': contentType,
                'Content-Disposition': contentDisposition,
                'Cache-Control': 'private, max-age=3600',
            },
        })
    } catch (error) {
        console.error('Erro ao fazer proxy do arquivo:', error)
        return NextResponse.json(
            {
                detail:
                    error instanceof Error
                        ? error.message
                        : 'Erro desconhecido ao obter arquivo',
            },
            { status: 500 }
        )
    }
}
