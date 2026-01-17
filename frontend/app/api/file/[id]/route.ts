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
  { params }: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    // Lidar com params síncrono (Next.js 13/14) ou assíncrono (Next.js 15+)
    const resolvedParams = params instanceof Promise ? await params : params
    const fileId = resolvedParams.id

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
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    // Lidar com params síncrono (Next.js 13/14) ou assíncrono (Next.js 15+)
    const resolvedParams = params instanceof Promise ? await params : params
    const fileId = resolvedParams.id

    if (!fileId) {
      return NextResponse.json(
        { detail: 'ID do arquivo é obrigatório' },
        { status: 400 }
      )
    }

    // Validar se fileId é um número válido
    const fileIdNum = parseInt(fileId, 10)
    if (isNaN(fileIdNum)) {
      return NextResponse.json(
        { detail: 'ID do arquivo deve ser um número válido' },
        { status: 400 }
      )
    }

    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Chamar backend
    const response = await fetch(`${API_URL}/file/${fileIdNum}`, {
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