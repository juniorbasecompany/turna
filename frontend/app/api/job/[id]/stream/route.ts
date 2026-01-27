import { NextRequest } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/job/[id]/stream
 *
 * Proxy SSE (Server-Sent Events) para aguardar conclusão de um job.
 * Faz streaming da resposta do backend para o cliente.
 * 
 * Nota: Esta rota não usa backendFetch pois precisa fazer streaming de dados.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const jobId = params.id

    if (!jobId) {
        return new Response(
            JSON.stringify({ detail: 'ID do job é obrigatório' }),
            { status: 400, headers: { 'Content-Type': 'application/json' } }
        )
    }

    const accessToken = request.cookies.get('access_token')?.value
    if (!accessToken) {
        return new Response(
            JSON.stringify({ detail: 'Não autenticado' }),
            { status: 401, headers: { 'Content-Type': 'application/json' } }
        )
    }

    try {
        const response = await fetch(`${API_URL}/job/${jobId}/stream`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Accept': 'text/event-stream',
            },
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                detail: `Erro HTTP ${response.status}`,
            }))
            return new Response(
                JSON.stringify(errorData),
                { status: response.status, headers: { 'Content-Type': 'application/json' } }
            )
        }

        if (!response.body) {
            return new Response(
                JSON.stringify({ detail: 'Stream não disponível' }),
                { status: 500, headers: { 'Content-Type': 'application/json' } }
            )
        }

        return new Response(response.body, {
            status: 200,
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        })
    } catch (error) {
        console.error('Erro ao conectar com SSE:', error)
        
        // Erro de conexão (backend indisponível)
        const isConnectionError = error instanceof TypeError || 
            (error instanceof Error && error.message.includes('fetch'))
        
        return new Response(
            JSON.stringify({
                detail: isConnectionError 
                    ? 'Servidor indisponível. Verifique sua conexão e tente novamente.'
                    : (error instanceof Error ? error.message : 'Erro desconhecido ao conectar com SSE'),
            }),
            { status: isConnectionError ? 503 : 500, headers: { 'Content-Type': 'application/json' } }
        )
    }
}
