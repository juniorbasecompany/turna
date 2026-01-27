'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { EntityCard } from '@/components/EntityCard'
import { FilterPanel } from '@/components/FilterPanel'
import { Pagination } from '@/components/Pagination'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { useMemo, useState } from 'react'
import {
    TenantCreateRequest,
    TenantResponse,
    TenantUpdateRequest,
} from '@/types/api'
import { useEntityPage } from '@/hooks/useEntityPage'
import { getCardTextClasses } from '@/lib/cardStyles'

type TenantFormData = {
    name: string
    slug: string
    timezone: string
    locale: string
    currency: string
}

export default function TenantPage() {
    const { settings } = useTenantSettings()
    const [nameFilter, setNameFilter] = useState('')

    const initialFormData: TenantFormData = {
        name: '',
        slug: '',
        timezone: 'America/Sao_Paulo',
        locale: 'pt-BR',
        currency: 'BRL',
    }

    const {
        items: tenants,
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
                return 'Slug é obrigatório'
            }
            return null
        },
        onSaveSuccess: () => {
            // Notificar Header para atualizar lista de tenants
            window.dispatchEvent(new CustomEvent('tenant-list-updated'))
        },
        onDeleteSuccess: () => {
            // Notificar Header para atualizar lista de tenants
            window.dispatchEvent(new CustomEvent('tenant-list-updated'))
        },
    })

    // Filtrar tenants por nome
    const filteredTenants = useMemo(() => {
        if (!nameFilter.trim()) {
            return tenants
        }
        const filterLower = nameFilter.toLowerCase().trim()
        return tenants.filter((tenant) => tenant.name.toLowerCase().includes(filterLower))
    }, [tenants, nameFilter])

    return (
        <>
            {/* Área de edição */}
            <EditForm title="Clínica" isEditing={isEditing}>
                <div className="space-y-4">
                    <FormFieldGrid>
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
                        <FormField label="Slug" required>
                            <input
                                type="text"
                                id="slug"
                                value={formData.slug}
                                onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                required
                                disabled={submitting}
                            />
                            <p className="mt-1 text-xs text-gray-500">
                                Identificador único da clínica (usado na URL). Será convertido automaticamente para minúsculas e hífens.
                            </p>
                        </FormField>
                    </FormFieldGrid>
                    <FormFieldGrid>
                        <FormField label="Fuso Horário">
                            <select
                                id="timezone"
                                value={formData.timezone}
                                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            >
                                <option value="America/Sao_Paulo">America/Sao_Paulo (Brasil)</option>
                                <option value="America/New_York">America/New_York (EUA - Leste)</option>
                                <option value="America/Los_Angeles">America/Los_Angeles (EUA - Oeste)</option>
                                <option value="Europe/London">Europe/London (Reino Unido)</option>
                                <option value="Europe/Paris">Europe/Paris (França)</option>
                                <option value="Asia/Tokyo">Asia/Tokyo (Japão)</option>
                            </select>
                        </FormField>
                        <FormField label="Localidade">
                            <select
                                id="locale"
                                value={formData.locale}
                                onChange={(e) => setFormData({ ...formData, locale: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            >
                                <option value="pt-BR">pt-BR (Português - Brasil)</option>
                                <option value="en-US">en-US (English - US)</option>
                                <option value="es-ES">es-ES (Español - España)</option>
                            </select>
                        </FormField>
                        <FormField label="Moeda">
                            <select
                                id="currency"
                                value={formData.currency}
                                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                disabled={submitting}
                            >
                                <option value="BRL">BRL (Real Brasileiro)</option>
                                <option value="USD">USD (Dólar Americano)</option>
                                <option value="EUR">EUR (Euro)</option>
                                <option value="GBP">GBP (Libra Esterlina)</option>
                            </select>
                        </FormField>
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
                error={actionBarErrorProps.error}
                message={actionBarErrorProps.message}
                messageType={actionBarErrorProps.messageType}
                buttons={actionBarButtons}
            />
        </>
    )
}
