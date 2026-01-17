import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/file/list
 *
 * Lista arquivos do tenant atual com paginação e filtros por período.
 */
export async function GET(request: NextRequest) {
  try {
    // Extrair query params
    const { searchParams } = new URL(request.url)
    const startAt = searchParams.get('start_at')
    const endAt = searchParams.get('end_at')
    const limit = searchParams.get('limit') || '20'
    const offset = searchParams.get('offset') || '0'

    // Construir URL do backend com query params
    const url = new URL(`${API_URL}/file/list`)
    if (startAt) url.searchParams.set('start_at', startAt)
    if (endAt) url.searchParams.set('end_at', endAt)
    url.searchParams.set('limit', limit)
    url.searchParams.set('offset', offset)

    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Chamar backend
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `Erro HTTP ${response.status}`,
      }))
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao listar arquivos:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao listar arquivos',
      },
      { status: 500 }
    )
  }
}