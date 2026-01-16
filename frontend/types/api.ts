// Types baseados nos modelos do backend

export interface AuthResponse {
  access_token: string | null
  token_type: string
  requires_tenant_selection: boolean
  tenants: TenantOption[]
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

export interface TenantResponse {
  id: number
  name: string
  slug: string
  timezone: string
  created_at: string
  updated_at: string
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
}
