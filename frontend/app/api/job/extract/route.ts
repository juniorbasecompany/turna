import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, errorResponse, requireToken } from '@/lib/backend-fetch'

/**
 * POST /api/job/extract
 *
 * Cria um job de extração de demanda a partir de um file_id.
 * Retorna job_id para polling de status.
 */
export async function POST(request: NextRequest) {
    const body = await request.json()

    if (!body.file_id) {
        return errorResponse('file_id é obrigatório', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch('/job/extract', {
        method: 'POST',
        token: auth.token,
        body: { file_id: body.file_id },
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
