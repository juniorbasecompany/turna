import { backendFetchPdf, requireToken } from '@/lib/backend-fetch'
import { NextRequest } from 'next/server'

/**
 * GET /api/hospital/report
 *
 * Relatório PDF: lista de hospitais (nome).
 */
export async function GET(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) return auth.error
    const { searchParams } = new URL(request.url)
    const params: Record<string, string> = {}
    searchParams.forEach((value, key) => {
        params[key] = value
    })
    return backendFetchPdf('/hospital/report', auth.token, params)
}
