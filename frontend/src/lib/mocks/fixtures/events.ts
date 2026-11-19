import { CaseEvent, Phase } from "@/lib/api/types";

const ago = (minutes: number) => new Date(Date.now() - minutes * 60000).toISOString();

function evt(overrides: Partial<CaseEvent> & Pick<CaseEvent, "case_id" | "phase" | "agent" | "summary">): CaseEvent {
  return {
    id: `evt-${Math.random().toString(36).slice(2, 9)}`,
    ts: ago(Math.floor(Math.random() * 100)),
    detail: null,
    ...overrides,
  };
}

// Events for case 1001 (Water Leak - IN_PROGRESS) - full loop
export const events1001: CaseEvent[] = [
  evt({ id: "e1001-01", case_id: "1001", ts: ago(120), agent: "citizen", phase: Phase.message, summary: "Citizen reported: major water leak at Oak St / 5th Ave", detail: { channel: "web", text: "There's a major water leak..." } }),
  evt({ id: "e1001-02", case_id: "1001", ts: ago(119), agent: "orchestrator", phase: Phase.perceive, summary: "Incoming citizen report received and queued", detail: { case_id: "1001" } }),
  evt({ id: "e1001-03", case_id: "1001", ts: ago(118), agent: "intake", phase: Phase.tool_call, summary: "Calling parse_media to analyze report", tool_name: "parse_media", detail: { args: { text: "There's a major water leak...", image_urls: [], language_hint: "en" } } }),
  evt({ id: "e1001-04", case_id: "1001", ts: ago(117), agent: "intake", phase: Phase.tool_result, summary: "parse_media completed: Water category, high confidence", tool_name: "parse_media", detail: { result: { category: "Water", confidence: 0.94, summary: "Major water main burst", visible_damage: ["burst pipe", "flooding"] } } }),
  evt({ id: "e1001-05", case_id: "1001", ts: ago(116), agent: "intake", phase: Phase.tool_call, summary: "Calling geo_lookup to verify location", tool_name: "geo_lookup", detail: { args: { lat: 37.7749, lng: -122.4194, address_text: "Corner of Oak St and 5th Ave" } } }),
  evt({ id: "e1001-06", case_id: "1001", ts: ago(115), agent: "intake", phase: Phase.tool_result, summary: "geo_lookup: Ward 5, Noe Valley Water Office", tool_name: "geo_lookup", detail: { result: { ward_id: "ward-5", ward_name: "Noe Valley", office_id: "office-noe-valley", formatted_address: "Corner of Oak St and 5th Ave, SF" } } }),
  evt({ id: "e1001-07", case_id: "1001", ts: ago(114), agent: "intake", phase: Phase.perceive, summary: "Intake complete: Water burst, Ward 5, confidence=0.94", detail: { confidence: 0.94, category: "Water", missing_info: [] } }),
  evt({ id: "e1001-08", case_id: "1001", ts: ago(113), agent: "triage", phase: Phase.tool_call, summary: "Calling policy_search for water burst policy", tool_name: "policy_search", detail: { args: { query: "water main burst emergency response", department_id: "dept-water", k: 4 } } }),
  evt({ id: "e1001-09", case_id: "1001", ts: ago(112), agent: "triage", phase: Phase.tool_result, summary: "policy_search: Found POL-WATER-BURST-001, SLA 4h", tool_name: "policy_search", detail: { result: [{ chunk_id: "pw001", doc_title: "Water Emergency Response", text: "Active water main burst requires 4h response SLA", sla_hours: 4, escalation_rule: "supervisor_notify_2h", score: 0.97 }] } }),
  evt({ id: "e1001-10", case_id: "1001", ts: ago(111), agent: "triage", phase: Phase.reason, summary: "Triage decision: HIGH urgency, 4h deadline, Dept Water", detail: { urgency: "high", rationale: "Active burst with flooding risk, school nearby", confidence: 0.91 } }),
  evt({ id: "e1001-11", case_id: "1001", ts: ago(110), agent: "planner", phase: Phase.plan, summary: "Plan v1 created: 4-step dispatch and notification plan", detail: { version: 1, steps: 4, risk_tier: "routine" } }),
  evt({ id: "e1001-12", case_id: "1001", ts: ago(108), agent: "action", phase: Phase.tool_call, summary: "Calling ticketing: create emergency water ticket", tool_name: "ticketing", detail: { args: { type: "create_ticket", department_id: "dept-water", priority: "high", description: "Water main burst Oak/5th" } } }),
  evt({ id: "e1001-13", case_id: "1001", ts: ago(107), agent: "action", phase: Phase.tool_result, summary: "Ticket TKT-5521 created, assigned crew-7", tool_name: "ticketing", detail: { result: { ticket_id: "TKT-5521", crew_id: "crew-7", eta_minutes: 20 } } }),
  evt({ id: "e1001-14", case_id: "1001", ts: ago(106), agent: "action", phase: Phase.tool_call, summary: "Calling notify: alerting 47 nearby residents via SMS", tool_name: "notify", detail: { args: { channel: "sms", radius_m: 200, template: "water_alert", vars: { address: "Oak St / 5th Ave" } } } }),
  evt({ id: "e1001-15", case_id: "1001", ts: ago(105), agent: "action", phase: Phase.tool_result, summary: "Notifications sent to 47 residents", tool_name: "notify", detail: { result: { sent: 47, failed: 0 } } }),
  evt({ id: "e1001-16", case_id: "1001", ts: ago(60), agent: "evaluator", phase: Phase.evaluate, summary: "Evaluation: crew dispatched, on-track, confidence=0.88", detail: { on_track: true, confidence: 0.88, checks: { crew_dispatched: true, timeline_met: true } } }),
  evt({ id: "e1001-17", case_id: "1001", ts: ago(30), agent: "citizen", phase: Phase.message, summary: "Citizen update: leak is slowing, crew has arrived", detail: { text: "I can see the repair crew is here, they started working" } }),
  evt({ id: "e1001-18", case_id: "1001", ts: ago(29), agent: "orchestrator", phase: Phase.perceive, summary: "Citizen update received, case status remains IN_PROGRESS", detail: {} }),
  evt({ id: "e1001-19", case_id: "1001", ts: ago(10), agent: "evaluator", phase: Phase.evaluate, summary: "Evaluation: repair in progress, crew on-site", detail: { on_track: true, confidence: 0.95, crew_on_site: true } }),
  evt({ id: "e1001-20", case_id: "1001", ts: ago(5), agent: "orchestrator", phase: Phase.act, summary: "Monitoring active repair, next check in 30 mins", detail: {} }),
];

