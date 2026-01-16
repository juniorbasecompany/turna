import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para trocar de tenant (quando já autenticado)
 *
 * Recebe tenant_id, chama backend POST /auth/switch-tenant,
 * e atualiza cookie com novo JWT.
 * Não requer id_token do Google - funciona apenas com cookie de autenticação.
 */
export async function POST(request: NextRequest) {
    try {
        const body = await request.json()

        if (!body.tenant_id) {
            return NextResponse.json(
                { detail: 'tenant_id é obrigatório' },
                { status: 400 }
            )
        }

        const token = request.cookies.get('access_token')?.value

        if (!token) {
            return NextResponse.json(
                { detail: 'Não autenticado' },
                { status: 401 }
            )
        }

        // Chamar backend com token no header
        const response = await fetch(`${API_URL}/auth/switch-tenant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                tenant_id: body.tenant_id,
            }),
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        // Atualizar cookie com novo JWT
        const nextResponse = NextResponse.json(data)

        nextResponse.cookies.set('access_token', data.access_token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            maxAge: 60 * 60 * 24 * 7, // 7 dias
            path: '/',
        })

        return nextResponse
    } catch (error) {
        console.error('Erro no handler de trocar tenant:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
