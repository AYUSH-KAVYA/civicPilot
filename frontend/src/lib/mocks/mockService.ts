import {
  CaseState,
  CaseEvent,
  Approval,
  PaginatedCases,
  CaseStatus,
  Urgency,
  Phase,
  StepStatus,
  RiskTier,
} from "@/lib/api/types";
import { mockCases } from "./fixtures/cases";
import {
  events1001,
  events1002,
  events1003,
  events1004,
  events1005,
  events1042,
} from "./fixtures/events";
import { mockApprovals } from "./fixtures/approvals";

class MockDataStore {
  private cases: CaseState[] = JSON.parse(JSON.stringify(mockCases));
  private eventsMap: Record<string, CaseEvent[]> = {
    "1001": JSON.parse(JSON.stringify(events1001)),
    "1002": JSON.parse(JSON.stringify(events1002)),
    "1003": JSON.parse(JSON.stringify(events1003)),
    "1004": JSON.parse(JSON.stringify(events1004)),
    "1005": JSON.parse(JSON.stringify(events1005)),
    "1042": JSON.parse(JSON.stringify(events1042)),
  };
  private approvals: Approval[] = JSON.parse(JSON.stringify(mockApprovals));
  private eventListeners: Record<string, ((event: CaseEvent) => void)[]> = {};

  public subscribe(caseId: string, listener: (event: CaseEvent) => void) {
    if (!this.eventListeners[caseId]) this.eventListeners[caseId] = [];
    this.eventListeners[caseId].push(listener);
    return () => {
      this.eventListeners[caseId] = this.eventListeners[caseId].filter((l) => l !== listener);
    };
  }