// Events for case 1002 (Road - AT_RISK) with adaptation
export const events1002: CaseEvent[] = [
  evt({ id: "e1002-01", case_id: "1002", ts: ago(360), agent: "citizen", phase: Phase.message, summary: "Citizen reported: massive pothole on Mission St near 24th", detail: {} }),
  evt({ id: "e1002-02", case_id: "1002", ts: ago(359), agent: "intake", phase: Phase.perceive, summary: "Intake: Roads category, pothole with damage, Ward 9", detail: { confidence: 0.89, category: "Roads" } }),
  evt({ id: "e1002-03", case_id: "1002", ts: ago(358), agent: "triage", phase: Phase.reason, summary: "Triage: MEDIUM urgency, 24h SLA, Road Dept", detail: { urgency: "medium", confidence: 0.86 } }),
  evt({ id: "e1002-04", case_id: "1002", ts: ago(357), agent: "planner", phase: Phase.plan, summary: "Plan v1 created: standard road repair workflow", detail: { version: 1, steps: 4 } }),
  evt({ id: "e1002-05", case_id: "1002", ts: ago(355), agent: "action", phase: Phase.tool_call, summary: "Create road repair ticket TKT-5420", tool_name: "ticketing", detail: { args: { type: "create_ticket", dept: "roads", priority: "medium" } } }),
  evt({ id: "e1002-06", case_id: "1002", ts: ago(354), agent: "action", phase: Phase.tool_result, summary: "TKT-5420 created, assigning nearest crew", tool_name: "ticketing", detail: { result: { ticket_id: "TKT-5420" } } }),
  evt({ id: "e1002-07", case_id: "1002", ts: ago(350), agent: "action", phase: Phase.tool_call, summary: "Assign nearest road crew to TKT-5420", tool_name: "ticketing", detail: { args: { action: "assign_crew", ticket_id: "TKT-5420", crew_id: "nearest" } } }),
  evt({ id: "e1002-08", case_id: "1002", ts: ago(349), agent: "action", phase: Phase.tool_result, summary: "crew-3 assigned, ETA 2 hours", tool_name: "ticketing", detail: { result: { crew_id: "crew-3", eta_hours: 2 } } }),
  evt({ id: "e1002-09", case_id: "1002", ts: ago(180), agent: "evaluator", phase: Phase.evaluate, summary: "Scheduled evaluation: crew check-in overdue by 30 mins", detail: { on_track: false, reason: "crew_no_checkin", deadline_at: ago(60) } }),
  evt({ id: "e1002-10", case_id: "1002", ts: ago(179), agent: "evaluator", phase: Phase.adapt, summary: "Adaptation triggered: crew no-show detected, escalating", reason: "crew-3 missed check-in window, SLA breach imminent", detail: { adaptation: "escalate_crew_noshow", new_plan_version: 2 } }),
  evt({ id: "e1002-11", case_id: "1002", ts: ago(178), agent: "planner", phase: Phase.plan, summary: "Plan v2 created: escalation path via supervisor notify", detail: { version: 2, reason: "crew no-show adaptation" } }),
  evt({ id: "e1002-12", case_id: "1002", ts: ago(60), agent: "action", phase: Phase.tool_call, summary: "Fallback: notify supervisor of SLA breach", tool_name: "notify", detail: { args: { channel: "email", template: "crew_escalation", to: "supervisor@sfroads.gov" } } }),
  evt({ id: "e1002-13", case_id: "1002", ts: ago(59), agent: "action", phase: Phase.tool_result, summary: "Supervisor notified of SLA breach", tool_name: "notify", detail: { result: { sent: true, to: "supervisor@sfroads.gov" } } }),
  evt({ id: "e1002-14", case_id: "1002", ts: ago(30), agent: "orchestrator", phase: Phase.guardrail, summary: "GUARDRAIL: Case flagged AT_RISK — SLA breached 60 mins ago", detail: { rule: "sla_breach_60min", action: "flag_at_risk", case_status: "AT_RISK" } }),
  evt({ id: "e1002-15", case_id: "1002", ts: ago(15), agent: "orchestrator", phase: Phase.act, summary: "AT_RISK: Awaiting supervisor intervention for crew dispatch", detail: {} }),
];

