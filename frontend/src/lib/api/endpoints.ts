import apiClient from "./client";
import type {
  CaseState,
  CaseEvent,
  Approval,
  PaginatedCases,
  MetricsSummary,
  EvalRun,
} from "./types";
import { mockStore } from "../mocks/mockService";

export const isMockMode = (): boolean => {
  if (typeof window !== "undefined") {
    const override = localStorage.getItem("civicpilot_use_mocks");
    if (override === "true") return true;
    if (override === "false") return false;
  }
  return (
    process.env.NEXT_PUBLIC_USE_MOCKS === "true" ||
    process.env.NEXT_PUBLIC_USE_MOCKS === "1"
  );
};

const citizenAuth = (accessToken?: string) =>
  accessToken ? { headers: { Authorization: `Bearer ${accessToken}` } } : undefined;

// Auth
export const login = async (password: string): Promise<{ data: { token: string } }> => {
  if (isMockMode()) {
    return { data: { token: "mock_jwt_officer_token_civicpilot_2026" } };
  }
  return apiClient.post<{ token: string }>("/api/auth/login", { password });
};

// Cases
export const listCases = async (params?: {
  status?: string;
  department?: string;
  urgency?: string;
  page?: number;
  per_page?: number;
  search?: string;
}): Promise<{ data: PaginatedCases }> => {
  if (isMockMode()) {
    return { data: mockStore.listCases(params) };
  }
  const query = {
    status: params?.status && params.status !== "ALL" ? params.status : undefined,
    department: params?.department && params.department !== "ALL" ? params.department : undefined,
    urgency: params?.urgency && params.urgency !== "ALL" ? params.urgency : undefined,
  };
  const response = await apiClient.get<CaseState[] | PaginatedCases>("/api/cases", { params: query });
  const payload = response.data;
  const allCases = Array.isArray(payload) ? payload : payload.cases;
  const filtered = params?.search
    ? allCases.filter((item) => {
        const queryText = params.search!.toLowerCase();
        return [item.id, item.raw.text, item.intake?.summary, item.intake?.location.address, item.raw.address_text]
          .some((value) => value?.toLowerCase().includes(queryText));
      })
    : allCases;
  return {
    data: {
      cases: filtered,
      total: filtered.length,
      page: 1,
      per_page: filtered.length,
    },
  };
};

export const runScenario = async (
  scenario: "happy" | "disruption" | "ambiguity" | "case1042"
): Promise<{ data: { case_id: string; access_token?: string } }> => {
  if (isMockMode()) {
    return { data: mockStore.runScenario(scenario) };
  }
  return apiClient.post<{ case_id: string; access_token?: string }>(`/api/demo/scenarios/${scenario}/run`);
};

export const getCase = async (id: string, accessToken?: string): Promise<{ data: CaseState }> => {
  if (isMockMode()) {
    const c = mockStore.getCase(id);
    if (!c) throw new Error("Case not found");
    return { data: c };
  }
  return apiClient.get<CaseState>(`/api/cases/${id}`, citizenAuth(accessToken));
};

export const getCaseEvents = async (id: string, accessToken?: string): Promise<{ data: CaseEvent[] }> => {
  if (isMockMode()) {
    return { data: mockStore.getCaseEvents(id) };
  }
  return apiClient.get<CaseEvent[]>(`/api/cases/${id}/events`, citizenAuth(accessToken));
};

