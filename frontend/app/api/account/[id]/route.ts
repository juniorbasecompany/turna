import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * PUT /api/account/[id]
 *
 * Atualiza um account (apenas admin).
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[ACCOUNT-FRONTEND] Atualizando account ID=${params.id}`)
  try {
    const accessToken = request.cookies.get('access_token')?.value
    const body = await request.json()

    const response = await fetch(`${API_URL}/account/${params.id}`, {
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
      console.error(
        `[ACCOUNT-FRONTEND] ❌ FALHA - Erro ao atualizar account ID=${params.id}:`,
        errorData
      )
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    console.log(
      `[ACCOUNT-FRONTEND] ✅ SUCESSO - Account atualizado com sucesso ID=${params.id}`,
      data
    )
    return NextResponse.json(data)
  } catch (error) {
    console.error(
      `[ACCOUNT-FRONTEND] ❌ FALHA - Erro ao atualizar account ID=${params.id}:`,
      error
    )
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao atualizar account',
      },
      { status: 500 }
    )
  }
}

/**
 * DELETE /api/account/[id]
 *
 * Remove um account do tenant atual (apenas admin).
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  console.log(`[ACCOUNT-FRONTEND] Removendo account ID=${params.id}`)
  try {
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/account/${params.id}`, {
      method: 'DELETE',
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
        `[ACCOUNT-FRONTEND] ❌ FALHA - Erro ao remover account ID=${params.id}:`,
        errorData
      )
      return NextResponse.json(errorData, { status: response.status })
    }

    console.log(
      `[ACCOUNT-FRONTEND] ✅ SUCESSO - Account removido com sucesso ID=${params.id}`
    )
    return new NextResponse(null, { status: 204 })
  } catch (error) {
    console.error(
      `[ACCOUNT-FRONTEND] ❌ FALHA - Erro ao remover account ID=${params.id}:`,
      error
    )
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao remover account',
      },
      { status: 500 }
    )
  }
}
