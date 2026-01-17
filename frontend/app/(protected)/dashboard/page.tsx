'use client'

export default function DashboardPage() {
  return (
    <div className="p-8">
      {/* Cards de Indicadores */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-600 mb-2">Importações Hoje</div>
          <div className="text-3xl font-semibold text-gray-900">12</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-600 mb-2">Escalas Ativas</div>
          <div className="text-3xl font-semibold text-gray-900">8</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-600 mb-2">Processando</div>
          <div className="text-3xl font-semibold text-gray-900">3</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-600 mb-2">Concluído Hoje</div>
          <div className="text-3xl font-semibold text-gray-900">9</div>
        </div>
      </div>

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
