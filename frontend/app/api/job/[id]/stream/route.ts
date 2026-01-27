import { NextRequest } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/job/[id]/stream
 *
 * Proxy SSE (Server-Sent Events) para aguardar conclusão de um job.
 * Faz streaming da resposta do backend para o cliente.
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

  // Obter access_token do cookie
  const accessToken = request.cookies.get('access_token')?.value

  try {
    // Chamar backend SSE
    const response = await fetch(`${API_URL}/job/${jobId}/stream`, {
      method: 'GET',
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
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

    // Verificar se o backend retornou um stream
    if (!response.body) {
      return new Response(
        JSON.stringify({ detail: 'Stream não disponível' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Retornar streaming response com headers SSE
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
    return new Response(
      JSON.stringify({
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao conectar com SSE',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
