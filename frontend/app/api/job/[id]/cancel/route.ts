import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * POST /api/job/[id]/cancel
 *
 * Cancela um job, mudando seu status para FAILED.
 */
export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        // Obter access_token do cookie
        const accessToken = request.cookies.get('access_token')?.value

        const jobId = params.id
        const url = `${API_URL}/job/${jobId}/cancel`

        // Chamar backend
        const response = await fetch(url, {
            method: 'POST',
            headers: accessToken
                ? {
                      Authorization: `Bearer ${accessToken}`,
                  }
                : {},
            credentials: 'include',
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                detail: `Erro HTTP ${response.status}`,
            }))
            return NextResponse.json(errorData, { status: response.status })
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error('Erro ao cancelar job:', error)
        return NextResponse.json(
            {
                detail:
                    error instanceof Error
                        ? error.message
                        : 'Erro desconhecido ao cancelar job',
            },
            { status: 500 }
        )
    }
}
