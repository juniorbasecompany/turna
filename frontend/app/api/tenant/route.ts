import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/tenant
 *
 * Cria um novo tenant (apenas admin).
 */
export async function POST(request: NextRequest) {
  console.log('[TENANT-FRONTEND] Criando novo tenant')
  try {
    const accessToken = request.cookies.get('access_token')?.value
    const body = await request.json()

    const response = await fetch(`${API_URL}/tenant`, {
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
      console.error('[TENANT-FRONTEND] ❌ FALHA - Erro ao criar tenant:', errorData)
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    console.log('[TENANT-FRONTEND] ✅ SUCESSO - Tenant criado com sucesso', data)
    return NextResponse.json(data)
  } catch (error) {
    console.error('[TENANT-FRONTEND] ❌ FALHA - Erro ao criar tenant:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao criar tenant',
      },
      { status: 500 }
    )
  }
}