// Events for case 1003 (NEEDS_HUMAN - ambiguous complaint)
export const events1003: CaseEvent[] = [
  evt({ id: "e1003-01", case_id: "1003", ts: ago(45), agent: "citizen", phase: Phase.message, summary: "Citizen reported (Spanish): Loud noise near Golden Gate Park", detail: { text: "Hay un ruido muy fuerte viniendo de un edificio...", language: "es" } }),
  evt({ id: "e1003-02", case_id: "1003", ts: ago(44), agent: "intake", phase: Phase.tool_call, summary: "parse_media: analyzing Spanish language report", tool_name: "parse_media", detail: { args: { language_hint: "es" } } }),
  evt({ id: "e1003-03", case_id: "1003", ts: ago(43), agent: "intake", phase: Phase.tool_result, summary: "parse_media: translated but confidence=0.47 (ambiguous)", tool_name: "parse_media", detail: { result: { translated: "There is a very loud noise from a building near the park", category: "Public Safety", confidence: 0.47, missing_info: ["noise source type", "exact address"] } } }),
  evt({ id: "e1003-04", case_id: "1003", ts: ago(42), agent: "orchestrator", phase: Phase.guardrail, summary: "GUARDRAIL: Confidence 0.47 < threshold 0.65 — requiring human review", detail: { rule: "confidence_threshold", threshold: 0.65, actual: 0.47, action: "needs_human" } }),
  evt({ id: "e1003-05", case_id: "1003", ts: ago(41), agent: "orchestrator", phase: Phase.reason, summary: "Case routed to NEEDS_HUMAN queue — awaiting officer categorization", detail: { reason: "low_confidence_ambiguous", confidence: 0.47 } }),
  evt({ id: "e1003-06", case_id: "1003", ts: ago(40), agent: "system", phase: Phase.message, summary: "Officer notification sent: human review required for case 1003", detail: { notified_at: ago(40) } }),
  evt({ id: "e1003-07", case_id: "1003", ts: ago(2), agent: "system", phase: Phase.evaluate, summary: "Still awaiting human officer review (38 mins elapsed)", detail: { wait_minutes: 38 } }),
];

