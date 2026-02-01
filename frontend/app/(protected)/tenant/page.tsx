'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterInput, FilterPanel } from '@/components/filter'
import { FormInput, FormSelect } from '@/components/form'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { Pagination } from '@/components/Pagination'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useEntityPage } from '@/hooks/useEntityPage'
import { useReportButton } from '@/hooks/useReportButton'
import { getCardTextClasses } from '@/lib/cardStyles'
import {
    TenantCreateRequest,
    TenantResponse,
    TenantUpdateRequest,
} from '@/types/api'
import { useMemo, useState } from 'react'

type TenantFormData = {
    name: string
    slug: string
    timezone: string
    locale: string
    currency: string
}

// Label do filtro: definido uma vez, usado no painel e no cabeçalho do relatório
const FILTER_NAME_LABEL = 'Nome'

export default function TenantPage() {
    const { settings } = useTenantSettings()
    const [filterName, setFilterName] = useState('')

    const listAndReportParams = useMemo(() => {
        if (!filterName.trim()) return undefined
        return { name: filterName.trim() }
    }, [filterName])

    const reportFilters = useMemo((): { label: string; value: string }[] => {
        if (!filterName.trim()) return []
        return [{ label: FILTER_NAME_LABEL, value: filterName.trim() }]
    }, [filterName])

    const initialFormData: TenantFormData = {
        name: '',
        slug: '',
        timezone: 'America/Sao_Paulo',
        locale: 'pt-BR',
        currency: 'BRL',
    }

    const {
        items: tenantList,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingTenant,
        isEditing,
        hasChanges,
        handleCreateClick,
        handleEditClick,
        handleCancel,
        selectedItems: selectedTenants,
        toggleSelection: toggleTenantSelection,
        toggleAll: toggleAllTenants,
        selectedCount: selectedTenantsCount,
        selectAllMode: selectAllTenantsMode,
        pagination,
        total,
        paginationHandlers,
        handleSave: baseHandleSave,
        handleDeleteSelected: baseHandleDeleteSelected,
        actionBarButtons,
        actionBarErrorProps,
    } = useEntityPage<TenantFormData, TenantResponse, TenantCreateRequest, TenantUpdateRequest>({
        endpoint: '/api/tenant',
        entityName: 'clínica',
        initialFormData,
        isEmptyCheck: (data) => {
            return (
                data.name.trim() === '' &&
                data.slug.trim() === '' &&
                data.timezone === 'America/Sao_Paulo' &&
                data.locale === 'pt-BR' &&
                data.currency === 'BRL'
            )
        },
        mapEntityToFormData: (tenant) => ({
            name: tenant.name,
            slug: tenant.slug,
            timezone: tenant.timezone,
            locale: tenant.locale,
            currency: tenant.currency,
        }),
        mapFormDataToCreateRequest: (formData) => ({
            name: formData.name.trim(),
            slug: formData.slug.trim(),
            timezone: formData.timezone,
            locale: formData.locale,
            currency: formData.currency,
        }),
        mapFormDataToUpdateRequest: (formData) => ({
            name: formData.name.trim(),
            slug: formData.slug.trim(),
            timezone: formData.timezone,
            locale: formData.locale,
            currency: formData.currency,
        }),
        validateFormData: (formData) => {
            if (!formData.name.trim()) {
                return 'Nome é obrigatório'
            }
            if (!formData.slug.trim()) {
                return 'Rótulo é obrigatório'
            }
            return null
        },
        onSaveSuccess: () => {
            // Notificar Header para atualizar lista de tenants
            window.dispatchEvent(new CustomEvent('tenant-list-updated'))
        },
        onDeleteSuccess: () => {
            window.dispatchEvent(new CustomEvent('tenant-list-updated'))
        },
        additionalListParams: listAndReportParams,
    })

    const { leftButtons: reportLeftButtons, reportError } = useReportButton({
        apiPath: '/api/tenant/report',
        params: listAndReportParams,
        reportFilters,
    })

    // Listagem já vem filtrada pelo backend quando listAndReportParams tem name
    const filteredTenants = tenantList

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Clínica" isEditing={isEditing}>
                <div className="space-y-4">
                    <FormFieldGrid>
                        <FormInput
                            label="Nome"
                            value={formData.name}
                            onChange={(value) => setFormData({ ...formData, name: value })}
                            id="name"
                            required
                            disabled={submitting}
                        />
                        <FormInput
                            label="Rótulo"
                            value={formData.slug}
                            onChange={(value) => setFormData({ ...formData, slug: value.toLowerCase().replace(/\s+/g, '-') })}
                            id="slug"
                            required
                            disabled={submitting}
                            helperText="Identificador único da clínica (usado na URL). Será convertido automaticamente para minúsculas e hífens."
                        />
                    </FormFieldGrid>
                    <FormFieldGrid>
                        <FormSelect
                            label="Fuso Horário"
                            value={formData.timezone}
                            onChange={(value) => setFormData({ ...formData, timezone: value || 'America/Sao_Paulo' })}
                            options={[
                                { value: 'America/Sao_Paulo', label: 'America/Sao_Paulo (Brasil)' },
                                { value: 'America/New_York', label: 'America/New_York (EUA - Leste)' },
                                { value: 'America/Los_Angeles', label: 'America/Los_Angeles (EUA - Oeste)' },
                                { value: 'Europe/London', label: 'Europe/London (Reino Unido)' },
                                { value: 'Europe/Paris', label: 'Europe/Paris (França)' },
                                { value: 'Asia/Tokyo', label: 'Asia/Tokyo (Japão)' },
                            ]}
                            id="timezone"
                            disabled={submitting}
                        />
                        <FormSelect
                            label="Localidade"
                            value={formData.locale}
                            onChange={(value) => setFormData({ ...formData, locale: value || 'pt-BR' })}
                            options={[
                                { value: 'pt-BR', label: 'pt-BR (Português - Brasil)' },
                                { value: 'en-US', label: 'en-US (English - US)' },
                                { value: 'es-ES', label: 'es-ES (Español - España)' },
                            ]}
                            id="locale"
                            disabled={submitting}
                        />
                        <FormSelect
                            label="Moeda"
                            value={formData.currency}
                            onChange={(value) => setFormData({ ...formData, currency: value || 'BRL' })}
                            options={[
                                { value: 'BRL', label: 'BRL (Real Brasileiro)' },
                                { value: 'USD', label: 'USD (Dólar Americano)' },
                                { value: 'EUR', label: 'EUR (Euro)' },
                                { value: 'GBP', label: 'GBP (Libra Esterlina)' },
                            ]}
                            id="currency"
                            disabled={submitting}
                        />
                    </FormFieldGrid>
                </div>
            </EditForm>

            <CardPanel
                title="Clínicas"
                description="Gerencie as clínicas (tenants) do sistema"
                totalCount={filteredTenants.length}
                selectedCount={selectedTenantsCount}
                loading={loading}
                loadingMessage="Carregando clínicas..."
                emptyMessage="Nenhuma clínica cadastrada ainda."
                createCard={
                    <CreateCard
                        label="Criar nova clínica"
                        subtitle="Clique para adicionar"
                        onClick={handleCreateClick}
                    />
                }
                filterContent={
                    !isEditing ? (
                        <FilterPanel>
                            <FilterInput
                                label={FILTER_NAME_LABEL}
                                value={filterName}
                                onChange={setFilterName}
                            />
                        </FilterPanel>
                    ) : undefined
                }
            >
                {filteredTenants.map((tenant) => {
                    const isSelected = selectedTenants.has(tenant.id)
                    return (
                        <EntityCard
                            key={tenant.id}
                            id={tenant.id}
                            isSelected={isSelected}
                            footer={
                                <CardFooter
                                    isSelected={isSelected}
                                    date={tenant.created_at}
                                    settings={settings}
                                    onToggleSelection={(e) => {
                                        e.stopPropagation()
                                        toggleTenantSelection(tenant.id)
                                    }}
                                    onEdit={() => handleEditClick(tenant)}
                                    disabled={deleting}
                                    deleteTitle={isSelected ? 'Desmarcar para exclusão' : 'Marcar para exclusão'}
                                    editTitle="Editar clínica"
                                />
                            }
                        >
                            {/* Corpo - Nome e informações */}
                            <div className="mb-3">
                                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-blue-50 border border-blue-200">
                                    <div className="flex flex-col items-center justify-center text-blue-600">
                                        <div className="w-16 h-16 sm:w-20 sm:h-20 mb-2">
                                            <svg
                                                className="w-full h-full"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                            </svg>
                                        </div>
                                        <h3
                                            className={`text-sm font-semibold text-center px-2 ${getCardTextClasses(isSelected)}`}
                                            title={tenant.name}
                                        >
                                            {tenant.name}
                                        </h3>
                                        <p className="text-xs text-gray-600 mt-1">{tenant.slug}</p>
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
                    selectedCount: selectedTenantsCount,
                    totalCount: filteredTenants.length,
                    grandTotal: total,
                    selectAllMode: selectAllTenantsMode,
                    onToggleAll: () => toggleAllTenants(filteredTenants.map((t) => t.id)),
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
                error={reportError ?? actionBarErrorProps.error}
                message={actionBarErrorProps.message}
                messageType={actionBarErrorProps.messageType}
                leftButtons={reportLeftButtons}
                buttons={actionBarButtons}
            />
        </>
    )
}
