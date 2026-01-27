import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, errorResponse, requireToken } from '@/lib/backend-fetch'

/**
 * Handler Next.js para rejeitar convite
 *
 * Requer autenticação (cookie access_token).
 */
export async function POST(
    request: NextRequest,
    { params }: { params: { member_id: string } }
) {
    const memberId = parseInt(params.member_id)
    if (isNaN(memberId)) {
        return errorResponse('member_id inválido', 400)
    }

    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const result = await backendFetch(`/auth/invites/${memberId}/reject`, {
        method: 'POST',
        token: auth.token,
    })

    if (!result.ok) {
        return result.error
    }

    return NextResponse.json(result.data)
}
