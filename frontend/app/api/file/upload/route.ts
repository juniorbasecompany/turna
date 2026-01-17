import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/file/upload
 *
 * Faz upload de arquivo para o backend.
 * Retorna file_id para uso na criação de job.
 */
export async function POST(request: NextRequest) {
  try {
    // Obter o arquivo do FormData
    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json(
        { detail: 'Arquivo não fornecido' },
        { status: 400 }
      )
    }

    // Obter hospital_id da query string
    const { searchParams } = new URL(request.url)
    const hospitalId = searchParams.get('hospital_id')

    if (!hospitalId) {
      return NextResponse.json(
        { detail: 'hospital_id é obrigatório' },
        { status: 400 }
      )
    }

    // Criar FormData para enviar ao backend
    const backendFormData = new FormData()
    backendFormData.append('file', file)

    // Obter access_token do cookie
    const accessToken = request.cookies.get('access_token')?.value

    // Chamar backend com hospital_id na query string
    const response = await fetch(`${API_URL}/file/upload?hospital_id=${hospitalId}`, {
      method: 'POST',
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : {},
      body: backendFormData,
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
    console.error('Erro ao fazer upload:', error)
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : 'Erro desconhecido ao fazer upload',
      },
      { status: 500 }
    )
  }
}