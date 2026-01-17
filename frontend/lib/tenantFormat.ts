/**
 * Módulo centralizado para formatação de datas, números e moedas
 * baseado nas configurações do tenant (timezone, locale, currency).
 *
 * Todas as conversões de fuso horário acontecem apenas na camada de apresentação.
 * O backend sempre trabalha com UTC.
 */

/**
 * Configurações de formatação do tenant
 */
export interface TenantFormatSettings {
    timezone: string // IANA timezone (ex: "America/Sao_Paulo")
    locale: string // BCP 47 locale (ex: "pt-BR")
    currency: string // ISO 4217 currency (ex: "BRL")
}

/**
 * Opções para formatação de data/hora
 */
export interface DateTimeFormatOptions extends Intl.DateTimeFormatOptions {
    // Opções padrão já incluem: year, month, day, hour, minute
}

/**
 * Opções para formatação de número
 */
export interface NumberFormatOptions extends Intl.NumberFormatOptions {
    // Opções padrão já incluem: locale do tenant
}

/**
 * Formata uma data/hora ISO 8601 (UTC) para exibição no timezone do tenant.
 *
 * @param isoUtcString - String ISO 8601 em UTC (ex: "2026-01-17T14:30:00Z")
 * @param settings - Configurações do tenant (timezone, locale)
 * @param options - Opções adicionais para Intl.DateTimeFormat
 * @returns String formatada conforme locale do tenant (ex: "17/01/2026 14:30" para pt-BR, "01/17/2026 02:30 PM" para en-US)
 */
export function formatDateTime(
    isoUtcString: string,
    settings: TenantFormatSettings,
    options?: DateTimeFormatOptions
): string {
    const date = new Date(isoUtcString)

    // Usar opções padrão de formatação (ano, mês, dia, hora, minuto)
    const defaultOptions: DateTimeFormatOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        ...options,
    }

    // Usar locale e timezone do tenant - Intl.DateTimeFormat aplica automaticamente
    // o formato apropriado para cada locale (ex: DD/MM/YYYY para pt-BR, MM/DD/YYYY para en-US)
    const formatter = new Intl.DateTimeFormat(settings.locale, {
        ...defaultOptions,
        timeZone: settings.timezone,
    })

    return formatter.format(date)
}

/**
 * Formata um número usando o locale do tenant.
 *
 * @param value - Valor numérico a formatar
 * @param settings - Configurações do tenant (locale)
 * @param options - Opções adicionais para Intl.NumberFormat
 * @returns String formatada (ex: "1.234,56")
 */
export function formatNumber(
    value: number,
    settings: TenantFormatSettings,
    options?: NumberFormatOptions
): string {
    const formatter = new Intl.NumberFormat(settings.locale, options)
    return formatter.format(value)
}

/**
 * Formata um valor monetário usando o locale e currency do tenant.
 *
 * @param value - Valor monetário a formatar
 * @param settings - Configurações do tenant (locale, currency)
 * @param options - Opções adicionais para Intl.NumberFormat
 * @returns String formatada conforme locale e currency do tenant (ex: "R$ 1.234,56" para pt-BR/BRL, "$1,234.56" para en-US/USD)
 */
export function formatMoney(
    value: number,
    settings: TenantFormatSettings,
    options?: NumberFormatOptions
): string {
    const formatter = new Intl.NumberFormat(settings.locale, {
        style: 'currency',
        currency: settings.currency,
        ...options,
    })
    return formatter.format(value)
}

/**
 * Formata apenas a data (sem hora) usando o locale do tenant.
 *
 * @param date - Objeto Date (será interpretado como data no timezone do tenant)
 * @param settings - Configurações do tenant (locale, timezone)
 * @returns String formatada apenas com data (ex: "17/01/2026" para pt-BR, "01/17/2026" para en-US)
 */
export function formatLocalDateOnly(
    date: Date,
    settings: TenantFormatSettings
): string {
    const formatter = new Intl.DateTimeFormat(settings.locale, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        timeZone: settings.timezone,
    })
    return formatter.format(date)
}

