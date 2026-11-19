// CivicPilot API Types - derived from docs/CONTRACT.md

export enum CaseStatus {
  NEW = "NEW",
  INTAKE = "INTAKE",
  TRIAGED = "TRIAGED",
  PLANNED = "PLANNED",
  IN_PROGRESS = "IN_PROGRESS",
  AT_RISK = "AT_RISK",
  NEEDS_HUMAN = "NEEDS_HUMAN",
  AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION",
  CLOSED = "CLOSED",
  REOPENED = "REOPENED",
}

export enum Urgency {
  critical = "critical",
  high = "high",
  medium = "medium",
  low = "low",
}

export enum Phase {
  perceive = "perceive",
  reason = "reason",
  plan = "plan",
  act = "act",
  evaluate = "evaluate",
  adapt = "adapt",
  guardrail = "guardrail",
  tool_call = "tool_call",
  tool_result = "tool_result",
  message = "message",
}

export enum StepStatus {
  pending = "pending",
  running = "running",
  done = "done",
  failed = "failed",
  skipped = "skipped",
  awaiting_approval = "awaiting_approval",
}

export enum RiskTier {
  routine = "routine",
  sensitive = "sensitive",
  critical = "critical",
}

export interface Location {
  address: string;
  lat: number | null;
  lng: number | null;
}

export interface PlanStep {
  id: string;
  title: string;
  tool: string;
  args: Record<string, unknown>;
  depends_on: string[];
  due_at: string | null;
  fallback: { tool: string; args: Record<string, unknown> } | null;
  risk_tier: RiskTier;
  status: StepStatus;
  result: Record<string, unknown> | null;
}

export interface Plan {
  version: number;
  steps: PlanStep[];
}

export interface Ticket {
  id: string;
  department_id: string;
  status: string;
  crew_id: string | null;
  priority: string;
  due_at: string;
  notes: string[];
}

export interface Approval {
  id: string;
  case_id: string;
  step_id?: string | null;
  risk_tier: RiskTier;
  summary?: string;
  rationale?: string | null;
  detail?: Record<string, unknown> | null;
  created_at?: string;
  requested_at?: string;
  status: "pending" | "approved" | "rejected";
  officer?: string;
  note?: string;
  decided_at?: string;
}

export interface CitizenInfo {
  contact_masked: string;
  language: string;
}

export interface RawInput {
  text: string;
  image_urls: string[];
  lat: number | null;
  lng: number | null;
  address_text: string | null;
  channel: "web" | "chat" | "voice" | "email";
}

export interface IntakeData {
  category: string;
  summary: string;
  location: Location;
  visible_damage: string[];
  nearby_sensitive_sites: string[];
  language_detected: string;
  missing_info: string[];
  confidence: number;
}

export interface TriageData {
  urgency: Urgency;
  department_id: string;
  ward_id: string;
  office_id: string;
  deadline_hours: number;
  policy_refs: string[];
  rationale: string;
  confidence: number;
}

export interface CaseFlags {
  needs_human: boolean;
  human_reason: string | null;
  reopen_count: number;
  merged_into: string | null;
  duplicate_of: string[];
}

export interface CaseState {
  id: string;
  created_at: string;
  updated_at: string;
  status: CaseStatus;
  deadline_at: string | null;
  citizen: CitizenInfo;
  raw: RawInput;
  intake: IntakeData | null;
  triage: TriageData | null;
  plan: Plan | null;
  tickets: Ticket[];
  flags: CaseFlags;
}

export interface CaseEvent {
  id: string;
  case_id: string;
  ts: string;
  agent:
    | "orchestrator"
    | "intake"
    | "triage"
    | "planner"
    | "action"
    | "evaluator"
    | "sandbox"
    | "citizen"
    | "officer"
    | "system";
  phase: Phase;
  summary: string;
  detail: Record<string, unknown> | null;
  tool_name?: string;
  reason?: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface PaginatedCases {
  cases: CaseState[];
  total: number;
  page: number;
  per_page: number;
}

export interface MetricsSummary {
  total_cases: number;
  cases_by_status: Record<string, number>;
  cases_by_department: Record<string, number>;
  cases_by_urgency: Record<string, number>;
  avg_time_to_first_action_sec: number;
  open_approvals: number;
  active_tickets: number;
}

export interface EvalRun {
  id: string;
  status: "pending" | "running" | "done" | "completed" | "failed";
  started_at: string;
  completed_at?: string;
  results?: Array<{ metric: string; score: number; details?: Record<string, unknown> }> | Record<string, unknown>;
}
