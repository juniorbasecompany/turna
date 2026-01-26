import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/schedule/generate-from-demands
 *
 * Gera escala a partir de demandas da tabela demand.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/schedule/generate-from-demands`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      let errorData: { detail?: string } = {}
      try {
        errorData = await response.json()
      } catch {
        errorData = { detail: `Erro HTTP ${response.status}` }
      }
      
      // Melhorar mensagem de erro para 405 (Method Not Allowed)
      if (response.status === 405) {
        errorData.detail = `Método HTTP POST não permitido para o endpoint /schedule/generate-from-demands. ` +
          `Verifique se: (1) o endpoint está registrado no backend, (2) o método POST está habilitado, ` +
          `(3) não há conflito de rotas. Status: ${response.status}`
      }
      
      // Melhorar mensagem de erro para 404 (Not Found)
      if (response.status === 404) {
        errorData.detail = `Endpoint /schedule/generate-from-demands não encontrado. ` +
          `Verifique se o endpoint está registrado no backend e se a URL está correta. Status: ${response.status}`
      }
      
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Erro ao gerar escala a partir de demandas:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao gerar escala',
      },
      { status: 500 }
    )
  }
}
