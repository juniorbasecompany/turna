/**
 * Funções utilitárias genéricas para gerenciamento de entidades
 */

/**
 * Toggle de seleção em um Set
 */
export function toggleSelection<T>(set: Set<T>, item: T): Set<T> {
    const newSet = new Set(set)
    if (newSet.has(item)) {
        newSet.delete(item)
    } else {
        newSet.add(item)
    }
    return newSet
}

type NameLike = {
    name?: string | null
    label?: string | null
    display_name?: string | null
}

type MemberNameLike = {
    id?: number | null
    member_name?: string | null
    member_label?: string | null
    member_email?: string | null
    display_name?: string | null
}

/**
 * Resolve o nome exibido priorizando display_name/label.
 */
export function getDisplayName(entity: NameLike | null | undefined, fallback = ''): string {
    if (!entity) return fallback

    const displayName = entity.display_name?.trim()
    if (displayName) return displayName

    const label = entity.label?.trim()
    if (label) return label

    const name = entity.name?.trim()
    if (name) return name

    return fallback
}

/**
 * Resolve o nome exibido do associado.
 */
export function getMemberDisplayName(member: MemberNameLike | null | undefined): string {
    if (!member) return 'Não disponível'

    const displayName = member.display_name?.trim()
    if (displayName) return displayName

    const label = member.member_label?.trim()
    if (label) return label

    const name = member.member_name?.trim()
    if (name) return name

    const email = member.member_email?.trim()
    if (email) return email

    if (member.id != null) {
        return `Associado ${member.id}`
    }

    return 'Não disponível'
}

/**
 * Verifica se há mudanças no formulário
 */
export function hasFormChanges<T extends Record<string, unknown>>(
    editingItem: T | null,
    formData: T,
    originalFormData: T,
    isEmptyCheck?: (data: T) => boolean
): boolean {
    // Se está criando (não há editingItem), verifica se há campos preenchidos
    if (!editingItem) {
        if (isEmptyCheck) {
            return !isEmptyCheck(formData)
        }
        // Verificação padrão: se algum campo não está vazio
        return Object.values(formData).some((value) => {
            if (value === null || value === undefined) return false
            if (typeof value === 'string') return value.trim() !== ''
            if (Array.isArray(value)) return value.length > 0
            if (typeof value === 'object') return Object.keys(value).length > 0
            return true
        })
    }

    // Se está editando, compara com os valores originais
    return JSON.stringify(formData) !== JSON.stringify(originalFormData)
}

/**
 * Obtém as props de erro para o ActionBar
 */
export function getActionBarErrorProps(
    error: string | null,
    isEditing: boolean,
    selectedCount: number,
    emailMessage?: string | null,
    emailMessageType?: 'success' | 'error'
) {
    const hasButtons = isEditing || selectedCount > 0

    // Se houver mensagem de email, priorizar ela
    if (emailMessage) {
        return {
            error: undefined,
            message: emailMessage,
            messageType: emailMessageType || 'success',
        }
    }

    // Caso contrário, usar lógica padrão
    return {
        error: hasButtons ? error || undefined : undefined,
        message: !hasButtons && error ? error : undefined,
        messageType: !hasButtons && error ? ('error' as const) : undefined,
    }
}

/**
 * Cria um handler genérico para exclusão de itens
 */
export function createDeleteHandler<T extends { id: number }>(
    selectedItems: Set<number>,
    items: T[],
    deleteEndpoint: (id: number) => string,
    onDelete: (ids: number[]) => Promise<void>,
    onSuccess?: () => void
) {
    return async () => {
        if (selectedItems.size === 0) return

        try {
            // Passar todos os IDs de uma vez para onDelete
            const ids = Array.from(selectedItems)
            await onDelete(ids)

            // Remover itens deletados da lista local
            const remainingItems = items.filter((item) => !selectedItems.has(item.id))

            if (onSuccess) {
                onSuccess()
            }

            return remainingItems
        } catch (err) {
            throw err
        }
    }
}
