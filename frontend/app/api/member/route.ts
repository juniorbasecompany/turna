import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/member
 *
 * Cria um novo member (apenas admin).
 */
export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get('access_token')?.value
    const body = await request.json()

    // Validação básica: email é obrigatório se account_id não for fornecido
    if (!body.account_id && (!body.email || body.email.trim() === '')) {
      return NextResponse.json(
        { detail: 'email é obrigatório quando account_id não é fornecido' },
        { status: 400 }
      )
    }

    const response = await fetch(`${API_URL}/member`, {
      method: 'POST',
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
    console.log('[MEMBER-FRONTEND] ✅ SUCESSO - Member criado com sucesso', data)
    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao criar member',
      },
      { status: 500 }
    )
  }
}
