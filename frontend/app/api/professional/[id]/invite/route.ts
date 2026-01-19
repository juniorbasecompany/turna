import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/professional/[id]/invite
 *
 * Envia email de convite para um profissional se juntar à clínica (apenas admin).
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[INVITE-FRONTEND] Iniciando envio de convite para profissional ID=${params.id}`)
  try {
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/professional/${params.id}/invite`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `Erro HTTP ${response.status}`,
      }))
      console.error(
        `[INVITE-FRONTEND] ❌ FALHA - Erro ao enviar convite para profissional ID=${params.id}:`,
        errorData
      )
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    console.log(
      `[INVITE-FRONTEND] ✅ SUCESSO - Convite enviado com sucesso para profissional ID=${params.id}`,
      data
    )
    return NextResponse.json(data)
  } catch (error) {
    console.error(
      `[INVITE-FRONTEND] ❌ FALHA - Erro ao enviar convite para profissional ID=${params.id}:`,
      error
    )
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao enviar convite',
      },
      { status: 500 }
    )
  }
}
