import { GoogleSelectTenantRequest, TokenResponse } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para seleção de tenant
 *
 * Recebe id_token + tenant_id, chama backend POST /auth/google/select-tenant,
 * e atualiza cookie com novo JWT.
 */
export async function POST(request: NextRequest) {
    try {
        const body: GoogleSelectTenantRequest = await request.json()

        if (!body.id_token || !body.tenant_id) {
            return NextResponse.json(
                { detail: 'id_token e tenant_id são obrigatórios' },
                { status: 400 }
            )
        }

        // Chamar backend
        const response = await fetch(`${API_URL}/auth/google/select-tenant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_token: body.id_token,
                tenant_id: body.tenant_id,
            }),
        })

        const data: TokenResponse = await response.json()

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
        console.error('Erro no handler de seleção de tenant:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
