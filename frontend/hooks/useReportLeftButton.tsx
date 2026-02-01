import { useMemo } from 'react'
import type { ActionBarButton } from '@/components/ActionBar'
import { ReportIcon } from '@/components/icons/ReportIcon'
import {
    useReportDownload,
    type ReportFilterItem,
    type ReportParams,
} from './useReportDownload'

export interface UseReportLeftButtonOptions {
    /** Caminho da API do relatório (ex: '/api/tenant/report') */
    apiPath: string
    /** Parâmetros de filtro para o relatório */
    params?: ReportParams
    /** Filtros para o cabeçalho do PDF */
    reportFilters?: ReportFilterItem[]
    /** Se false, o botão não é exibido (ex: quando isEditing no Schedule) */
    visible?: boolean
}

/**
 * Hook que encapsula a lógica do botão de relatório no ActionBar.
 * Retorna leftButtons e reportError para uso direto no ActionBar.
 *
 * O painel só precisa passar a config (endpoint, params, filters, visible).
 */
export function useReportLeftButton({
    apiPath,
    params,
    reportFilters,
    visible = true,
}: UseReportLeftButtonOptions): { leftButtons: ActionBarButton[]; reportError: string | null } {
    const { downloadReport, reportLoading, reportError } = useReportDownload(
        apiPath,
        params,
        reportFilters
    )

    const leftButtons = useMemo<ActionBarButton[]>(() => {
        if (!visible) return []
        return [
            {
                icon: <ReportIcon />,
                title: 'Relatório',
                onClick: downloadReport,
                variant: 'primary',
                disabled: reportLoading,
                loading: reportLoading,
            },
        ]
    }, [visible, downloadReport, reportLoading])

    return { leftButtons, reportError }
}
