import { NextRequest, NextResponse } from 'next/server'
import { errorResponse, requireToken } from '@/lib/backend-fetch'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/file/upload
 *
 * Faz upload de arquivo para o backend.
 * Retorna file_id para uso na criação de job.
 * 
 * Nota: Esta rota não usa backendFetch pois precisa enviar FormData.
 */
export async function POST(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
        return errorResponse('Arquivo não fornecido', 400)
    }

    const { searchParams } = new URL(request.url)
    const hospitalId = searchParams.get('hospital_id')

    if (!hospitalId) {
        return errorResponse('hospital_id é obrigatório', 400)
    }

    const backendFormData = new FormData()
    backendFormData.append('file', file)

    try {
        const response = await fetch(`${API_URL}/file/upload?hospital_id=${hospitalId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${auth.token}`,
            },
            body: backendFormData,
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
        
        const isConnectionError = error instanceof TypeError || 
            (error instanceof Error && error.message.includes('fetch'))
        
        return NextResponse.json(
            { detail: isConnectionError 
                ? 'Servidor indisponível. Verifique sua conexão e tente novamente.'
                : (error instanceof Error ? error.message : 'Erro desconhecido ao fazer upload')
            },
            { status: isConnectionError ? 503 : 500 }
        )
    }
}
