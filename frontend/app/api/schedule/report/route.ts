import { backendFetchPdf, requireToken } from '@/lib/backend-fetch'
import { NextRequest } from 'next/server'

/**
 * GET /api/schedule/report
 *
 * Relatório PDF: todas as escalas no período (formato escala_dia1), um dia por página.
 * Query opcional: start_time_from, start_time_to (ISO 8601 com timezone).
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) return auth.error
    const { searchParams } = new URL(request.url)
    const params: Record<string, string> = {}
    searchParams.forEach((value, key) => {
        params[key] = value
    })
    return backendFetchPdf('/schedule/report', auth.token, params)
}
