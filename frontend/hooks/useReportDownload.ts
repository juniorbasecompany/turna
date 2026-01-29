import { useCallback, useState } from 'react'

export type ReportParams = Record<string, string | number | boolean | null | undefined>

/**
 * Monta query string a partir dos parâmetros do relatório (mesmos filtros do painel).
 */
function buildReportQueryString(params: ReportParams | undefined): string {
    if (!params || Object.keys(params).length === 0) return ''
    const search = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
            search.append(key, String(value))
        }
    })
    const qs = search.toString()
    return qs ? `?${qs}` : ''
}

/**
 * Hook para baixar/abrir relatório PDF no ActionBar.
 * Usa os mesmos parâmetros de filtro do painel para o relatório respeitar os filtros.
 *
 * @param apiPath - Caminho da API do relatório (ex: '/api/tenant/report')
 * @param params - Parâmetros de filtro (mesmo objeto usado na listagem do painel)
 */
export function useReportDownload(apiPath: string, params?: ReportParams) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const downloadReport = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const queryString = buildReportQueryString(params)
            const url = `${apiPath}${queryString}`
            const response = await fetch(url, { credentials: 'include' })
            if (!response.ok) {
                const data = await response.json().catch(() => ({}))
                const message = (data as { detail?: string }).detail ?? 'Erro ao gerar relatório'
                throw new Error(message)
            }
            const blob = await response.blob()
            const objectUrl = URL.createObjectURL(blob)
            window.open(objectUrl, '_blank')
            setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Erro ao gerar relatório')
        } finally {
            setLoading(false)
        }
    }, [apiPath, params])

    return { downloadReport, reportLoading: loading, reportError: error }
}
