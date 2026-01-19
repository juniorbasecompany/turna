import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/profile/list
 *
 * Lista todos os profiles do tenant atual.
 */
export async function GET(request: NextRequest) {
  try {
    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Obter query params para paginação
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '20'
    const offset = searchParams.get('offset') || '0'

    // Chamar backend
    const response = await fetch(`${API_URL}/profile/list?limit=${limit}&offset=${offset}`, {
      method: 'GET',
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : {},
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
    console.error('Erro ao listar profiles:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao listar profiles',
      },
      { status: 500 }
    )
  }
}
