import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/job/list
 *
 * Lista todos os jobs do tenant atual.
 */
export async function GET(request: NextRequest) {
  try {
    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Obter query params
    const { searchParams } = new URL(request.url)
    const params = new URLSearchParams()
    if (searchParams.get('job_type')) params.append('job_type', searchParams.get('job_type')!)
    if (searchParams.get('status')) params.append('status', searchParams.get('status')!)
    if (searchParams.get('limit')) params.append('limit', searchParams.get('limit')!)
    if (searchParams.get('offset')) params.append('offset', searchParams.get('offset')!)

    const queryString = params.toString()
    const url = `${API_URL}/job/list${queryString ? `?${queryString}` : ''}`

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
    console.error('Erro ao listar jobs:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao listar jobs',
      },
      { status: 500 }
    )
  }
}
