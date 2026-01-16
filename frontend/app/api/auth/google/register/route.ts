import { AuthResponse, GoogleTokenRequest } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para cadastro com Google
 *
 * Recebe id_token do frontend, chama backend POST /auth/google/register,
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
        const response = await fetch(`${API_URL}/auth/google/register`, {
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

        // Verificar requires_tenant_selection PRIMEIRO
        // Se exige seleção de tenant, retornar resposta sem gravar cookie
        if (data.requires_tenant_selection) {
            return NextResponse.json(data)
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

        // Sem token e sem requires_tenant_selection (resposta inesperada)
        return NextResponse.json(data)
    } catch (error) {
        console.error('Erro no handler de cadastro:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
