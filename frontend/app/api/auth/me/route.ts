import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para verificar autenticação do usuário
 *
 * Lê o cookie access_token e verifica no backend se está válido.
 */
export async function GET(request: NextRequest) {
    try {
        const token = request.cookies.get('access_token')?.value

        if (!token) {
            return NextResponse.json(
                { authenticated: false },
                { status: 401 }
            )
        }

        // Chama o backend com o token no header
        const response = await fetch(`${API_URL}/me`, {
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        })

        if (response.ok) {
            const data = await response.json()
            return NextResponse.json({
                authenticated: true,
                account: data,
            })
        } else {
            return NextResponse.json(
                { authenticated: false },
                { status: 401 }
            )
        }
    } catch (error) {
        console.error('Erro ao verificar autenticação:', error)
        return NextResponse.json(
            { authenticated: false },
            { status: 500 }
        )
    }
}
