// ── Team ──────────────────────────────────────────────────────────────────────

export interface Team {
  id: string
  name: string
  slug: string
  description: string
  issue_types: string[]
  product_types: string[]
  is_active: boolean
  member_count: number
  created_at: string
  updated_at: string
}

// ── User ──────────────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'analyst' | 'viewer' | 'customer'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  team_id: string | null
  team_name: string | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RefreshResponse {
  access_token: string
  token_type: string
  expires_in: number
}

// ── Response Draft ────────────────────────────────────────────────────────────

export interface InternalResponse {
  resolution_summary: string
  action_steps: string[]
}

export interface ExternalResponse {
  acknowledgment: string
  findings: string
  timeline: string
}

export interface ResponseDraftData {
  internal: InternalResponse
  external: ExternalResponse
  policy_citation_labels: string[]
  critique_items_addressed: string[]
}

// ── Complaint ─────────────────────────────────────────────────────────────────

export type ComplaintStatus =
  | 'pending'
  | 'processing'
  | 'interrupted'
  | 'complete'
  | 'rejected'
  | 'failed'

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type ComplianceRisk = 'LOW' | 'MEDIUM' | 'HIGH'

export interface ClassificationResult {
  product_type: string
  issue_type: string
  severity: SeverityLevel
  compliance_risk: ComplianceRisk
  confidence: number
}

export interface RemediationStep {
  order: number
  action: string
  policy_reference: string
}

export interface RootCauseEvidence {
  rank: number
  summary: string
  citation: { id: string; product: string; issue: string; date: string }
  score: number
}

export interface Complaint {
  id: string
  user_id: string
  scrubbed_text: string | null
  state_code: string
  status: ComplaintStatus
  assigned_team: string | null
  team_id: string | null
  classification: ClassificationResult | null
  root_cause: string | null
  root_cause_evidence: RootCauseEvidence[]
  remediation_steps: RemediationStep[]
  policy_citations: Record<string, unknown> | null
  response_draft: ResponseDraftData | string | null
  audit_verdict: string | null
  explanation: string | null
  review_required: boolean
  review_action: string | null
  reviewer_id: string | null
  reviewer_notes: string | null
  reviewed_at: string | null
  pipeline_stages?: PipelineStage[]
  created_at: string
  updated_at: string
  completed_at: string | null
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

export type PipelineStageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'interrupted'

export interface PipelineStage {
  id: string
  complaint_id: string
  node: string
  status: PipelineStageStatus
  model_used: string | null
  latency_ms: number
  tokens_used: number
  output: Record<string, unknown> | null
  error: string | null
  created_at: string
  updated_at: string
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

export interface PipelineUpdateMessage {
  type: 'pipeline_update'
  node: string
  event: 'started' | 'completed' | 'failed' | 'interrupted'
  payload: Record<string, unknown>
  timestamp: string
}

export interface PipelineDoneMessage {
  type: 'pipeline_done'
  status: ComplaintStatus | 'failed'
  error?: string
}

export interface StateMessage {
  type: 'current_state' | 'final_state'
  complaint: Complaint
  stages: PipelineStage[]
}

export type WSMessage = PipelineUpdateMessage | PipelineDoneMessage | StateMessage | { type: 'ping' }

// ── Audit ─────────────────────────────────────────────────────────────────────

export interface AuditEvent {
  id: string
  user_id: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  details: Record<string, unknown>
  ip_address: string | null
  timestamp: string
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface DashboardStats {
  totals: {
    complaints: number
    users: number
    pending: number
    interrupted_awaiting_review: number
    last_7_days: number
  }
  by_status: Record<string, number>
  by_product: Array<{ product: string | null; count: number }>
  by_severity: Record<string, number>
  daily_volume: Array<{ date: string; count: number }>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  skip: number
}
