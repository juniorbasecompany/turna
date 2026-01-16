import { TenantListResponse } from '@/types/api'
import { NextRequest, NextResponse } from 'next/server'
import { api } from '@/lib/api'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Handler Next.js para listar tenants disponíveis
 *
 * Chama GET /auth/tenant/list no backend.
 * Requer autenticação via cookie httpOnly.
 */
export async function GET(request: NextRequest) {
    try {
        // Chamar backend
        const response = await fetch(`${API_URL}/auth/tenant/list`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        })

        const data: TenantListResponse = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Erro no handler de listar tenants:', error)
        return NextResponse.json(
            { detail: 'Erro interno do servidor' },
            { status: 500 }
        )
    }
}
