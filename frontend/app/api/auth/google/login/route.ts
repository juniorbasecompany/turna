import { AuthResponse, GoogleTokenRequest } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para login com Google
 *
 * Recebe id_token do frontend, chama backend POST /auth/google,
 * e grava JWT em cookie httpOnly.
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
        const response = await fetch(`${API_URL}/auth/google`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ id_token: body.id_token }),
        })

        const data: AuthResponse = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        // Se temos access_token, gravar em cookie httpOnly
        if (data.access_token) {
            const nextResponse = NextResponse.json(data)

            // Cookie httpOnly para segurança
            nextResponse.cookies.set('access_token', data.access_token, {
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'lax',
                maxAge: 60 * 60 * 24 * 7, // 7 dias
                path: '/',
            })

            return nextResponse
        }

        // Sem token (exige seleção de tenant)
        return NextResponse.json(data)
    } catch (error) {
        console.error('Erro no handler de login:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
