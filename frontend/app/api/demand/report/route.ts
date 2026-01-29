import { backendFetchPdf, requireToken } from '@/lib/backend-fetch'
import { NextRequest } from 'next/server'

/**
 * GET /api/demand/report
 *
 * Relatório PDF: grade de demandas por hospital e horário, um dia por página.
 * Query opcional: start_at, end_at (ISO 8601 com timezone).
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) return auth.error
    const { searchParams } = new URL(request.url)
    const params: Record<string, string> = {}
    searchParams.forEach((value, key) => {
        params[key] = value
    })
    return backendFetchPdf('/demand/report', auth.token, params)
}
