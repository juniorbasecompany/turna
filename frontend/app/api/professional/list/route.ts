import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/professional/list
 *
 * Lista todos os profissionais do tenant atual.
 */
export async function GET(request: NextRequest) {
  try {
    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Obter query params
    const { searchParams } = new URL(request.url)
    const params = new URLSearchParams()
    if (searchParams.get('q')) params.append('q', searchParams.get('q')!)
    if (searchParams.get('active')) params.append('active', searchParams.get('active')!)
    if (searchParams.get('limit')) params.append('limit', searchParams.get('limit')!)
    if (searchParams.get('offset')) params.append('offset', searchParams.get('offset')!)

    const queryString = params.toString()
    const url = `${API_URL}/professional/list${queryString ? `?${queryString}` : ''}`

    // Chamar backend
    const response = await fetch(url, {
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
    console.error('Erro ao listar profissionais:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao listar profissionais',
      },
      { status: 500 }
    )
  }
}