/**
 * Converte uma data local (timezone do tenant) para UTC início do dia (00:00:00).
 *
 * Usa Intl.DateTimeFormat para converter corretamente considerando o timezone do tenant,
 * mesmo quando o navegador está em um timezone diferente.
 *
 * @param localDate - Objeto Date representando uma data (componentes ano/mês/dia)
 * @param settings - Configurações do tenant (timezone)
 * @returns String ISO 8601 em UTC representando início do dia no timezone do tenant
 */
export function localDateToUtcStart(
    localDate: Date,
    settings: TenantFormatSettings
): string {
    // Validar entrada
    if (!(localDate instanceof Date) || isNaN(localDate.getTime())) {
        throw new Error('localDate deve ser uma Date válida')
    }

    // Extrair componentes ano/mês/dia da Date fornecida
    // Esses componentes são interpretados como representando o dia no timezone do tenant
    const year = localDate.getFullYear()
    const month = localDate.getMonth() + 1 // getMonth() retorna 0-11, precisamos 1-12
    const day = localDate.getDate()

    // Criar formatters para o timezone do tenant
    const dateFormatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: settings.timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    })

    const timeFormatter = new Intl.DateTimeFormat('en-US', {
        timeZone: settings.timezone,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    })

    // Começar com uma estimativa baseada na data local à meia-noite
    const localMidnight = new Date(year, month - 1, day, 0, 0, 0, 0)

    // Tentar diferentes ajustes UTC até encontrar aquele que quando formatado
    // no timezone do tenant resulta em YYYY-MM-DD 00:00:00
    const adjustments = [0, -3600000, -7200000, -10800000, 3600000, 7200000, 10800000] // ±0, ±1h, ±2h, ±3h

    for (const adjustment of adjustments) {
        const testDate = new Date(localMidnight.getTime() + adjustment)

        if (isNaN(testDate.getTime())) {
            continue
        }

        try {
            const dateStr = dateFormatter.format(testDate)
            const timeStr = timeFormatter.format(testDate)

            const [datePart] = dateStr.split(' ')
            const [tzYear, tzMonth, tzDay] = datePart.split('-').map(Number)
            const [tzHour, tzMinute, tzSecond] = timeStr.split(':').map(Number)

            // Verificar se corresponde ao dia e hora desejados
            if (tzYear === year && tzMonth === month && tzDay === day && tzHour === 0 && tzMinute === 0 && tzSecond === 0) {
                return testDate.toISOString()
            }
        } catch (e) {
            // Continuar tentando outros ajustes
            continue
        }
    }

    // Se não encontrou com ajustes simples, usar busca iterativa mais cuidadosa
    let testDate = new Date(year, month - 1, day, 0, 0, 0, 0)

    // Iterar até encontrar (máximo 10 iterações)
    for (let i = 0; i < 10; i++) {
        if (isNaN(testDate.getTime())) {
            break
        }

        try {
            const dateStr = dateFormatter.format(testDate)
            const timeStr = timeFormatter.format(testDate)

            const [datePart] = dateStr.split(' ')
            if (!datePart) break

            const [tzYear, tzMonth, tzDay] = datePart.split('-').map(Number)
            const [tzHour, tzMinute, tzSecond] = timeStr.split(':').map(Number)

            if (tzYear === year && tzMonth === month && tzDay === day && tzHour === 0 && tzMinute === 0 && tzSecond === 0) {
                return testDate.toISOString()
            }

            // Ajustar: subtrair horas/minutos/segundos que aparecem no timezone do tenant
            if (tzHour !== 0 || tzMinute !== 0 || tzSecond !== 0) {
                const msToSubtract = (tzHour * 3600 + tzMinute * 60 + tzSecond) * 1000
                testDate = new Date(testDate.getTime() - msToSubtract)
            } else if (tzYear !== year || tzMonth !== month || tzDay !== day) {
                // Se hora é 00:00:00 mas dia/ano/mês estão errados, ajustar dia
                // Calcular diferença de forma mais robusta considerando mudanças de mês/ano
                const targetDate = new Date(year, month - 1, day)
                const currentDate = new Date(tzYear, tzMonth - 1, tzDay)
                const dayDiff = Math.round((targetDate.getTime() - currentDate.getTime()) / (1000 * 60 * 60 * 24))
                testDate = new Date(testDate.getTime() + dayDiff * 24 * 60 * 60 * 1000)
            } else {
                // Dia, mês, ano e hora corretos - convergiu
                return testDate.toISOString()
            }
        } catch (e) {
            break
        }
    }

    // Fallback final: usar data local à meia-noite
    const fallback = new Date(year, month - 1, day, 0, 0, 0, 0)
    if (!isNaN(fallback.getTime())) {
        return fallback.toISOString()
    }

    throw new Error(`Não foi possível converter data para UTC: ${year}-${month}-${day}`)
}

