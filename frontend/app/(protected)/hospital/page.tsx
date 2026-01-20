'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { ColorPicker } from '@/components/ColorPicker'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { getCardContainerClasses } from '@/lib/cardStyles'
import {
    HospitalCreateRequest,
    HospitalResponse,
    HospitalUpdateRequest,
} from '@/types/api'
import { useEntityPage } from '@/hooks/useEntityPage'

type HospitalFormData = {
    name: string
    prompt: string
    color: string | null
}

export default function HospitalPage() {
    const { settings } = useTenantSettings()

    const initialFormData: HospitalFormData = { name: '', prompt: '', color: null }

    const {
        items: hospitals,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingHospital,
        isEditing,
        hasChanges,
        handleCreateClick,
        handleEditClick,
        handleCancel,
        selectedItems: selectedHospitals,
        toggleSelection: toggleHospitalSelection,
        selectedCount: selectedHospitalsCount,
        pagination,
        total,
        paginationHandlers,
        handleSave,
        handleDeleteSelected,
        actionBarButtons,
        actionBarErrorProps,
    } = useEntityPage<HospitalFormData, HospitalResponse, HospitalCreateRequest, HospitalUpdateRequest>({
        endpoint: '/api/hospital',
        entityName: 'hospital',
        initialFormData,
        isEmptyCheck: (data) => {
            return data.name.trim() === '' && (data.prompt || '').trim() === '' && data.color === null
        },
        mapEntityToFormData: (hospital) => ({
            name: hospital.name,
            prompt: hospital.prompt || '',
            color: hospital.color || null,
        }),
        mapFormDataToCreateRequest: (formData) => ({
            name: formData.name.trim(),
            prompt: formData.prompt ? formData.prompt.trim() || undefined : undefined,
            color: formData.color || undefined,
        }),
        mapFormDataToUpdateRequest: (formData) => ({
            name: formData.name.trim(),
            prompt: formData.prompt ? formData.prompt.trim() : undefined,
            color: formData.color || null,
        }),
        validateFormData: (formData) => {
            if (!formData.name.trim()) {
                return 'Nome é obrigatório'
            }
            return null
        },
    })

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Hospital" isEditing={isEditing}>
                <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row gap-4 items-start">
                        <div className="flex-1 min-w-0">
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
                        <div className="flex-shrink-0">
                            <ColorPicker
                                value={formData.color}
                                onChange={(color) => setFormData({ ...formData, color })}
                                label="Cor"
                                disabled={submitting}
                            />
                        </div>
                    </div>
                    <div>
                        <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
                            Como os arquivos devem ser lidos?
                        </label>
                        <textarea
                            id="prompt"
                            value={formData.prompt || ''}
                            onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                            rows={15}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                            disabled={submitting}
                        />
                        <p className="mt-1 text-xs text-gray-500">
                            Escreva o prompt com as instruções para a IA extrair as demandas dos arquivos deste hospital.
                        </p>
                    </div>
                </div>
            </EditForm>

            <CardPanel
                title="Hospitais"
                description="Gerencie os hospitais e seus prompts de extração"
                totalCount={hospitals.length}
                selectedCount={selectedHospitals.size}
                loading={loading}
                loadingMessage="Carregando hospitais..."
                emptyMessage="Nenhum hospital cadastrado ainda."
                createCard={
                    <CreateCard
                        label="Criar novo hospital"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
            >
                {hospitals.map((hospital) => {
                            const isSelected = selectedHospitals.has(hospital.id)
                            return (
                                <div
                                    key={hospital.id}
                                    className={getCardContainerClasses(isSelected)}
                                >
                                    {/* 1. Corpo - Ícone de hospital e nome */}
                                    <div className="mb-3">
                                        <div
                                            className="h-40 sm:h-48 rounded-lg flex items-center justify-center"
                                            style={{
                                                backgroundColor: hospital.color || '#f1f5f9',
                                            }}
                                        >
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
                                                    className={`text-sm font-semibold text-center px-2 ${isSelected ? 'text-red-900' : 'text-gray-900'
                                                        }`}
                                                    title={hospital.name}
                                                >
                                                    {hospital.name}
                                                </h3>
                                            </div>
                                        </div>
                                    </div>

                                    {/* 3. Rodapé - Metadados e ações */}
                                    <CardFooter
                                        isSelected={isSelected}
                                        date={hospital.created_at}
                                        settings={settings}
                                        onToggleSelection={(e) => {
                                            e.stopPropagation()
                                            toggleHospitalSelection(hospital.id)
                                        }}
                                        onEdit={() => handleEditClick(hospital)}
                                        disabled={deleting}
                                        deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                        editTitle="Editar hospital"
                                    />
                                </div>
                            )
                        })}
            </CardPanel>

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <ActionBarSpacer />

            {/* Barra inferior fixa com ações */}
            <ActionBar
                pagination={
                    total > 0 ? (
                        <Pagination
                            offset={pagination.offset}
                            limit={pagination.limit}
                            total={total}
                            onFirst={paginationHandlers.onFirst}
                            onPrevious={paginationHandlers.onPrevious}
                            onNext={paginationHandlers.onNext}
                            onLast={paginationHandlers.onLast}
                            disabled={loading}
                        />
                    ) : undefined
                }
                error={actionBarErrorProps.error}
                message={actionBarErrorProps.message}
                messageType={actionBarErrorProps.messageType}
                buttons={actionBarButtons}
            />
        </>
    )
}
