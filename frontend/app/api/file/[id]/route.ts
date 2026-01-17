import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * GET /api/file/[id]
 *
 * Obtém informações do arquivo e URL presignada.
 * Para download, use /api/file/[id]/proxy
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fileId = params.id

    if (!fileId) {
      return NextResponse.json(
        { detail: 'ID do arquivo é obrigatório' },
        { status: 400 }
      )
    }

    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Chamar backend
    const response = await fetch(`${API_URL}/file/${fileId}`, {
      method: 'GET',
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
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
    console.error('Erro ao obter arquivo:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao obter arquivo',
      },
      { status: 500 }
    )
  }
}

/**
 * DELETE /api/file/[id]
 *
 * Deleta arquivo do backend e do S3/MinIO.
 * Apenas permite exclusão se o arquivo ainda não foi processado com sucesso.
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fileId = params.id

    if (!fileId) {
      return NextResponse.json(
        { detail: 'ID do arquivo é obrigatório' },
        { status: 400 }
      )
    }

    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Chamar backend
    const response = await fetch(`${API_URL}/file/${fileId}`, {
      method: 'DELETE',
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `Erro HTTP ${response.status}`,
      }))
      return NextResponse.json(errorData, { status: response.status })
    }

    // 204 No Content - retornar response vazia
    return new NextResponse(null, { status: 204 })
  } catch (error) {
    console.error('Erro ao deletar arquivo:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao deletar arquivo',
      },
      { status: 500 }
    )
  }
}