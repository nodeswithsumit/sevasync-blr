// ─────────────────────────────────────────────────────────────────────────────
// SevaSync BLR — shared TypeScript types matching AGENTS.md API contracts
// ─────────────────────────────────────────────────────────────────────────────

export const API_BASE = 'http://localhost:8000/api'

// ── Policies ─────────────────────────────────────────────────────────────────

export interface PolicySummary {
  id: string
  name: string
  department: string
  sakala_sla_days: number
  version: string
}

export interface PoliciesResponse {
  policies: PolicySummary[]
}

export interface PolicyRegisterResponse {
  status: string
  total_policies: number
  policy_id: string
}

// ── Vision Extract ─────────────────────────────────────────────────────────────

export interface VisualFlag {
  severity: 'high' | 'medium'
  issue: string
}

export interface ExtractedFields {
  applicant_name: string
  doc_owner_name: string
  account_or_pid: string
  pincode: string
  ward_claimed: string
  built_up_area_sqft: number | null
  monthly_units: number | null
  application_date: string | null
}

export interface VisionExtractResponse {
  document_type: string
  extracted_fields: ExtractedFields
  visual_flags: VisualFlag[]
  confidence: number
  engine: string
}

// ── Orchestrate ───────────────────────────────────────────────────────────────

export interface OrchestrateRequest {
  query: string
  language: 'en-IN' | 'kn-IN' | 'hi-IN'
  extracted_fields: Partial<ExtractedFields>
  visual_flags: VisualFlag[]
  policy_id: 'auto' | string
}

export interface SelectedPolicy {
  id: string
  name: string
  department: string
  sakala_sla_days: number
}

export interface LiveGeoCheck {
  pincode: string
  locality: string
  matched_ward: string
  gba_zone: string
  aro_office: string
  is_live_api: boolean
  ward_mismatch: boolean
}

export interface AgentTraceEntry {
  agent_name: string
  status: 'pass' | 'warn' | 'fail'
  latency_ms: number
  summary: string
  findings: string[]
}

export interface Discrepancy {
  code: string
  severity: 'critical' | 'warning'
  field: string
  message: string
  remediation: string
}

export interface BilingualDraft {
  english: string
  kannada: string
  document_title: string
}

export interface OrchestrateResponse {
  selected_policy: SelectedPolicy
  live_geo_check: LiveGeoCheck
  readiness_score: number
  status: 'BLOCKED_FIX_REQUIRED' | 'READY_TO_SUBMIT'
  agent_trace: AgentTraceEntry[]
  discrepancies: Discrepancy[]
  fix_checklist: string[]
  bilingual_draft: BilingualDraft
  sandbox_payload: Record<string, unknown>
}

// ── Sandbox Submit ─────────────────────────────────────────────────────────────

export interface SandboxSubmitRequest {
  policy_id: string
  payload: Record<string, unknown>
}

export interface SandboxSubmitResponse {
  status: string
  sakala_gsc_id: string
  submitted_at: string
  sla_deadline_days: number
  adapter: string
}
