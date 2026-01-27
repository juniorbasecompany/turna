import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, requireToken } from '@/lib/backend-fetch'

/**
 * Handler Next.js para verificar autenticação do usuário
 *
 * Lê o cookie access_token e verifica no backend se está válido.
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return NextResponse.json({ authenticated: false }, { status: 401 })
    }

    const result = await backendFetch<{ name: string; email: string }>('/me', {
        token: auth.token,
    })

    if (!result.ok) {
        // Erro de conexão ou backend indisponível → retornar não autenticado
        return NextResponse.json({ authenticated: false }, { status: 401 })
    }

    return NextResponse.json({
        authenticated: true,
        account: result.data,
    })
}
