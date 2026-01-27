import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, errorResponse, requireToken } from '@/lib/backend-fetch'

/**
 * POST /api/member
 *
 * Cria um novo member (apenas admin).
 */
export async function POST(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json()

    // Validação básica: email é obrigatório se account_id não for fornecido
    if (!body.account_id && (!body.email || body.email.trim() === '')) {
        return errorResponse('email é obrigatório quando account_id não é fornecido', 400)
    }

    const result = await backendFetch('/member', {
        method: 'POST',
        token: auth.token,
        body,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
