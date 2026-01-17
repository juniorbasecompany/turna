import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/job/extract
 *
 * Cria um job de extração de demanda a partir de um file_id.
 * Retorna job_id para polling de status.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    if (!body.file_id) {
      return NextResponse.json(
        { detail: 'file_id é obrigatório' },
        { status: 400 }
      )
    }

    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Chamar backend
    const response = await fetch(`${API_URL}/job/extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify({ file_id: body.file_id }),
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
    console.error('Erro ao criar job:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao criar job',
      },
      { status: 500 }
    )
  }
}