  public emitEvent(
    caseId: string,
    event: Omit<CaseEvent, "id" | "ts" | "case_id"> & { id?: string; ts?: string; case_id?: string }
  ): CaseEvent {
    const fullEvent: CaseEvent = {
      id: event.id || `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      case_id: caseId,
      ts: event.ts || new Date().toISOString(),
      agent: event.agent,
      phase: event.phase,
      summary: event.summary,
      detail: event.detail || null,
      tool_name: event.tool_name,
      reason: event.reason,
    };

    if (!this.eventsMap[caseId]) {
      this.eventsMap[caseId] = [];
    }
    this.eventsMap[caseId].push(fullEvent);

    const listeners = this.eventListeners[caseId] || [];
    listeners.forEach((fn) => fn(fullEvent));
    return fullEvent;
  }

  public listCases(params?: {
    status?: string;
    department?: string;
    urgency?: string;
    page?: number;
    per_page?: number;
    search?: string;
  }): PaginatedCases {
    let filtered = [...this.cases];
    if (params?.status && params.status !== "ALL") {
      filtered = filtered.filter((c) => c.status === params.status);
    }
    if (params?.department && params.department !== "ALL") {
      const targetDept = params.department.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.triage?.department_id?.toLowerCase() === targetDept ||
          (c.intake?.category && c.intake.category.toLowerCase() === targetDept)
      );
    }
    if (params?.urgency && params.urgency !== "ALL") {
      filtered = filtered.filter((c) => c.triage?.urgency === params.urgency);
    }
    if (params?.search) {
      const q = params.search.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.id.includes(q) ||
          c.intake?.summary.toLowerCase().includes(q) ||
          c.raw.text.toLowerCase().includes(q) ||
          c.intake?.location.address.toLowerCase().includes(q)
      );
    }

    const page = params?.page || 1;
    const per_page = params?.per_page || 50;
    const total = filtered.length;
    const start = (page - 1) * per_page;
    const paginated = filtered.slice(start, start + per_page);

    return {
      cases: paginated,
      total,
      page,
      per_page,
    };
  }

  public getCase(id: string): CaseState | null {
    return this.cases.find((c) => c.id === id) || null;
  }

  public getCaseEvents(id: string): CaseEvent[] {
    return this.eventsMap[id] || [];
  }

  public createCase(data: {
    text: string;
    image_urls?: string[];
    lat?: number;
    lng?: number;
    address_text?: string;
    language?: string;
    contact?: string;
    channel?: "web" | "chat" | "voice" | "email";
  }): { case_id: string; access_token: string } {
    const id = `${Math.floor(1000 + Math.random() * 9000)}`;
    const access_token = `token_${Math.random().toString(36).slice(2, 12)}`;
    const nowIso = new Date().toISOString();

    const category = data.text.toLowerCase().includes("water")
      ? "Water"
      : data.text.toLowerCase().includes("light") || data.text.toLowerCase().includes("wire")
      ? "Electricity"
      : data.text.toLowerCase().includes("pot") || data.text.toLowerCase().includes("road")
      ? "Roads"
      : data.text.toLowerCase().includes("trash") || data.text.toLowerCase().includes("garbage")
      ? "Sanitation"
      : "General";

    const urgency = data.text.toLowerCase().includes("urgent") || data.text.toLowerCase().includes("danger")
      ? Urgency.critical
      : Urgency.high;

    const newCase: CaseState = {
      id,
      created_at: nowIso,
      updated_at: nowIso,
      status: CaseStatus.IN_PROGRESS,
      deadline_at: new Date(Date.now() + 4 * 3600000).toISOString(),
      citizen: {
        contact_masked: data.contact ? data.contact.replace(/\d(?=\d{4})/g, "*") : "+1***-***-1234",
        language: data.language || "en",
      },
      raw: {
        text: data.text,
        image_urls: data.image_urls || [],
        lat: data.lat || 37.7749,
        lng: data.lng || -122.4194,
        address_text: data.address_text || "San Francisco, CA",
        channel: data.channel || "web",
      },
      intake: {
        category,
        summary: data.text.slice(0, 120),
        location: {
          address: data.address_text || "Downtown Civic Center, SF",
          lat: data.lat || 37.7749,
          lng: data.lng || -122.4194,
        },
        visible_damage: ["Reported public infrastructure defect"],
        nearby_sensitive_sites: ["Transit hub nearby"],
        language_detected: data.language || "en",
        missing_info: [],
        confidence: 0.92,
      },
      triage: {
        urgency,
        department_id: `dept-${category.toLowerCase()}`,
        ward_id: "ward-6",
        office_id: "office-central",
        deadline_hours: 4,
        policy_refs: [`POL-${category.toUpperCase()}-01`],
        rationale: "Automated triage classification matching municipality standard response guidelines.",
        confidence: 0.89,
      },
      plan: {
        version: 1,
        steps: [
          {
            id: "s1",
            title: `Dispatch ${category} response crew`,
            tool: "ticketing",
            args: { dept: category.toLowerCase(), priority: urgency },
            depends_on: [],
            due_at: new Date(Date.now() + 1800000).toISOString(),
            fallback: null,
            risk_tier: RiskTier.routine,
            status: StepStatus.running,
            result: null,
          },
          {
            id: "s2",
            title: "Notify ward supervisor and citizen",
            tool: "notify",
            args: { channel: "sms", template: "dispatch_confirmation" },
            depends_on: ["s1"],
            due_at: new Date(Date.now() + 3600000).toISOString(),
            fallback: null,
            risk_tier: RiskTier.routine,
            status: StepStatus.pending,
            result: null,
          },
        ],
      },
      tickets: [
        {
          id: `TKT-${Math.floor(5000 + Math.random() * 5000)}`,
          department_id: `dept-${category.toLowerCase()}`,
          status: "dispatched",
          crew_id: "crew-1",
          priority: urgency,
          due_at: new Date(Date.now() + 3600000).toISOString(),
          notes: ["Initial crew auto-assigned"],
        },
      ],
      flags: {
        needs_human: false,
        human_reason: null,
        reopen_count: 0,
        merged_into: null,
        duplicate_of: [],
      },
    };

    this.cases.unshift(newCase);
    this.eventsMap[id] = [
      {
        id: `evt-${Date.now()}-1`,
        case_id: id,
        ts: nowIso,
        agent: "citizen",
        phase: Phase.message,
        summary: `Citizen filed grievance: "${data.text.slice(0, 60)}..."`,
        detail: { channel: data.channel || "web" },
      },
      {
        id: `evt-${Date.now()}-2`,
        case_id: id,
        ts: nowIso,
        agent: "orchestrator",
        phase: Phase.perceive,
        summary: "Perceive: Report received, validated, and intake pipeline initiated",
        detail: {},
      },
      {
        id: `evt-${Date.now()}-3`,
        case_id: id,
        ts: nowIso,
        agent: "intake",
        phase: Phase.tool_call,
        summary: "parse_media: Extracted grievance intent and context",
        tool_name: "parse_media",
        detail: { confidence: 0.92, category },
      },
      {
        id: `evt-${Date.now()}-4`,
        case_id: id,
        ts: nowIso,
        agent: "triage",
        phase: Phase.reason,
        summary: `Reason: Classified as ${category} (${urgency} urgency, 4h deadline)`,
        detail: { rationale: "Automated policy evaluation" },
      },
      {
        id: `evt-${Date.now()}-5`,
        case_id: id,
        ts: nowIso,
        agent: "planner",
        phase: Phase.plan,
        summary: "Plan: Generated 2-step resolution plan v1",
        detail: { steps: 2 },
      },
      {
        id: `evt-${Date.now()}-6`,
        case_id: id,
        ts: nowIso,
        agent: "action",
        phase: Phase.act,
        summary: "Act: Dispatched emergency response crew and ticket created",
        tool_name: "ticketing",
        detail: { ticket_id: newCase.tickets[0].id },
      },
    ];

    return { case_id: id, access_token };
  }

  public addCitizenMessage(caseId: string, text: string): CaseEvent {
    const c = this.getCase(caseId);
    const event = this.emitEvent(caseId, {
      agent: "citizen",
      phase: Phase.message,
      summary: `Citizen update: "${text.slice(0, 80)}"`,
      detail: { text },
    });

    // Simulate adaptive response
    setTimeout(() => {
      this.emitEvent(caseId, {
        agent: "orchestrator",
        phase: Phase.adapt,
        summary: "Adaptation Rule (c): Supplemental evidence evaluated and attached to work order",
        detail: { new_evidence: text },
        reason: "Citizen provided follow-up details",
      });
      if (c) {
        c.updated_at = new Date().toISOString();
      }
    }, 1200);

    return event;
  }

  public confirmCase(caseId: string, confirmed: boolean, comment?: string): CaseState {
    const c = this.getCase(caseId);
    if (!c) throw new Error("Case not found");

    if (confirmed) {
      c.status = CaseStatus.CLOSED;
      c.updated_at = new Date().toISOString();
      this.emitEvent(caseId, {
        agent: "citizen",
        phase: Phase.evaluate,
        summary: `Citizen confirmed closure: ${comment || "Satisfied with resolution"}`,
        detail: { confirmed: true, comment },
      });
      this.emitEvent(caseId, {
        agent: "orchestrator",
        phase: Phase.evaluate,
        summary: "Case officially CLOSED with verified citizen confirmation",
        detail: { status: "CLOSED" },
      });
    } else {
      c.status = CaseStatus.REOPENED;
      c.flags.reopen_count += 1;
      c.flags.needs_human = true;
      c.flags.human_reason = `Citizen disputed resolution: ${comment || "Issue persists"}`;
      c.updated_at = new Date().toISOString();

      this.emitEvent(caseId, {
        agent: "citizen",
        phase: Phase.adapt,
        summary: `Citizen DISPUTED resolution: "${comment || "Work incomplete"}"`,
        detail: { confirmed: false, comment },
        reason: "Citizen dispute",
      });
      this.emitEvent(caseId, {
        agent: "orchestrator",
        phase: Phase.adapt,
        summary: "Adaptation Rule (e): Case REOPENED and routed to NEEDS_HUMAN queue for officer investigation",
        detail: { reopen_count: c.flags.reopen_count },
        reason: "Citizen dispute closure trigger",
      });
    }

    return c;
  }

  public resolveCase(caseId: string, note: string): CaseState {
    const c = this.getCase(caseId);
    if (!c) throw new Error("Case not found");

    c.flags.needs_human = false;
    c.status = CaseStatus.IN_PROGRESS;
    c.updated_at = new Date().toISOString();

    this.emitEvent(caseId, {
      agent: "officer",
      phase: Phase.reason,
      summary: `Officer intervention: Grievance clarified and unblocked: "${note}"`,
      detail: { note },
      reason: "Human-in-the-loop manual resolution",
    });

    this.emitEvent(caseId, {
      agent: "orchestrator",
      phase: Phase.plan,
      summary: "Autonomous execution resumed following officer override",
      detail: {},
    });

    return c;
  }

  public listApprovals(status?: string): Approval[] {
    if (!status) return this.approvals;
    return this.approvals.filter((a) => a.status === status);
  }

  public handleApproval(id: string, decision: "approve" | "reject", note?: string): Approval {
    const appr = this.approvals.find((a) => a.id === id);
    if (!appr) throw new Error("Approval not found");

    appr.status = decision === "approve" ? "approved" : "rejected";
    appr.officer = "Officer Chen (Badge #409)";
    appr.note = note || `Officer decided: ${decision}`;
    appr.decided_at = new Date().toISOString();

    const c = this.getCase(appr.case_id);
    if (c) {
      c.updated_at = new Date().toISOString();
      const step = c.plan?.steps.find((s) => s.id === appr.step_id);
      if (step) {
        step.status = decision === "approve" ? StepStatus.done : StepStatus.failed;
        step.result = { approval_id: id, decision, note };
      }

      this.emitEvent(appr.case_id, {
        agent: "officer",
        phase: Phase.reason,
        summary: `Officer ${decision.toUpperCase()} approval: "${appr.summary}"`,
        detail: { approval_id: id, decision, note },
        reason: "Risk-tiered authorization gate",
      });

      if (decision === "approve") {
        this.emitEvent(appr.case_id, {
          agent: "action",
          phase: Phase.act,
          summary: "Executing authorized critical action: Emergency perimeter secured & grid isolated",
          detail: { step_id: appr.step_id },
        });
      }
    }

    return appr;
  }

  public runScenario(scenario: "happy" | "disruption" | "ambiguity" | "case1042"): { case_id: string; access_token: string } {
    const idMap = {
      happy: "1001",
      disruption: "1002",
      ambiguity: "1003",
      case1042: "1042",
    };
    const targetId = idMap[scenario];
    const c = this.getCase(targetId);
    if (c) {
      c.updated_at = new Date().toISOString();
      this.emitEvent(targetId, {
        agent: "orchestrator",
        phase: Phase.perceive,
        summary: `Demo scenario triggered: [${scenario.toUpperCase()}] at simulated speed`,
        detail: { scenario, timestamp: new Date().toISOString() },
      });
    }
    return { case_id: targetId, access_token: `mock-case-access-${targetId}` };
  }

  public sandboxRejectTicket(ticketId: string, reason: string) {
    const foundCase = this.cases.find((c) => c.tickets.some((t) => t.id === ticketId));
    if (foundCase) {
      const ticket = foundCase.tickets.find((t) => t.id === ticketId);
      if (ticket) ticket.status = "rejected";
      this.emitEvent(foundCase.id, {
        agent: "sandbox",
        phase: Phase.adapt,
        summary: `SANDBOX SIGNAL: Ticket ${ticketId} rejected: "${reason}"`,
        detail: { ticket_id: ticketId, reason },
      });
      this.emitEvent(foundCase.id, {
        agent: "orchestrator",
        phase: Phase.adapt,
        summary: "Adaptation Rule (a): Ticket rejection received. Initiating policy re-search & replan",
        detail: { previous_ticket: ticketId },
        reason: "Department ticket rejection",
      });
    }
    return { success: true };
  }

  public sandboxCrewNoShow(ticketId: string) {
    const foundCase = this.cases.find((c) => c.tickets.some((t) => t.id === ticketId));
    if (foundCase) {
      foundCase.status = CaseStatus.AT_RISK;
      this.emitEvent(foundCase.id, {
        agent: "sandbox",
        phase: Phase.adapt,
        summary: `SANDBOX SIGNAL: Crew check-in deadline breached on ticket ${ticketId}`,
        detail: { ticket_id: ticketId },
      });
      this.emitEvent(foundCase.id, {
        agent: "orchestrator",
        phase: Phase.adapt,
        summary: "Adaptation Rule (b): Deadline imminent / Crew no-show! Urgency escalated to HIGH",
        detail: { urgency_boost: "high" },
        reason: "Crew no-show escalation",
      });
    }
    return { success: true };
  }

  public sandboxCrewCheckin(ticketId: string) {
    const foundCase = this.cases.find((c) => c.tickets.some((t) => t.id === ticketId));
    if (foundCase) {
      this.emitEvent(foundCase.id, {
        agent: "sandbox",
        phase: Phase.act,
        summary: `SANDBOX SIGNAL: Crew checked in on site for ticket ${ticketId}`,
        detail: { ticket_id: ticketId, coords: { lat: 37.775, lng: -122.419 } },
      });
    }
    return { success: true };
  }

  public sandboxRepairPhoto(ticketId: string) {
    const foundCase = this.cases.find((c) => c.tickets.some((t) => t.id === ticketId));
    if (foundCase) {
      foundCase.status = CaseStatus.AWAITING_CONFIRMATION;
      this.emitEvent(foundCase.id, {
        agent: "sandbox",
        phase: Phase.evaluate,
        summary: `SANDBOX SIGNAL: Repair completion photo uploaded for ticket ${ticketId}`,
        detail: { photo_url: "/placeholder-repair.jpg" },
      });
      this.emitEvent(foundCase.id, {
        agent: "evaluator",
        phase: Phase.evaluate,
        summary: "Evaluator: Gemini Vision verified repair photo. Transitioning to AWAITING_CONFIRMATION",
        detail: { confidence: 0.96, verification: "pipe_replaced_and_dry" },
      });
    }
    return { success: true };
  }
}

export const mockStore = new MockDataStore();
