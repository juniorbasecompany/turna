'use client'

import { TenantDateTimePicker } from '../TenantDateTimePicker'

interface FilterDateRangeProps {
  /** Label para o campo de data inicial */
  startLabel?: string
  /** Label para o campo de data final */
  endLabel?: string
  /** Valor da data inicial */
  startValue: Date | null
  /** Valor da data final */
  endValue: Date | null
  /** Callback quando a data inicial muda */
  onStartChange: (value: Date | null) => void
  /** Callback quando a data final muda */
  onEndChange: (value: Date | null) => void
  /** ID para o campo de data inicial (acessibilidade) */
  startId?: string
  /** ID para o campo de data final (acessibilidade) */
  endId?: string
  /** Se o campo de data inicial está desabilitado */
  startDisabled?: boolean
  /** Se o campo de data final está desabilitado */
  endDisabled?: boolean
  /** Mostrar efeito flash no campo de data inicial */
  startShowFlash?: boolean
  /** Mostrar efeito flash no campo de data final */
  endShowFlash?: boolean
}

/**
 * Componente de intervalo de datas para filtros.
 * Encapsula dois TenantDateTimePicker com labels padronizados.
 *
 * Nota: A validação de intervalo (início <= fim) deve ser feita
 * pelo componente pai via useEffect, como já é feito nos painéis.
 *
 * @example
 * ```tsx
 * <FormFieldGrid cols={1} smCols={2} gap={4}>
 *   <FilterDateRange
 *     startLabel="Desde"
 *     endLabel="Até"
 *     startValue={filterStartDate}
 *     endValue={filterEndDate}
 *     onStartChange={setFilterStartDate}
 *     onEndChange={setFilterEndDate}
 *     startId="filter_start_date"
 *     endId="filter_end_date"
 *   />
 * </FormFieldGrid>
 * ```
 */
export function FilterDateRange({
  startLabel = 'Desde',
  endLabel = 'Até',
  startValue,
  endValue,
  onStartChange,
  onEndChange,
  startId,
  endId,
  startDisabled = false,
  endDisabled = false,
  startShowFlash = false,
  endShowFlash = false,
}: FilterDateRangeProps) {
  return (
    <>
      <TenantDateTimePicker
        label={startLabel}
        value={startValue}
        onChange={onStartChange}
        id={startId}
        disabled={startDisabled}
        showFlash={startShowFlash}
      />
      <TenantDateTimePicker
        label={endLabel}
        value={endValue}
        onChange={onEndChange}
        id={endId}
        disabled={endDisabled}
        showFlash={endShowFlash}
      />
    </>
  )
}
