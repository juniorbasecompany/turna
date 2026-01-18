'use client'

import { useState, useEffect } from 'react'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { formatDateTime } from '@/lib/tenantFormat'
import { BottomActionBar, BottomActionBarSpacer } from '@/components/BottomActionBar'
import {
  HospitalResponse,
  HospitalListResponse,
  HospitalCreateRequest,
  HospitalUpdateRequest,
} from '@/types/api'

export default function HospitalPage() {
  const { settings } = useTenantSettings()
  const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingHospital, setEditingHospital] = useState<HospitalResponse | null>(null)
  const [formData, setFormData] = useState({ name: '', prompt: '' })
  const [submitting, setSubmitting] = useState(false)
  const [selectedHospitals, setSelectedHospitals] = useState<Set<number>>(new Set())
  const [deleting, setDeleting] = useState(false)

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
    setFormData({ name: hospital.name, prompt: hospital.prompt || '' })
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

    if (!formData.name.trim()) {
      setError('Nome é obrigatório')
      return
    }

    try {
      setSubmitting(true)
      setError(null)

      if (editingHospital) {
        // Editar hospital existente
        const updateData: HospitalUpdateRequest = {
          name: formData.name.trim(),
          prompt: formData.prompt ? formData.prompt.trim() || null : null,
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
          prompt: formData.prompt ? formData.prompt.trim() || null : null,
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

  // Toggle seleção de hospital para exclusão
  const toggleHospitalSelection = (hospitalId: number) => {
    setSelectedHospitals((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(hospitalId)) {
        newSet.delete(hospitalId)
      } else {
        newSet.add(hospitalId)
      }
      return newSet
    })
  }

  // Deletar hospitais selecionados
  const handleDeleteSelected = async () => {
    if (selectedHospitals.size === 0) return

    setDeleting(true)
    setError(null)

    try {
      // Deletar todos os hospitais selecionados em paralelo
      const deletePromises = Array.from(selectedHospitals).map(async (hospitalId) => {
        const response = await fetch(`/api/hospital/${hospitalId}`, {
          method: 'DELETE',
          credentials: 'include',
        })

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Sessão expirada. Por favor, faça login novamente.')
          }
          const errorData = await response.json().catch(() => ({
            detail: `Erro HTTP ${response.status}`,
          }))
          throw new Error(errorData.detail || `Erro HTTP ${response.status}`)
        }

        return hospitalId
      })

      await Promise.all(deletePromises)

      // Remover hospitais deletados da lista
      setHospitals(hospitals.filter((hospital) => !selectedHospitals.has(hospital.id)))
      setSelectedHospitals(new Set())
      
      // Recarregar lista para garantir sincronização
      await loadHospitals()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Erro ao deletar hospitais. Tente novamente.'
      )
    } finally {
      setDeleting(false)
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {hospitals.map((hospital) => {
            const isSelected = selectedHospitals.has(hospital.id)
            return (
            <div
              key={hospital.id}
              className={`group rounded-xl border p-4 min-w-0 transition-all duration-200 ${
                isSelected
                  ? 'border-red-300 ring-2 ring-red-200 bg-red-50'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              {/* 1. Corpo - Ícone de hospital e nome */}
              <div className="mb-3">
                <div className="h-40 sm:h-48 bg-slate-50 rounded-lg flex items-center justify-center">
                  <div className="flex flex-col items-center justify-center text-blue-500">
                    <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                      <svg
                        className="w-full h-full"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                        />
                      </svg>
                    </div>
                    <h3
                      className={`text-sm font-semibold text-center px-2 ${
                        isSelected ? 'text-red-900' : 'text-gray-900'
                      }`}
                      title={hospital.name}
                    >
                      {hospital.name}
                    </h3>
                  </div>
                </div>
              </div>

              {/* 3. Rodapé - Metadados e ações */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex flex-col min-w-0 flex-1">
                  <span className={`text-sm truncate ${isSelected ? 'text-red-900' : 'text-slate-500'}`}>
                    {settings
                      ? formatDateTime(hospital.created_at, settings)
                      : new Date(hospital.created_at).toLocaleDateString('pt-BR', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                        })}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {/* Ícone para exclusão */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleHospitalSelection(hospital.id)
                    }}
                    disabled={deleting}
                    className={`shrink-0 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                      isSelected
                        ? 'text-red-700 bg-red-100 opacity-100'
                        : 'text-gray-400'
                    }`}
                    title={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleEditClick(hospital)}
                    className="shrink-0 px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-all duration-200"
                  >
                    Editar
                  </button>
                </div>
              </div>
            </div>
          )
          })}
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
                    Prompt
                  </label>
                  <p className="text-xs text-gray-500 mb-2">
                    O prompt influencia como a IA extrai as demandas dos arquivos deste hospital.
                  </p>
                  <textarea
                    id="prompt"
                    value={formData.prompt || ''}
                    onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                    rows={15}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
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
                  {submitting ? 'Salvando...' : editingHospital ? 'Salvar' : 'Criar Hospital'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
      <BottomActionBarSpacer />

      {/* Barra inferior fixa com ações */}
      <BottomActionBar
        leftContent={
          <div className="text-sm text-gray-600">
            Total de hospitais: <span className="font-medium">{hospitals.length}</span>
            {selectedHospitals.size > 0 && (
              <span className="ml-2 sm:ml-4 text-red-600">
                {selectedHospitals.size} marcado{selectedHospitals.size > 1 ? 's' : ''} para exclusão
              </span>
            )}
          </div>
        }
        buttons={(() => {
          const buttons = []
          // Adicionar botão "Excluir" se houver hospitais marcados para exclusão
          if (selectedHospitals.size > 0) {
            buttons.push({
              label: 'Excluir',
              onClick: handleDeleteSelected,
              variant: 'primary' as const,
              disabled: deleting,
              loading: deleting,
            })
          }
          return buttons
        })()}
      />
    </div>
  )
}
