'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { ColorPicker } from '@/components/ColorPicker'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterPanel } from '@/components/FilterPanel'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useMemo, useState } from 'react'
import {
    HospitalCreateRequest,
    HospitalResponse,
    HospitalUpdateRequest,
} from '@/types/api'
import { useEntityPage } from '@/hooks/useEntityPage'
import { getCardTextClasses } from '@/lib/cardStyles'

type HospitalFormData = {
    name: string
    prompt: string
    color: string | null
}

export default function HospitalPage() {
    const { settings } = useTenantSettings()
    const [nameFilter, setNameFilter] = useState('')

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
        toggleAll: toggleAllHospitals,
        selectedCount: selectedHospitalsCount,
        selectAllMode: selectAllHospitalsMode,
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

    // Filtrar hospitais por nome
    const filteredHospitals = useMemo(() => {
        if (!nameFilter.trim()) {
            return hospitals
        }
        const filterLower = nameFilter.toLowerCase().trim()
        return hospitals.filter((hospital) => hospital.name.toLowerCase().includes(filterLower))
    }, [hospitals, nameFilter])

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Hospital" isEditing={isEditing}>
                <div className="space-y-4">
                    <FormFieldGrid cols={1} smCols={2} gap={4}>
                        <FormField label="Nome" required>
                            <input
                                type="text"
                                id="name"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                required
                                disabled={submitting}
                            />
                        </FormField>
                        <FormField label="Cor">
                            <ColorPicker
                                value={formData.color}
                                onChange={(color) => setFormData({ ...formData, color })}
                                label=""
                                disabled={submitting}
                            />
                        </FormField>
                    </FormFieldGrid>
                    <FormField
                        label="Como os arquivos devem ser lidos?"
                        helperText="Escreva o prompt com as instruções para a IA extrair as demandas dos arquivos deste hospital."
                    >
                        <textarea
                            id="prompt"
                            value={formData.prompt || ''}
                            onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                            rows={15}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                            disabled={submitting}
                        />
                    </FormField>
                </div>
            </EditForm>

            <CardPanel
                title="Hospitais"
                description="Gerencie os hospitais e seus prompts de extração"
                totalCount={filteredHospitals.length}
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
                filterContent={
                    !isEditing ? (
                        <FilterPanel>
                            <FormField label="Nome">
                                <input
                                    type="text"
                                    value={nameFilter}
                                    onChange={(e) => setNameFilter(e.target.value)}
                                    placeholder="Filtrar por nome..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                />
                            </FormField>
                        </FilterPanel>
                    ) : undefined
                }
            >
                {filteredHospitals.map((hospital) => {
                    const isSelected = selectedHospitals.has(hospital.id)
                    return (
                        <EntityCard
                            key={hospital.id}
                            id={hospital.id}
                            isSelected={isSelected}
                            footer={
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
                            }
                        >
                            {/* Corpo - Ícone de hospital e nome */}
                            <div className="mb-3">
                                <div
                                    className="h-40 sm:h-48 rounded-lg flex items-center justify-center border border-blue-200"
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
                                            className={`text-sm font-semibold text-center px-2 ${getCardTextClasses(isSelected)}`}
                                            title={hospital.name}
                                        >
                                            {hospital.name}
                                        </h3>
                                    </div>
                                </div>
                            </div>
                        </EntityCard>
                    )
                })}
            </CardPanel>

            {/* Spacer para evitar que conteúdo fique escondido atrás da barra */}
            <ActionBarSpacer />

            {/* Barra inferior fixa com ações */}
            <ActionBar
                selection={{
                    selectedCount: selectedHospitalsCount,
                    totalCount: filteredHospitals.length,
                    grandTotal: total,
                    selectAllMode: selectAllHospitalsMode,
                    onToggleAll: () => toggleAllHospitals(filteredHospitals.map((h) => h.id)),
                }}
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
