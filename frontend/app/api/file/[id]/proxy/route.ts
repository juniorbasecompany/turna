import { NextRequest, NextResponse } from 'next/server'
import { errorResponse, requireToken } from '@/lib/backend-fetch'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/file/[id]/proxy
 *
 * Proxy para obter arquivo do MinIO e servir ao cliente.
 * Resolve o problema de URLs do MinIO não serem acessíveis do navegador.
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
        const downloadResponse = await fetch(`${API_URL}/file/${fileId}/download`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${auth.token}`,
            },
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
        
        const isConnectionError = error instanceof TypeError || 
            (error instanceof Error && error.message.includes('fetch'))
        
        return NextResponse.json(
            { detail: isConnectionError 
                ? 'Servidor indisponível. Verifique sua conexão e tente novamente.'
                : (error instanceof Error ? error.message : 'Erro desconhecido ao obter arquivo')
            },
            { status: isConnectionError ? 503 : 500 }
        )
    }
}
