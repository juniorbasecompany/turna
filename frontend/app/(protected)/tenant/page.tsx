'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { EditForm } from '@/components/EditForm'
import { Pagination } from '@/components/Pagination'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { getCardContainerClasses } from '@/lib/cardStyles'
import {
    TenantCreateRequest,
    TenantResponse,
    TenantUpdateRequest,
} from '@/types/api'
import { useEntityPage } from '@/hooks/useEntityPage'

type TenantFormData = {
    name: string
    slug: string
    timezone: string
    locale: string
    currency: string
}

export default function TenantPage() {
    const { settings } = useTenantSettings()

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
        selectedCount: selectedTenantsCount,
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
                totalCount={tenants.length}
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
            >
                {tenants.map((tenant) => {
                    const isSelected = selectedTenants.has(tenant.id)
                    return (
                        <div
                            key={tenant.id}
                            className={getCardContainerClasses(isSelected)}
                        >
                            {/* Corpo - Nome e informações */}
                            <div className="mb-3">
                                <div className="h-40 sm:h-48 rounded-lg flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200">
                                    <div className="flex flex-col items-center justify-center text-blue-600">
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
                                            title={tenant.name}
                                        >
                                            {tenant.name}
                                        </h3>
                                        <p className="text-xs text-gray-600 mt-1">{tenant.slug}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Rodapé - Metadados e ações */}
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
