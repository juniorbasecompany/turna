import { useCallback, useState } from 'react';

export type ReportParams = Record<string, string | number | boolean | null | undefined>

/** Lista de filtros para o cabeçalho do relatório: mesmo título e valor exibidos no painel. */
export type ReportFilterItem = { label: string; value: string }

/**
 * Monta query string: params (para a API filtrar os dados) e opcionalmente filters (JSON)
 * para o cabeçalho do PDF (título e valor como no painel, sem duplicar labels no backend).
 */
function buildReportQueryString(
    params: ReportParams | undefined,
    reportFilters: ReportFilterItem[] | undefined
): string {
    const search = new URLSearchParams()
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                search.append(key, String(value))
            }
        })
    }
    if (reportFilters && reportFilters.length > 0) {
        search.append('filters', JSON.stringify(reportFilters))
    }
    const qs = search.toString()
    return qs ? `?${qs}` : ''
}

/**
 * Hook para baixar/abrir relatório PDF no ActionBar.
 *
 * @param apiPath - Caminho da API do relatório (ex: '/api/tenant/report')
 * @param params - Parâmetros de filtro (mesmo objeto usado na listagem do painel)
 * @param reportFilters - Lista { label, value } para o cabeçalho do PDF; use os mesmos títulos e valores exibidos no painel (fonte única de verdade)
 */
export function useReportDownload(
    apiPath: string,
    params?: ReportParams,
    reportFilters?: ReportFilterItem[]
) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const downloadReport = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const queryString = buildReportQueryString(params, reportFilters)
            const url = `${apiPath}${queryString}`
            const response = await fetch(url, { credentials: 'include' })
            if (!response.ok) {
                const text = await response.text()
                let message = 'Erro ao gerar relatório'
                try {
                    const data = JSON.parse(text) as { detail?: string | unknown; error?: { message?: string } }
                    const d = data.detail ?? data.error?.message
                    if (typeof d === 'string') message = d
                    else if (Array.isArray(d) && d.length > 0) message = (d[0] as { msg?: string })?.msg ?? String(d[0])
                    else if (d != null) message = String(d)
                } catch {
                    if (text.length > 0) message = text.slice(0, 500)
                }
                if (message === 'Erro ao gerar relatório') {
                    message = text.length > 0 ? text.slice(0, 500) : `${message} (${response.status} ${response.statusText})`
                } else {
                    message = `Erro ao gerar relatório - ${message}`
                }
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
    }, [apiPath, params, reportFilters])

    return { downloadReport, reportLoading: loading, reportError: error }
}
