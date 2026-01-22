import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/membership
 *
 * Cria um novo membership (apenas admin).
 */
export async function POST(request: NextRequest) {
  console.log('[MEMBERSHIP-FRONTEND] Criando novo membership')
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

    const response = await fetch(`${API_URL}/membership`, {
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
      console.error('[MEMBERSHIP-FRONTEND] ❌ FALHA - Erro ao criar membership:', errorData)
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    console.log('[MEMBERSHIP-FRONTEND] ✅ SUCESSO - Membership criado com sucesso', data)
    return NextResponse.json(data)
  } catch (error) {
    console.error('[MEMBERSHIP-FRONTEND] ❌ FALHA - Erro ao criar membership:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao criar membership',
      },
      { status: 500 }
    )
  }
}
