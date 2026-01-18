import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/demand/list
 *
 * Lista demandas do tenant atual, com filtros opcionais e paginação.
 */
export async function GET(request: NextRequest) {
  try {
    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Obter query params
    const { searchParams } = new URL(request.url)
    const params = new URLSearchParams()

    // Passar todos os query params para o backend
    searchParams.forEach((value, key) => {
      params.append(key, value)
    })

    const queryString = params.toString()
    const url = `${API_URL}/demand/list${queryString ? `?${queryString}` : ''}`

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
    console.error('Erro ao listar demandas:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao listar demandas',
      },
      { status: 500 }
    )
  }
}
