import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/tenant/list
 *
 * Lista todos os tenants (apenas admin).
 */
export async function GET(request: NextRequest) {
  console.log('[TENANT-FRONTEND] Listando tenants')
  try {
    const accessToken = request.cookies.get('access_token')?.value

    const response = await fetch(`${API_URL}/tenant/list`, {
      method: 'GET',
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
      console.error('[TENANT-FRONTEND] ❌ FALHA - Erro ao listar tenants:', errorData)
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    console.log('[TENANT-FRONTEND] ✅ SUCESSO - Tenants listados com sucesso', data)
    return NextResponse.json(data)
  } catch (error) {
    console.error('[TENANT-FRONTEND] ❌ FALHA - Erro ao listar tenants:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao listar tenants',
      },
      { status: 500 }
    )
  }
}
