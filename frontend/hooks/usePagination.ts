import { useState, useCallback } from 'react'

interface PaginationState {
    limit: number
    offset: number
}

interface UsePaginationReturn {
    pagination: PaginationState
    setPagination: React.Dispatch<React.SetStateAction<PaginationState>>
    total: number
    setTotal: React.Dispatch<React.SetStateAction<number>>
    onFirst: () => void
    onPrevious: () => void
    onNext: () => void
    onLast: () => void
    reset: () => void
}

export function usePagination(initialLimit = 20): UsePaginationReturn {
    const [pagination, setPagination] = useState<PaginationState>({
        limit: initialLimit,
        offset: 0,
    })
    const [total, setTotal] = useState(0)

    const onFirst = useCallback(() => {
        setPagination((prev) => ({ ...prev, offset: 0 }))
    }, [])

    const onPrevious = useCallback(() => {
        setPagination((prev) => ({
            ...prev,
            offset: Math.max(0, prev.offset - prev.limit),
        }))
    }, [])

    const onNext = useCallback(() => {
        setPagination((prev) => ({
            ...prev,
            offset: prev.offset + prev.limit,
        }))
    }, [])

    const onLast = useCallback(() => {
        setPagination((prev) => ({
            ...prev,
            offset: Math.floor((total - 1) / prev.limit) * prev.limit,
        }))
    }, [total])

    const reset = useCallback(() => {
        setPagination({ limit: initialLimit, offset: 0 })
    }, [initialLimit])

    return {
        pagination,
        setPagination,
        total,
        setTotal,
        onFirst,
        onPrevious,
        onNext,
        onLast,
        reset,
    }
}
