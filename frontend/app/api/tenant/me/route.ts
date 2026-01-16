import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para obter informações do tenant atual
 *
 * Chama GET /tenant/me no backend.
 * Requer autenticação via cookie httpOnly.
 */
export async function GET(request: NextRequest) {
    try {
        const token = request.cookies.get('access_token')?.value

        if (!token) {
            return NextResponse.json(
                { detail: 'Não autenticado' },
                { status: 401 }
            )
        }

        // Chamar backend com token no header
        const response = await fetch(`${API_URL}/tenant/me`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Erro ao obter informações do tenant:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
