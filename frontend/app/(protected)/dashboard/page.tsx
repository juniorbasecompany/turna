'use client'

import { LoadingSpinner } from '@/components/LoadingSpinner'
import { protectedFetch } from '@/lib/api'
import {
    DemandListResponse,
    FileListResponse,
    HospitalListResponse,
    JobListResponse,
    MemberListResponse,
} from '@/types/api'
import { useEffect, useState } from 'react'

export default function DashboardPage() {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [totals, setTotals] = useState({
        hospitals: 0,
        members: 0,
        demands: 0,
        files: 0,
        jobs: 0,
        jobsRunning: 0,
    })

    useEffect(() => {
        const loadTotals = async () => {
            try {
                setLoading(true)
                setError(null)

                // Carregar todos os totais em paralelo
                const [
                    hospitalsData,
                    membersData,
                    demandsData,
                    filesData,
                    jobsData,
                    jobsRunningData,
                ] = await Promise.all([
                    protectedFetch<HospitalListResponse>('/api/hospital/list'),
                    protectedFetch<MemberListResponse>('/api/member/list'),
                    protectedFetch<DemandListResponse>('/api/demand/list'),
                    protectedFetch<FileListResponse>('/api/file/list'),
                    protectedFetch<JobListResponse>('/api/job/list'),
                    protectedFetch<JobListResponse>('/api/job/list?status=RUNNING'),
                ])

                setTotals({
                    hospitals: hospitalsData.total,
                    members: membersData.total,
                    demands: demandsData.total,
                    files: filesData.total,
                    jobs: jobsData.total,
                    jobsRunning: jobsRunningData.total,
                })
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Erro ao carregar dados do dashboard'
                setError(message)
                console.error('Erro ao carregar dados do dashboard:', err)
            } finally {
                setLoading(false)
            }
        }

        loadTotals()
    }, [])

    return (
        <div className="p-8">
            {/* Cards de Indicadores */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="text-sm font-medium text-gray-600 mb-2">Total de Hospitais</div>
                    <div className="text-3xl font-semibold text-gray-900">
                        {loading ? <LoadingSpinner /> : totals.hospitals}
                    </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="text-sm font-medium text-gray-600 mb-2">Total de associados</div>
                    <div className="text-3xl font-semibold text-gray-900">
                        {loading ? <LoadingSpinner /> : totals.members}
                    </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="text-sm font-medium text-gray-600 mb-2">Total de Demandas</div>
                    <div className="text-3xl font-semibold text-gray-900">
                        {loading ? <LoadingSpinner /> : totals.demands}
                    </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="text-sm font-medium text-gray-600 mb-2">Total de Arquivos</div>
                    <div className="text-3xl font-semibold text-gray-900">
                        {loading ? <LoadingSpinner /> : totals.files}
                    </div>
                </div>
            </div>

            {/* Segunda linha de cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="text-sm font-medium text-gray-600 mb-2">Total de Jobs</div>
                    <div className="text-3xl font-semibold text-gray-900">
                        {loading ? <LoadingSpinner /> : totals.jobs}
                    </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="text-sm font-medium text-gray-600 mb-2">Jobs em Processamento</div>
                    <div className="text-3xl font-semibold text-yellow-600">
                        {loading ? <LoadingSpinner /> : totals.jobsRunning}
                    </div>
                </div>
            </div>

            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800">{error}</p>
                </div>
            )}

            {/* Tabela Principal */}
            <div className="bg-white rounded-lg border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">Atividades Recentes</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Arquivo
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Tipo
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Data
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            <tr className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    demandas1.pdf
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    Importação
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                                        Concluído
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    17/01/2026 00:45
                                </td>
                            </tr>
                            <tr className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    escala_janeiro.pdf
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    Escala
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                                        Publicado
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    16/01/2026 14:30
                                </td>
                            </tr>
                            <tr className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    demandas2.xlsx
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    Importação
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">
                                        Processando
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                    17/01/2026 01:15
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
