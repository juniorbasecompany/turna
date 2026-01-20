'use client'

import { ActionBar, ActionBarSpacer } from '@/components/ActionBar'
import { CardFooter } from '@/components/CardFooter'
import { CardPanel } from '@/components/CardPanel'
import { CreateCard } from '@/components/CreateCard'
import { Pagination } from '@/components/Pagination'
import { FormField } from '@/components/FormField'
import { FormFieldGrid } from '@/components/FormFieldGrid'
import { useTenantSettings } from '@/contexts/TenantSettingsContext'
import { protectedFetch } from '@/lib/api'
import { getCardContainerClasses } from '@/lib/cardStyles'
import {
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
    TenantUpdateRequest,
} from '@/types/api'
import { useEffect, useState } from 'react'

export default function TenantPage() {
    const { settings } = useTenantSettings()
    const [tenants, setTenants] = useState<TenantResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [editingTenant, setEditingTenant] = useState<TenantResponse | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        slug: '',
        timezone: 'America/Sao_Paulo',
        locale: 'pt-BR',
        currency: 'BRL',
    })
    const [originalFormData, setOriginalFormData] = useState({
        name: '',
        slug: '',
        timezone: 'America/Sao_Paulo',
        locale: 'pt-BR',
        currency: 'BRL',
    })
    const [submitting, setSubmitting] = useState(false)
    const [selectedTenants, setSelectedTenants] = useState<Set<number>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [pagination, setPagination] = useState({ limit: 20, offset: 0 })
    const [total, setTotal] = useState(0)

    // Carregar lista de tenants
    const loadTenants = async () => {
        try {
            setLoading(true)
            setError(null)

            const params = new URLSearchParams()
            params.append('limit', String(pagination.limit))
            params.append('offset', String(pagination.offset))

            const data = await protectedFetch<TenantListResponse>(`/api/tenant/list?${params.toString()}`)
            setTenants(data.items)
            setTotal(data.total)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar clínicas'
            setError(message)
            console.error('Erro ao carregar clínicas:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadTenants()
    }, [pagination])

    // Verificar se há mudanças nos campos
    const hasChanges = () => {
        // Se está criando (não há editingTenant), qualquer campo preenchido é mudança
        if (!editingTenant) {
            return (
                formData.name.trim() !== '' ||
                formData.slug.trim() !== '' ||
                formData.timezone !== 'America/Sao_Paulo' ||
                formData.locale !== 'pt-BR' ||
                formData.currency !== 'BRL'
            )
        }
        // Se está editando, compara com os valores originais
        return (
            formData.name.trim() !== originalFormData.name.trim() ||
            formData.slug.trim() !== originalFormData.slug.trim() ||
            formData.timezone !== originalFormData.timezone ||
            formData.locale !== originalFormData.locale ||
            formData.currency !== originalFormData.currency
        )
    }

    // Verificar se está em modo de edição/criação
    const [showEditArea, setShowEditArea] = useState(false)
    const isEditing = showEditArea

    // Abrir modo de criação
    const handleCreateClick = () => {
        setFormData({
            name: '',
            slug: '',
            timezone: 'America/Sao_Paulo',
            locale: 'pt-BR',
            currency: 'BRL',
        })
        setOriginalFormData({
            name: '',
            slug: '',
            timezone: 'America/Sao_Paulo',
            locale: 'pt-BR',
            currency: 'BRL',
        })
        setEditingTenant(null)
        setShowEditArea(true)
        setError(null)
    }

    // Abrir modo de edição
    const handleEditClick = (tenant: TenantResponse) => {
        const initialData = {
            name: tenant.name,
            slug: tenant.slug,
            timezone: tenant.timezone,
            locale: tenant.locale,
            currency: tenant.currency,
        }
        setFormData(initialData)
        setOriginalFormData(initialData)
        setEditingTenant(tenant)
        setShowEditArea(true)
        setError(null)
    }

    // Cancelar edição e/ou seleção
    const handleCancel = () => {
        setFormData({
            name: '',
            slug: '',
            timezone: 'America/Sao_Paulo',
            locale: 'pt-BR',
            currency: 'BRL',
        })
        setOriginalFormData({
            name: '',
            slug: '',
            timezone: 'America/Sao_Paulo',
            locale: 'pt-BR',
            currency: 'BRL',
        })
        setEditingTenant(null)
        setShowEditArea(false)
        setSelectedTenants(new Set())
        setError(null)
    }

    // Submeter formulário (criar ou editar)
    const handleSave = async () => {
        if (!formData.name.trim()) {
            setError('Nome é obrigatório')
            return
        }

        if (!formData.slug.trim()) {
            setError('Slug é obrigatório')
            return
        }

        try {
            setSubmitting(true)
            setError(null)

            if (editingTenant) {
                // Editar tenant existente
                const updateData: TenantUpdateRequest = {
                    name: formData.name.trim(),
                    slug: formData.slug.trim(),
                    timezone: formData.timezone,
                    locale: formData.locale,
                    currency: formData.currency,
                }

                await protectedFetch(`/api/tenant/${editingTenant.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                })
            } else {
                // Criar novo tenant
                const createData: TenantCreateRequest = {
                    name: formData.name.trim(),
                    slug: formData.slug.trim(),
                    timezone: formData.timezone,
                    locale: formData.locale,
                    currency: formData.currency,
                }

                await protectedFetch('/api/tenant', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(createData),
                })
            }

            // Recarregar lista e limpar formulário
            await loadTenants()
            setFormData({
                name: '',
                slug: '',
                timezone: 'America/Sao_Paulo',
                locale: 'pt-BR',
                currency: 'BRL',
            })
            setOriginalFormData({
                name: '',
                slug: '',
                timezone: 'America/Sao_Paulo',
                locale: 'pt-BR',
                currency: 'BRL',
            })
            setEditingTenant(null)
            setShowEditArea(false)

            // Notificar Header para atualizar lista de tenants
            window.dispatchEvent(new CustomEvent('tenant-list-updated'))
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao salvar clínica'
            setError(message)
            console.error('Erro ao salvar clínica:', err)
        } finally {
            setSubmitting(false)
        }
    }

    // Toggle seleção de tenant para exclusão
    const toggleTenantSelection = (tenantId: number) => {
        setSelectedTenants((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(tenantId)) {
                newSet.delete(tenantId)
            } else {
                newSet.add(tenantId)
            }
            return newSet
        })
    }

    // Excluir tenants selecionados
    const handleDeleteSelected = async () => {
        if (selectedTenants.size === 0) return

        setDeleting(true)
        setError(null)

        try {
            // Excluir todos os tenants selecionados em paralelo
            const deletePromises = Array.from(selectedTenants).map(async (tenantId) => {
                await protectedFetch(`/api/tenant/${tenantId}`, {
                    method: 'DELETE',
                })
                return tenantId
            })

            await Promise.all(deletePromises)

            // Remover tenants deletados da lista
            setTenants(tenants.filter((tenant) => !selectedTenants.has(tenant.id)))
            setSelectedTenants(new Set())

            // Recarregar lista para garantir sincronização
            await loadTenants()

            // Notificar Header para atualizar lista de tenants
            window.dispatchEvent(new CustomEvent('tenant-list-updated'))
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Erro ao excluir clínicas. Tente novamente.'
            )
        } finally {
            setDeleting(false)
        }
    }

    return (
        <>
            {/* Área de edição */}
            {isEditing && (
                <div className="p-4 sm:p-6 lg:p-8 min-w-0">
                    <div className="mb-4 sm:mb-6 bg-white rounded-lg border border-gray-200 p-4 sm:p-6">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">
                            {editingTenant ? 'Editar Clínica' : 'Criar Clínica'}
                        </h2>
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
                    </div>
                </div>
            )}

            <CardPanel
                title="Clínicas"
                description="Gerencie as clínicas (tenants) do sistema"
                totalCount={tenants.length}
                selectedCount={selectedTenants.size}
                loading={loading}
                loadingMessage="Carregando clínicas..."
                emptyMessage="Nenhuma clínica cadastrada ainda."
                countLabel="Total de clínicas"
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
                            onFirst={() => setPagination({ ...pagination, offset: 0 })}
                            onPrevious={() => setPagination({ ...pagination, offset: Math.max(0, pagination.offset - pagination.limit) })}
                            onNext={() => setPagination({ ...pagination, offset: pagination.offset + pagination.limit })}
                            onLast={() => setPagination({ ...pagination, offset: Math.floor((total - 1) / pagination.limit) * pagination.limit })}
                            disabled={loading}
                        />
                    ) : undefined
                }
                error={(() => {
                    // Mostra erro no ActionBar apenas se houver botões de ação
                    const hasButtons = isEditing || selectedTenants.size > 0
                    return hasButtons ? error : undefined
                })()}
                message={(() => {
                    // Se não há botões mas há erro, mostrar via message
                    const hasButtons = isEditing || selectedTenants.size > 0
                    if (!hasButtons && error) {
                        return error
                    }
                    return undefined
                })()}
                messageType={(() => {
                    // Se não há botões mas há erro, usar tipo error
                    const hasButtons = isEditing || selectedTenants.size > 0
                    if (!hasButtons && error) {
                        return 'error' as const
                    }
                    return undefined
                })()}
                buttons={(() => {
                    const buttons = []
                    // Botão Cancelar (aparece se houver edição OU seleção)
                    if (isEditing || selectedTenants.size > 0) {
                        buttons.push({
                            label: 'Cancelar',
                            onClick: handleCancel,
                            variant: 'secondary' as const,
                            disabled: submitting || deleting,
                        })
                    }
                    // Botão Excluir (aparece se houver seleção)
                    if (selectedTenants.size > 0) {
                        buttons.push({
                            label: 'Excluir',
                            onClick: handleDeleteSelected,
                            variant: 'primary' as const,
                            disabled: deleting || submitting,
                            loading: deleting,
                        })
                    }
                    // Botão Salvar (aparece se houver edição com mudanças)
                    if (isEditing && hasChanges()) {
                        buttons.push({
                            label: submitting ? 'Salvando...' : 'Salvar',
                            onClick: handleSave,
                            variant: 'primary' as const,
                            disabled: submitting,
                            loading: submitting,
                        })
                    }
                    return buttons
                })()}
            />
        </>
    )
}