// Events for case 1004 (AWAITING_CONFIRMATION - sanitation)
export const events1004: CaseEvent[] = [
  evt({ id: "e1004-01", case_id: "1004", ts: ago(180), agent: "citizen", phase: Phase.message, summary: "Citizen: 2 weeks missed garbage collection on Hayes St 400 block", detail: {} }),
  evt({ id: "e1004-02", case_id: "1004", ts: ago(179), agent: "intake", phase: Phase.perceive, summary: "Intake: Sanitation/missed collection, Ward 5, confidence=0.92", detail: { confidence: 0.92, category: "Sanitation" } }),
  evt({ id: "e1004-03", case_id: "1004", ts: ago(178), agent: "triage", phase: Phase.reason, summary: "Triage: MEDIUM urgency, 48h SLA, Sanitation Dept", detail: { urgency: "medium", confidence: 0.90 } }),
  evt({ id: "e1004-04", case_id: "1004", ts: ago(177), agent: "planner", phase: Phase.plan, summary: "Plan: schedule emergency pickup + confirm with citizen", detail: { version: 1, steps: 3 } }),
  evt({ id: "e1004-05", case_id: "1004", ts: ago(176), agent: "action", phase: Phase.tool_call, summary: "scheduler: booking emergency pickup for Hayes 400 block", tool_name: "scheduler", detail: { args: { type: "emergency_pickup", address: "400 Hayes St", earliest: "tomorrow 8am" } } }),
  evt({ id: "e1004-06", case_id: "1004", ts: ago(175), agent: "action", phase: Phase.tool_result, summary: "Emergency pickup scheduled for tomorrow 8am", tool_name: "scheduler", detail: { result: { scheduled_at: "tomorrow 8am", crew: "san-team-b" } } }),
  evt({ id: "e1004-07", case_id: "1004", ts: ago(170), agent: "action", phase: Phase.tool_call, summary: "notify: emailing citizen with resolution plan", tool_name: "notify", detail: { args: { channel: "email", template: "sanitation_scheduled", vars: { pickup_time: "tomorrow 8am" } } } }),
  evt({ id: "e1004-08", case_id: "1004", ts: ago(169), agent: "action", phase: Phase.tool_result, summary: "Citizen email sent: emergency pickup tomorrow 8am", tool_name: "notify", detail: { result: { sent: true } } }),
  evt({ id: "e1004-09", case_id: "1004", ts: ago(10), agent: "evaluator", phase: Phase.evaluate, summary: "Evaluation: pickup scheduled, awaiting citizen confirmation", detail: { on_track: true, waiting_confirmation: true } }),
  evt({ id: "e1004-10", case_id: "1004", ts: ago(10), agent: "orchestrator", phase: Phase.message, summary: "Citizen confirmation request sent via chat", detail: {} }),
];

// Events for case 1005 (CLOSED - streetlight repair)
export const events1005: CaseEvent[] = [
  evt({ id: "e1005-01", case_id: "1005", ts: ago(2880), agent: "citizen", phase: Phase.message, summary: "Streetlight flickering continuously on Chestnut St", detail: { text: "Streetlight flickering" } }),
  evt({ id: "e1005-02", case_id: "1005", ts: ago(2870), agent: "triage", phase: Phase.reason, summary: "Triage: Electricity & Power, low urgency, 48h SLA", detail: { urgency: "low" } }),
  evt({ id: "e1005-03", case_id: "1005", ts: ago(2800), agent: "action", phase: Phase.act, summary: "Maintenance ticket TKT-5201 created and assigned crew-elec-2", tool_name: "ticketing", detail: { ticket_id: "TKT-5201" } }),
  evt({ id: "e1005-04", case_id: "1005", ts: ago(1500), agent: "action", phase: Phase.act, summary: "Crew replaced LED fixture and verified lumination", tool_name: "ticketing", detail: { repaired: true } }),
  evt({ id: "e1005-05", case_id: "1005", ts: ago(1440), agent: "evaluator", phase: Phase.evaluate, summary: "Evaluator: Work verified and citizen closure notification sent", tool_name: "notify", detail: { status: "CLOSED" } }),
];

