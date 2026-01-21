import { GoogleTokenRequest, TokenResponse } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para criação automática de tenant
 *
 * Recebe id_token do Google, chama backend POST /auth/google/create-tenant,
 * e atualiza cookie com novo JWT.
 */
export async function POST(request: NextRequest) {
    try {
        const body: GoogleTokenRequest = await request.json()

        if (!body.id_token) {
            return NextResponse.json(
                { detail: 'id_token é obrigatório' },
                { status: 400 }
            )
        }

        // Chamar backend
        const response = await fetch(`${API_URL}/auth/google/create-tenant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_token: body.id_token,
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
        console.error('Erro no handler de criação de tenant:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
