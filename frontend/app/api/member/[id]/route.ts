import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/member/[id]
 *
 * Obtém detalhes de um member específico.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/member/${params.id}`, {
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
    console.error('Erro ao obter member:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao obter member',
      },
      { status: 500 }
    )
  }
}

/**
 * PUT /api/member/[id]
 *
 * Atualiza um member (apenas admin).
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const body = await request.json()
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/member/${params.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
      body: JSON.stringify(body),
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
    console.error('Erro ao atualizar member:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao atualizar member',
      },
      { status: 500 }
    )
  }
}

/**
 * DELETE /api/member/[id]
 *
 * Remove um member (apenas admin).
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/member/${params.id}`, {
      method: 'DELETE',
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

    return new NextResponse(null, { status: 204 })
  } catch (error) {
    console.error('Erro ao remover member:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao remover member',
      },
      { status: 500 }
    )
  }
}