// Events for case 1042 (CRITICAL - downed power line near school)
export const events1042: CaseEvent[] = [
  evt({ id: "e1042-01", case_id: "1042", ts: ago(30), agent: "citizen", phase: Phase.message, summary: "URGENT: Citizen reported downed power line near Sunset Elementary", detail: { text: "URGENT: Downed power line near Sunset Elementary School on Irving St. Sparking and smoking!", urgency: "critical" } }),
  evt({ id: "e1042-02", case_id: "1042", ts: ago(29), agent: "orchestrator", phase: Phase.perceive, summary: "Critical report received - elevated processing priority", detail: { priority: "critical" } }),
  evt({ id: "e1042-03", case_id: "1042", ts: ago(28), agent: "intake", phase: Phase.tool_call, summary: "parse_media: analyzing images + text for power line hazard", tool_name: "parse_media", detail: { args: { text: "URGENT: Downed power line...", image_urls: ["img1.jpg", "img2.jpg"] } } }),
  evt({ id: "e1042-04", case_id: "1042", ts: ago(27), agent: "intake", phase: Phase.tool_result, summary: "parse_media: Electricity/CRITICAL, downed live wire, school nearby", tool_name: "parse_media", detail: { result: { category: "Electricity", confidence: 0.98, damage: ["downed_power_line", "sparking", "smoke"], nearby_sensitive: ["school_50m"] } } }),
  evt({ id: "e1042-05", case_id: "1042", ts: ago(27), agent: "intake", phase: Phase.tool_call, summary: "geo_lookup: Mapping incident location", tool_name: "geo_lookup", detail: { args: { lat: 37.7633, lng: -122.4836 } } }),
  evt({ id: "e1042-06", case_id: "1042", ts: ago(26), agent: "intake", phase: Phase.tool_result, summary: "geo_lookup: Ward 7 Sunset, school confirmed 50m away", tool_name: "geo_lookup", detail: { result: { ward_id: "ward-7", ward_name: "Sunset", nearby_sensitive_sites: ["Sunset Elementary School 50m"] } } }),
  evt({ id: "e1042-07", case_id: "1042", ts: ago(25), agent: "triage", phase: Phase.tool_call, summary: "policy_search: emergency protocol for school-adjacent electrical hazard", tool_name: "policy_search", detail: { args: { query: "downed power line school evacuation protocol", k: 4 } } }),
  evt({ id: "e1042-08", case_id: "1042", ts: ago(24), agent: "triage", phase: Phase.tool_result, summary: "policy_search: POL-SCHOOL-SAFETY-003 — mandatory evacuation within 100m", tool_name: "policy_search", detail: { result: [{ doc_title: "School Safety Emergency Protocol", text: "Downed electrical line within 100m of school requires immediate 100m evacuation and utility shutoff", sla_hours: 0.5, escalation_rule: "officer_approval_required", score: 0.99 }] } }),
  evt({ id: "e1042-09", case_id: "1042", ts: ago(23), agent: "triage", phase: Phase.reason, summary: "CRITICAL triage: immediate response, 1h deadline, officer approval needed for evacuation", detail: { urgency: "critical", confidence: 0.98, rationale: "Live electrical hazard + school proximity = critical" } }),
  evt({ id: "e1042-10", case_id: "1042", ts: ago(22), agent: "orchestrator", phase: Phase.guardrail, summary: "GUARDRAIL: Risk tier CRITICAL — step s1 requires officer approval before execution", detail: { rule: "critical_risk_approval", step: "s1", action: "block_pending_approval" } }),
  evt({ id: "e1042-11", case_id: "1042", ts: ago(21), agent: "planner", phase: Phase.plan, summary: "Plan v1: evacuation + utility shutoff + emergency dispatch (pending officer approval)", detail: { version: 1, blocked_on_approval: "appr-001" } }),
  evt({ id: "e1042-12", case_id: "1042", ts: ago(20), agent: "system", phase: Phase.message, summary: "APPROVAL REQUEST sent to on-duty officer: emergency evacuation authorization needed", detail: { approval_id: "appr-001", urgency: "critical", timeout_minutes: 5 } }),
  evt({ id: "e1042-13", case_id: "1042", ts: ago(19), agent: "action", phase: Phase.tool_call, summary: "notify: alerting school administration via email (pre-approval)", tool_name: "notify", detail: { args: { channel: "email", to: "sunset-elementary@sfusd.edu", template: "electrical_hazard_alert" } } }),
  evt({ id: "e1042-14", case_id: "1042", ts: ago(18), agent: "action", phase: Phase.tool_result, summary: "School administration alerted", tool_name: "notify", detail: { result: { sent: true } } }),
  evt({ id: "e1042-15", case_id: "1042", ts: ago(1), agent: "orchestrator", phase: Phase.evaluate, summary: "Waiting for officer approval (approval_id: appr-001) — 19 mins elapsed", detail: { waiting_approval: "appr-001", elapsed_minutes: 19 } }),
];

export const allEvents: Record<string, CaseEvent[]> = {
  "1001": events1001,
  "1002": events1002,
  "1003": events1003,
  "1004": events1004,
  "1005": [],
  "1042": events1042,
};
