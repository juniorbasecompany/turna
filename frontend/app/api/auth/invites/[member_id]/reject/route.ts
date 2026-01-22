import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para rejeitar convite
 *
 * Requer autenticação (cookie access_token).
 */
export async function POST(
    request: NextRequest,
    { params }: { params: { member_id: string } }
) {
    try {
        const memberId = parseInt(params.member_id)
        if (isNaN(memberId)) {
            return NextResponse.json(
                { detail: 'member_id inválido' },
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

        // Chamar backend
        const response = await fetch(`${API_URL}/auth/invites/${memberId}/reject`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Erro ao rejeitar convite:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
