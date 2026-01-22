import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/tenant/[id]/invite
 *
 * Cria/atualiza um convite (Member PENDING) para um email no tenant (apenas admin).
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[INVITE-FRONTEND] Iniciando convite para tenant ID=${params.id}`)
  try {
    const accessToken = request.cookies.get('access_token')?.value
    const body = await request.json()

    const response = await fetch(`${API_URL}/tenant/${params.id}/invite`, {
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
      console.error(
        `[INVITE-FRONTEND] ❌ FALHA - Erro ao criar convite para tenant ID=${params.id}:`,
        errorData
      )
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    console.log(
      `[INVITE-FRONTEND] ✅ SUCESSO - Convite criado com sucesso para tenant ID=${params.id}`,
      data
    )
    return NextResponse.json(data)
  } catch (error) {
    console.error(
      `[INVITE-FRONTEND] ❌ FALHA - Erro ao criar convite para tenant ID=${params.id}:`,
      error
    )
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao criar convite',
      },
      { status: 500 }
    )
  }
}