/**
 * Converte uma data local (timezone do tenant) para UTC início do próximo dia (00:00:00).
 * Útil para criar intervalos [start_at, end_at) onde end_at é exclusivo.
 *
 * @param localDate - Objeto Date representando uma data no timezone do tenant
 * @param settings - Configurações do tenant (timezone)
 * @returns String ISO 8601 em UTC do início do próximo dia
 */
export function localDateToUtcEndExclusive(
    localDate: Date,
    settings: TenantFormatSettings
): string {
    // Adicionar 1 dia e retornar início do dia
    const nextDay = new Date(localDate)
    nextDay.setDate(nextDay.getDate() + 1)
    return localDateToUtcStart(nextDay, settings)
}

/**
 * Converte uma string ISO UTC para Date local (extrai apenas os componentes de data, ignorando hora).
 * Útil para converter datas retornadas da API (UTC) para Date objects usados no DatePicker.
 *
 * @param isoUtcString - String ISO 8601 em UTC (ex: "2026-01-17T03:00:00.000Z")
 * @param settings - Configurações do tenant (timezone)
 * @returns Date representando a data no timezone do tenant (hora será 00:00:00 local)
 */
export function utcToLocalDate(
    isoUtcString: string,
    settings: TenantFormatSettings
): Date {
    // Criar Date da string UTC
    const utcDate = new Date(isoUtcString)

    // Obter componentes da data no timezone do tenant usando formatter
    const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: settings.timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    })
    const dateStr = formatter.format(utcDate) // Formato: YYYY-MM-DD

    // Parse da string
    const [year, month, day] = dateStr.split('-').map(Number)

    // Criar Date local com esses componentes (hora 00:00:00)
    // Isso garante que o Date representa o dia correto no timezone do tenant
    return new Date(year, month - 1, day, 0, 0, 0, 0)
}

/**
 * Converte um intervalo de datas no timezone do tenant para UTC (ISO 8601).
 * Retorna intervalo no formato [start_at, end_at) conforme diretrizes.
 *
 * @param localStart - String de data no timezone do tenant (ex: "2026-01-17" ou ISO já em UTC)
 * @param localEnd - String de data no timezone do tenant (ex: "2026-01-17" ou ISO já em UTC)
 * @param settings - Configurações do tenant (timezone)
 * @returns Objeto com start_at e end_at em UTC (ISO 8601 com Z)
 */
export function toUtcRange(
    localStart: string,
    localEnd: string,
    settings: TenantFormatSettings
): { start_at: string; end_at: string } {
    // Se já são ISO 8601 completos com timezone, retornar diretamente
    if ((localStart.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(localStart)) &&
        (localEnd.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(localEnd))) {
        return { start_at: localStart, end_at: localEnd }
    }

    // Se for só data (YYYY-MM-DD), adicionar hora e converter
    let startDateTime = localStart
    let endDateTime = localEnd

    if (localStart.length === 10) {
        startDateTime = `${localStart}T00:00:00`
    }
    if (localEnd.length === 10) {
        endDateTime = `${localEnd}T23:59:59.999`
    }

    // Parse das strings - JavaScript Date interpreta no timezone local do navegador
    // Por enquanto, assumimos que o timezone do navegador está alinhado com o do tenant
    // Para conversão precisa com timezone diferente, seria necessário usar biblioteca externa
    const startDate = new Date(startDateTime)
    const endDate = new Date(endDateTime)

    // Converter para UTC (ISO 8601 com Z)
    const start_at = startDate.toISOString()
    const end_at = endDate.toISOString()

    return { start_at, end_at }
}
