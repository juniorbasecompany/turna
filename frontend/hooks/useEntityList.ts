import { useState, useEffect, useCallback } from 'react'
import { protectedFetch } from '@/lib/api'
import { usePagination } from './usePagination'

interface ListResponse<T> {
    items: T[]
    total: number
}

interface UseEntityListOptions<T> {
    endpoint: string
    pagination: ReturnType<typeof usePagination>['pagination']
    setTotal: (total: number) => void
    additionalParams?: Record<string, string | number | boolean | null>
    enabled?: boolean
}

interface UseEntityListReturn<T> {
    items: T[]
    loading: boolean
    error: string | null
    loadItems: () => Promise<void>
    setError: React.Dispatch<React.SetStateAction<string | null>>
}

export function useEntityList<T extends { id: number }>(
    options: UseEntityListOptions<T>
): UseEntityListReturn<T> {
    const { endpoint, pagination, setTotal, additionalParams, enabled = true } = options
    const [items, setItems] = useState<T[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const loadItems = useCallback(async () => {
        if (!enabled) {
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const params = new URLSearchParams()
            params.append('limit', String(pagination.limit))
            params.append('offset', String(pagination.offset))

            // Adicionar parâmetros adicionais se fornecidos
            if (additionalParams) {
                Object.entries(additionalParams).forEach(([key, value]) => {
                    if (value !== null && value !== undefined) {
                        params.append(key, String(value))
                    }
                })
            }

            const data = await protectedFetch<ListResponse<T>>(`${endpoint}?${params.toString()}`)
            setItems(data.items)
            setTotal(data.total)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Erro ao carregar dados'
            setError(message)
            console.error('Erro ao carregar dados:', err)
        } finally {
            setLoading(false)
        }
    }, [endpoint, pagination.limit, pagination.offset, setTotal, additionalParams, enabled])

    useEffect(() => {
        loadItems()
    }, [loadItems])

    return {
        items,
        loading,
        error,
        loadItems,
        setError,
    }
}
