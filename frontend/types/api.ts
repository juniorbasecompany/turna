// Types baseados nos modelos do backend

export interface AuthResponse {
    access_token: string | null
    token_type: string
    requires_tenant_selection: boolean
    tenants: TenantOption[]
    invites?: InviteOption[] // Convites pendentes
    detail?: string // Para mensagens de erro
}

export interface TenantOption {
    tenant_id: number
    name: string
    slug: string
    role: string
}

export interface InviteOption {
    member_id: number
    tenant_id: number
    name: string
    slug: string
    role: string
    status: string
}

export interface TokenResponse {
    access_token: string
    token_type: string
}

export interface TenantListResponse {
    tenants: TenantOption[]
    invites: InviteOption[]
}

export interface AccountResponse {
    id: number
    email: string
    name: string
    role: string
    tenant_id: number
    auth_provider: string
    created_at: string
    updated_at: string
}

// Resposta do endpoint /me (inclui member_name)
export interface MeResponse {
    id: number
    email: string
    name: string  // Nome privado (account.name)
    member_name: string | null  // Nome público na clínica (member.name)
    role: string
    tenant_id: number
    auth_provider: string
    created_at: string
    updated_at: string
}

export interface AccountListResponse {
    items: AccountResponse[]
    total: number
}

export interface TenantResponse {
    id: number
    name: string
    slug: string
    timezone: string
    locale: string
    currency: string
    created_at: string
    updated_at: string
}

export interface TenantListResponse {
    items: TenantResponse[]
    total: number
}

export interface TenantCreateRequest {
    name: string
    slug: string
    timezone?: string
    locale?: string
    currency?: string
}

export interface TenantUpdateRequest {
    name?: string
    slug?: string
    timezone?: string
    locale?: string
    currency?: string
}

export interface JobResponse {
    id: number
    tenant_id: number
    job_type: string
    status: string
    input_data: Record<string, unknown> | null
    result_data: Record<string, unknown> | null
    error_message: string | null
    created_at: string
    updated_at: string
    started_at: string | null
    completed_at: string | null
}

export interface JobListResponse {
    items: JobResponse[]
    total: number
}

export interface FileUploadResponse {
    file_id: number
    filename: string
    content_type: string
    file_size: number
    s3_url: string
    presigned_url: string
}

export interface FileResponse {
    id: number
    filename: string
    content_type: string
    file_size: number
    created_at: string
    can_delete: boolean
    job_status: string | null
}

export interface FileListResponse {
    items: FileResponse[]
    total: number
}

export interface ScheduleResponse {
    id: number
    tenant_id: number
    name: string
    period_start_at: string
    period_end_at: string
    status: string
    version_number: number
    job_id: number | null
    pdf_file_id: number | null
    generated_at: string | null
    published_at: string | null
    created_at: string
    updated_at: string
}

export interface ScheduleListResponse {
    items: ScheduleResponse[]
    total: number
}

export interface SchedulePublishResponse {
    schedule_id: number
    status: string
    pdf_file_id: number
    presigned_url: string
}

export interface ScheduleGenerateRequest {
    extract_job_id: number
    period_start_at: string
    period_end_at: string
    allocation_mode?: string
    pros_by_sequence?: number[]
}

export interface ScheduleGenerateResponse {
    job_id: number
    schedule_id: number
}

export interface ScheduleCreateRequest {
    name: string
    period_start_at: string
    period_end_at: string
    version_number?: number
}

export interface ScheduleUpdateRequest {
    name?: string
    period_start_at?: string
    period_end_at?: string
    version_number?: number
    status?: string
}

export interface ScheduleGenerateFromDemandsRequest {
    name: string
    period_start_at: string
    period_end_at: string
    allocation_mode?: string
    pros_by_sequence?: Array<Record<string, unknown>>
    version_number?: number
}

export interface ScheduleGenerateFromDemandsResponse {
    job_id: number
    schedule_id: number
}

export interface GoogleTokenRequest {
    id_token: string
}

export interface GoogleSelectTenantRequest {
    id_token: string
    tenant_id: number
}

export interface TenantCreateRequest {
    name: string
    slug: string
    timezone?: string
    locale?: string
    currency?: string
}

export interface HospitalResponse {
    id: number
    tenant_id: number
    name: string
    prompt: string | null
    color: string | null
    created_at: string
    updated_at: string
}

export interface HospitalListResponse {
    items: HospitalResponse[]
    total: number
}

export interface HospitalCreateRequest {
    name: string
    prompt?: string | null
    color?: string | null
}

export interface HospitalUpdateRequest {
    name?: string
    prompt?: string
    color?: string | null
}

export interface DemandResponse {
    id: number
    tenant_id: number
    hospital_id: number | null
    job_id: number | null
    room: string | null
    start_time: string
    end_time: string
    procedure: string
    anesthesia_type: string | null
    complexity: string | null
    skills: string[] | null
    priority: string | null
    is_pediatric: boolean
    notes: string | null
    source: Record<string, unknown> | null
    created_at: string
    updated_at: string
}

export interface DemandListResponse {
    items: DemandResponse[]
    total: number
}

export interface DemandCreateRequest {
    hospital_id?: number | null
    job_id?: number | null
    room?: string | null
    start_time: string
    end_time: string
    procedure: string
    anesthesia_type?: string | null
    complexity?: string | null
    skills?: string[] | null
    priority?: string | null
    is_pediatric?: boolean
    notes?: string | null
    source?: Record<string, unknown> | null
}

export interface DemandUpdateRequest {
    hospital_id?: number | null
    job_id?: number | null
    room?: string | null
    start_time?: string
    end_time?: string
    procedure?: string
    anesthesia_type?: string | null
    complexity?: string | null
    skills?: string[] | null
    priority?: string | null
    is_pediatric?: boolean
    notes?: string | null
    source?: Record<string, unknown> | null
}


export interface MemberResponse {
    id: number
    tenant_id: number
    account_id: number | null
    account_email: string | null  // Privado, apenas para compatibilidade/auditoria
    member_email: string | null  // Email público na clínica (pode ser editado)
    member_name: string | null  // Nome público na clínica (pode ser editado)
    role: string
    status: string
    attribute: Record<string, unknown>
    created_at: string
    updated_at: string
}

export interface MemberListResponse {
    items: MemberResponse[]
    total: number
}

export interface MemberUpdateRequest {
    role?: string | null
    status?: string | null
    name?: string | null
    email?: string | null  // Email público editável
    attribute?: Record<string, unknown> | null
}

export interface MemberCreateRequest {
    email?: string | null  // Email público (obrigatório se account_id não for fornecido)
    name?: string | null  // Nome público
    role: string
    status: string
    account_id?: number | null  // Opcional (não usado no painel)
    attribute?: Record<string, unknown> | null
}

export interface AccountOption {
    id: number
    email: string
    name: string
}