export const createCase = async (formData: FormData): Promise<{ data: { case_id: string; access_token: string } }> => {
  if (isMockMode()) {
    const text = (formData.get("text") as string) || "Grievance report";
    const address = (formData.get("address_text") as string) || "";
    const lat = formData.get("lat") ? parseFloat(formData.get("lat") as string) : undefined;
    const lng = formData.get("lng") ? parseFloat(formData.get("lng") as string) : undefined;
    const language = (formData.get("language") as string) || "en";
    const contact = (formData.get("contact") as string) || "";
    const channelValue = formData.get("channel");
    const channel = channelValue === "chat" || channelValue === "voice" || channelValue === "email"
      ? channelValue
      : "web";

    const res = mockStore.createCase({
      text,
      address_text: address,
      lat,
      lng,
      language,
      contact,
      channel,
    });
    return { data: res };
  }
  return apiClient.post<{ case_id: string; access_token: string }>("/api/cases", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const sendCitizenMessage = async (
  id: string,
  data: { text: string; image?: File },
  accessToken?: string
): Promise<{ data: CaseEvent }> => {
  if (isMockMode()) {
    const evt = mockStore.addCitizenMessage(id, data.text);
    return { data: evt };
  }
  const formData = new FormData();
  formData.append("text", data.text);
  if (data.image) formData.append("image", data.image);
  return apiClient.post<CaseEvent>(`/api/cases/${id}/messages`, formData, {
    headers: {
      ...citizenAuth(accessToken)?.headers,
      "Content-Type": "multipart/form-data",
    },
  });
};

export const confirmCase = async (
  id: string,
  data: { confirmed: boolean; comment?: string },
  accessToken?: string
): Promise<{ data: CaseState }> => {
  if (isMockMode()) {
    const c = mockStore.confirmCase(id, data.confirmed, data.comment);
    return { data: c };
  }
  await apiClient.post(`/api/cases/${id}/confirm`, data, citizenAuth(accessToken));
  return getCase(id, accessToken);
};

export const resolveCase = async (
  id: string,
  data: { note: string }
): Promise<{ data: CaseState }> => {
  if (isMockMode()) {
    const c = mockStore.resolveCase(id, data.note);
    return { data: c };
  }
  await apiClient.post(`/api/cases/${id}/resolve`, data);
  return getCase(id);
};

// Approvals
export const listApprovals = async (status?: string): Promise<{ data: Approval[] }> => {
  if (isMockMode()) {
    return { data: mockStore.listApprovals(status) };
  }
  return apiClient.get<Approval[]>("/api/approvals", { params: { status } });
};

export const handleApproval = async (
  id: string,
  data: { decision: "approve" | "reject"; note?: string }
): Promise<{ data: Approval | { status: string; approval_id: string; decision: "approve" | "reject" } }> => {
  if (isMockMode()) {
    const appr = mockStore.handleApproval(id, data.decision, data.note);
    return { data: appr };
  }
  return apiClient.post<{ status: string; approval_id: string; decision: "approve" | "reject" }>(`/api/approvals/${id}`, data);
};

// Sandbox / Demo controls
export const sandboxRejectTicket = async (id: string, reason: string): Promise<{ data: Record<string, unknown> }> => {
  if (isMockMode()) {
    return { data: mockStore.sandboxRejectTicket(id, reason) };
  }
  return apiClient.post(`/api/sandbox/tickets/${id}/reject`, { reason });
};

export const sandboxCrewCheckin = async (ticketId: string): Promise<{ data: Record<string, unknown> }> => {
  if (isMockMode()) {
    return { data: mockStore.sandboxCrewCheckin(ticketId) };
  }
  return apiClient.post(`/api/sandbox/tickets/${ticketId}/crew-checkin`, {});
};

export const sandboxCrewNoShow = async (ticketId: string): Promise<{ data: Record<string, unknown> }> => {
  if (isMockMode()) {
    return { data: mockStore.sandboxCrewNoShow(ticketId) };
  }
  return apiClient.post(`/api/sandbox/tickets/${ticketId}/crew-no-show`, {});
};

export const sandboxRepairPhoto = async (ticketId: string, photo?: File): Promise<{ data: Record<string, unknown> }> => {
  if (isMockMode()) {
    return { data: mockStore.sandboxRepairPhoto(ticketId) };
  }
  return apiClient.post(`/api/sandbox/tickets/${ticketId}/repair-photo`, {
    photo_url: photo ? photo.name : "/demo/repair-proof.jpg",
  });
};

// Eval & Metrics
export const runEval = async (): Promise<{ data: EvalRun }> => {
  if (isMockMode()) {
    return {
      data: {
        id: `eval_${Date.now()}`,
        status: "done",
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
    };
  }
  const response = await apiClient.post<{
    id?: string;
    run_id?: string;
    status: EvalRun["status"];
    started_at?: string | null;
    completed_at?: string | null;
    results?: EvalRun["results"];
    metrics?: Array<{ metric: string; score: number; details?: Record<string, unknown> }>;
  }>("/api/eval/run");
  return {
    data: {
      id: response.data.id || response.data.run_id || "unknown",
      status: response.data.status,
      started_at: response.data.started_at || new Date().toISOString(),
      completed_at: response.data.completed_at || undefined,
      results: response.data.results || response.data.metrics,
    },
  };
};

export const getEvalRun = async (id: string): Promise<{ data: EvalRun }> => {
  if (isMockMode()) {
    return {
      data: {
        id,
        status: "done",
        started_at: new Date().toISOString(),
      },
    };
  }
  return apiClient.get<EvalRun>(`/api/eval/runs/${id}`);
};

export const getMetricsSummary = async (): Promise<{ data: MetricsSummary | null }> => {
  if (isMockMode()) {
    return { data: null };
  }
  return apiClient.get<MetricsSummary>("/api/metrics/summary");
};

// Health
export const getHealth = async () => {
  if (isMockMode()) {
    return { data: { status: "healthy", mode: "mock", time: new Date().toISOString() } };
  }
  return apiClient.get("/api/health");
};

export const triggerTick = async () => {
  if (isMockMode()) {
    return { data: { status: "tick_processed", executed_timers: 1 } };
  }
  return apiClient.post("/api/tick");
};
