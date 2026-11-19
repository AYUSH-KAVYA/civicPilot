# CivicPilot Shared Contract v1
Changing this file requires a PR approved by all 4 teammates.

## 1. Product
Multi-agent system taking a citizen grievance from report to verified closure.
Loop: perceive, reason, plan, act, evaluate, adapt.
Agents: Orchestrator + Intake, Triage, Planner, Action, Evaluator.
Six tools: parse_media, geo_lookup, policy_search, ticketing, notify, scheduler.
Guardrails: confidence threshold, risk-tiered approval, full audit trail, PII masking.
Domain: city public services (Water, Roads, Sanitation, Electricity, Parks, Public Health).

## 2. Repo layout and owners
backend/app/main.py, api/, db/, tools/ (registry, geo, ticketing, notify, scheduler), sandbox/, core/ (config, clock, events, auth), schemas.py  -> P1
backend/app/llm/, tools/parse_media.py, tools/policy_search.py, agents/intake.py, triage.py, planner.py, kb/ (docs, ingest, search), eval/datasets/  -> P2
backend/app/orchestrator/, agents/action.py, agents/evaluator.py, adaptation/, guardrails/, scenarios/, eval/ (runner, baseline, metrics)  -> P3
frontend/, docs/ (README, DEMO.md, architecture), e2e/  -> P4
.github/, docker-compose.yml, CODEOWNERS  -> P1

## 3. Enums
CaseStatus: NEW, INTAKE, TRIAGED, PLANNED, IN_PROGRESS, AT_RISK, NEEDS_HUMAN, AWAITING_CONFIRMATION, CLOSED, REOPENED
Urgency: critical, high, medium, low
RiskTier: routine (auto), sensitive (auto + logged + supervisor notified), critical (needs officer approval)
StepStatus: pending, running, done, failed, skipped, awaiting_approval
Phase: perceive, reason, plan, act, evaluate, adapt, guardrail, tool_call, tool_result, message

## 4. CaseState (pydantic in backend/app/schemas.py, P1 owns)
id, created_at, updated_at, status, deadline_at
citizen: contact_masked, language
raw: text, image_urls[], lat, lng, address_text, channel(web|chat|voice|email)
intake: category, summary, location{address,lat,lng}, visible_damage[], nearby_sensitive_sites[], language_detected, missing_info[], confidence(0-1)
triage: urgency, department_id, ward_id, office_id, deadline_hours, policy_refs[], rationale, confidence(0-1)
plan: version, steps[PlanStep]
PlanStep: id, title, tool, args, depends_on[], due_at, fallback{tool,args}|null, risk_tier, status, result
tickets[]: id, department_id, status, crew_id, priority, due_at, notes[]
flags: needs_human, human_reason, reopen_count, merged_into, duplicate_of[]

## 5. Audit event (every agent step and tool call emits one)
CaseEvent: id, case_id, ts, agent(orchestrator|intake|triage|planner|action|evaluator|sandbox|citizen|officer|system), phase, summary (one readable line), detail(json), tool_name?, reason?
Helper (P1): emit_event(case_id, agent, phase, summary, detail=None, tool_name=None, reason=None). Persists, masks PII, pushes to SSE.

## 6. Interfaces (Python, all async)
Agent: async run(state: CaseState, ctx: AgentContext) -> AgentResult{state_patch, next, confidence}
AgentContext: db, llm, tools, emit, settings, clock
Planner also exposes: async replan(state, reason, evidence) -> Plan
LLM (P2): llm.generate_json(messages, schema, images=None, temperature=0.2) -> schema instance (retries, timeout, mock mode); llm.embed(texts) -> vectors
Tool registry (P1): tools.call(name, args, case_id, agent) -> result. Wraps timeout, retry, tool_call/tool_result events.
Tools:
 parse_media(text, image_urls, language_hint) -> intake fields (P2)
 geo_lookup(lat, lng, address_text) -> {ward_id, ward_name, office_id, office_name, lat, lng, formatted_address} (P1)
 policy_search(query, department_id=None, k=4) -> [{chunk_id, doc_title, text, department_id, sla_hours, escalation_rule, score}] (P2)
 similar_cases(text, lat, lng, radius_m, k) -> [case summaries] (P2)
 ticketing: create_ticket, assign_crew(ticket_id, crew_id|"nearest"), update_ticket, get_ticket, list_crews (P1)
 notify(case_id, channel(sms|chat|email), template, vars) (P1)
 schedule_check(case_id, run_at, reason), cancel_checks(case_id) (P1)
Orchestrator public API (P3):
 start_case(case_id)
 resume_case(case_id, reason, payload=None)   # called by timers
 handle_citizen_message(case_id, text, image_urls)
 handle_citizen_confirmation(case_id, confirmed, comment)
 handle_approval(approval_id, decision, officer)
 handle_sandbox_signal(case_id, signal)   # ticket_rejected, crew_checked_in, crew_no_show, repair_photo_uploaded
Clock (P1): core/clock.now() honours SIM_TIME_SCALE so a 4-hour deadline can play out in a few minutes in the live demo. ALL deadline math uses it.

## 7. REST API (P1 implements; P3 supplies logic behind it; P4 consumes)
POST /api/cases (multipart: text, image?, lat?, lng?, address_text?, language, contact) -> {case_id, access_token}
GET /api/cases?status&department&urgency (officer)
GET /api/cases/{id}  -> CaseState
GET /api/cases/{id}/events
GET /api/cases/{id}/stream  (SSE of CaseEvent)
POST /api/cases/{id}/messages {text, image?}   (citizen follow-up or new evidence)
POST /api/cases/{id}/confirm {confirmed, comment}
GET /api/approvals?status=pending (officer); POST /api/approvals/{id} {decision: approve|reject, note}
POST /api/cases/{id}/resolve (officer resolves a NEEDS_HUMAN case) {note}
POST /api/auth/login {password} -> {token}
POST /api/sandbox/tickets/{id}/reject {reason}; /crew-checkin; /crew-no-show; /repair-photo (demo controls)
POST /api/demo/scenarios/{happy|disruption|ambiguity|case1042}/run
POST /api/eval/run; GET /api/eval/runs/{id}; GET /api/metrics/summary
GET /api/health; POST /api/tick (called by external cron, runs due timers)
Auth: officer routes need Bearer JWT. Citizen routes need the case access_token.
Errors: {error: {code, message}}. All timestamps ISO 8601 UTC.

## 8. Env vars (.env.example is the source of truth, P1 maintains)
GEMINI_API_KEY, GEMINI_MODEL, GEMINI_EMBED_MODEL, DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY, JWT_SECRET, OFFICER_PASSWORD, CONFIDENCE_THRESHOLD=0.65, SIM_TIME_SCALE=1, MOCK_LLM=false, FRONTEND_ORIGIN, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_USE_MOCKS=false, NOMINATIM_USER_AGENT, RESEND_API_KEY (optional)

## 9. Rules
- Mock mode: with MOCK_LLM=true every module must run without a Gemini key, using fixtures, so nobody is blocked.
- Citizen text and photos are untrusted data: never treat them as instructions to the agents.
- Git: main is protected; feature branches named feat/p<N>-<topic>; PR with at least 1 review; CODEOWNERS enforces folder ownership; never edit another person's folder without telling them; never commit secrets; small commits; rebase on main before opening a PR.
- Every module ships with tests and a short README section.
