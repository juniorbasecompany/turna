'use client'

import { useState, useEffect } from 'react'
import {
  HospitalResponse,
  HospitalListResponse,
  HospitalCreateRequest,
  HospitalUpdateRequest,
} from '@/types/api'

export default function HospitalPage() {
  const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingHospital, setEditingHospital] = useState<HospitalResponse | null>(null)
  const [formData, setFormData] = useState({ name: '', prompt: '' })
  const [submitting, setSubmitting] = useState(false)

  // Carregar lista de hospitais
  const loadHospitals = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('/api/hospital/list', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
      }

      const data: HospitalListResponse = await response.json()
      setHospitals(data.items)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao carregar hospitais'
      setError(message)
      console.error('Erro ao carregar hospitais:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHospitals()
  }, [])

  // Abrir modal de criação
  const handleCreateClick = () => {
    setFormData({ name: '', prompt: '' })
    setEditingHospital(null)
    setShowCreateModal(true)
  }

  // Abrir modal de edição
  const handleEditClick = (hospital: HospitalResponse) => {
    setFormData({ name: hospital.name, prompt: hospital.prompt })
    setEditingHospital(hospital)
    setShowCreateModal(true)
  }

  // Fechar modal
  const handleCloseModal = () => {
    setShowCreateModal(false)
    setEditingHospital(null)
    setFormData({ name: '', prompt: '' })
  }

  // Submeter formulário (criar ou editar)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim() || !formData.prompt.trim()) {
      setError('Nome e prompt são obrigatórios')
      return
    }

    try {
      setSubmitting(true)
      setError(null)

      if (editingHospital) {
        // Editar hospital existente
        const updateData: HospitalUpdateRequest = {
          name: formData.name.trim(),
          prompt: formData.prompt.trim(),
        }

        const response = await fetch(`/api/hospital/${editingHospital.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(updateData),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
        }
      } else {
        // Criar novo hospital
        const createData: HospitalCreateRequest = {
          name: formData.name.trim(),
          prompt: formData.prompt.trim(),
        }

        const response = await fetch('/api/hospital', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(createData),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
        }
      }

      // Recarregar lista e fechar modal
      await loadHospitals()
      handleCloseModal()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao salvar hospital'
      setError(message)
      console.error('Erro ao salvar hospital:', err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 min-w-0">
      <div className="mb-4 sm:mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">Hospitais</h1>
          <p className="mt-1 text-sm text-gray-600">
            Gerencie os hospitais e seus prompts de extração
          </p>
        </div>
        <button
          onClick={handleCreateClick}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          Criar Hospital
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-800 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-2 text-sm text-gray-600">Carregando hospitais...</p>
        </div>
      ) : hospitals.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-600">Nenhum hospital cadastrado ainda.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nome
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Criado em
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {hospitals.map((hospital) => (
                  <tr key={hospital.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{hospital.name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600">
                        {new Date(hospital.created_at).toLocaleDateString('pt-BR', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                        })}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleEditClick(hospital)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal de criação/edição */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingHospital ? 'Editar Hospital' : 'Criar Hospital'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
              <div className="px-6 py-4 space-y-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                    Nome <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    required
                    disabled={submitting}
                  />
                </div>
                <div>
                  <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
                    Prompt <span className="text-red-500">*</span>
                  </label>
                  <p className="text-xs text-gray-500 mb-2">
                    O prompt influencia como a IA extrai as demandas dos arquivos deste hospital.
                  </p>
                  <textarea
                    id="prompt"
                    value={formData.prompt}
                    onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                    rows={15}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    required
                    disabled={submitting}
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? 'Salvando...' : editingHospital ? 'Salvar Alterações' : 'Criar Hospital'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
