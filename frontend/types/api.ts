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
    membership_id: number
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

export interface ScheduleVersionResponse {
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
    items: ScheduleVersionResponse[]
    total: number
}

export interface SchedulePublishResponse {
    schedule_version_id: number
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
    schedule_version_id: number
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

export interface ProfileResponse {
    id: number
    tenant_id: number
    account_id: number
    hospital_id: number | null
    attribute: Record<string, unknown>
    created_at: string
    updated_at: string
}

export interface ProfileListResponse {
    items: ProfileResponse[]
    total: number
}

export interface ProfileCreateRequest {
    account_id: number
    hospital_id?: number | null
    attribute?: Record<string, unknown>
}

export interface ProfileUpdateRequest {
    hospital_id?: number | null
    attribute?: Record<string, unknown>
}

export interface ProfessionalResponse {
    id: number
    tenant_id: number
    account_id: number | null
    name: string
    email: string
    phone: string | null
    notes: string | null
    active: boolean
    created_at: string
    updated_at: string
}

export interface ProfessionalListResponse {
    items: ProfessionalResponse[]
    total: number
}

export interface MembershipResponse {
    id: number
    tenant_id: number
    account_id: number
    account_email: string | null
    membership_name: string | null  // Nome público na clínica (pode ser NULL)
    role: string
    status: string
    created_at: string
    updated_at: string
}

export interface MembershipListResponse {
    items: MembershipResponse[]
    total: number
}

export interface MembershipUpdateRequest {
    role?: string | null
    status?: string | null
}

export interface ProfessionalCreateRequest {
    name: string
    email: string
    phone?: string | null
    notes?: string | null
    active?: boolean
}

export interface ProfessionalUpdateRequest {
    name?: string | null
    email?: string | null
    phone?: string | null
    notes?: string | null
    active?: boolean | null
}

export interface AccountOption {
    id: number
    email: string
    name: string
}
