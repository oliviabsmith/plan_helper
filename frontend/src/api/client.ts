import { env } from "../config/env";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const base = env.apiBaseUrl || "";
  const url = `${base}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || response.statusText, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const data = await response.json();
  return data as T;
}

export interface TicketUploadRow {
  id: string;
  title?: string;
  description?: string;
  story_points?: number;
  labels?: string[];
  components?: string[];
  tech?: string[];
  due_date?: string | null;
  sprint?: string | null;
  status?: string;
}

export interface TicketUploadResponse {
  inserted: number;
  updated: number;
  warnings: string[];
}

export interface TicketSearchRequest {
  ids?: string[];
  status?: string[];
  text?: string;
  tech?: string[];
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  story_points: number;
  labels: string[];
  components: string[];
  tech: string[];
  due_date: string | null;
  sprint: string | null;
  status: string;
}

export interface SubtaskInputBullet {
  text_sub: string;
  tags?: string[];
  est_hours?: number | null;
}

export interface CreateSubtasksRequest {
  ticket_id: string;
  bullets?: SubtaskInputBullet[];
  mode?: "append" | "replace";
  llm_options?: Record<string, unknown>;
}

export interface Subtask {
  id: string;
  ticket_id: string;
  seq: number;
  text_sub: string;
  tags: string[];
  status: string;
  est_hours: number | null;
}

export interface SubtaskListRequest {
  ticket_id?: string;
  status?: string[];
}

export interface MarkSubtasksStatusRequest {
  subtask_ids: string[];
  status: string;
}

export interface MarkSubtasksStatusResponse {
  updated: number;
}

export interface AffinityComputeRequest {
  status?: string[];
  ticket_ids?: string[];
  clear_existing?: boolean;
}

export interface AffinityGroup {
  id?: string;
  key: string;
  rationale: string;
  members: string[];
}

export interface PlannerConstraints {
  max_contexts_per_day?: number;
  max_focus_blocks_per_day?: number;
  buffer_ratio?: number;
  workdays?: number[];
}

export interface PlanRequest {
  start_date?: string;
  days?: number;
  constraints?: PlannerConstraints;
  clear_existing_from_start?: boolean;
  ticket_ids?: string[];
}

export interface PlannedBlock {
  date: string;
  bucket: string;
  note: string | null;
  subtask_ids: string[];
}

export interface PlanItem {
  id: string;
  date: string;
  bucket: string;
  notes: string | null;
  subtask_ids: string[];
}

export interface MorningReportRequest {
  date?: string;
  narrative?:
    | boolean
    | string
    | {
        enabled?: boolean;
        llm_options?: Record<string, unknown>;
        options?: Record<string, unknown>;
      };
}

export interface MorningChecklistItem {
  subtask_id: string;
  ticket_id: string;
  seq: number;
  text_sub: string;
  why_now: string;
  tags: string[];
}

export interface MorningBatch {
  note: string;
  plan_item_id: string;
  members: string[];
  rationale: string;
}

export interface MorningNarrative {
  text: string;
  context_tags: string[];
  memory_refs: string[];
  error?: string;
}

export interface MorningMemoryItem {
  id: string;
  topic: string;
  text: string;
  pinned: boolean;
  created_at: string;
}

export interface MorningReportResponse {
  date: string;
  checklist: MorningChecklistItem[];
  batches: MorningBatch[];
  risks: string[];
  memory_top3: MorningMemoryItem[];
  narrative: MorningNarrative | null;
}

export interface EveningReportRequest {
  date?: string;
  completed?: string[];
  partial?: string[];
  blocked?: { id: string; note: string }[];
}

export interface EveningPlanDelta {
  id: string;
  date: string;
  bucket: string;
  notes: string | null;
  subtask_ids: string[];
}

export interface EveningReportResponse {
  plan_delta: EveningPlanDelta[];
  notes: string[];
  summary?: string;
}

export const api = {
  uploadTickets: (payload: { tickets: TicketUploadRow[] }) =>
    request<TicketUploadResponse>("/tools/tickets/load_manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  searchTickets: (payload: TicketSearchRequest) =>
    request<Ticket[]>("/tools/tickets/search", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createSubtasks: (payload: CreateSubtasksRequest) =>
    request<Subtask[]>("/tools/subtasks/create_for_ticket", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  markSubtasksStatus: (payload: MarkSubtasksStatusRequest) =>
    request<MarkSubtasksStatusResponse>("/tools/subtasks/mark_status", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listSubtasks: (payload: SubtaskListRequest = {}) =>
    request<Subtask[]>("/tools/subtasks/list", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  computeAffinity: (payload: AffinityComputeRequest) =>
    request<AffinityGroup[]>("/tools/affinity/compute", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listAffinityGroups: () => request<AffinityGroup[]>("/tools/affinity/list"),

  makePlan: (payload: PlanRequest) =>
    request<PlannedBlock[]>("/tools/planner/make_two_week_plan", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listPlan: () => request<PlanItem[]>("/tools/planner/list"),

  morningReport: (payload: MorningReportRequest) =>
    request<MorningReportResponse>("/tools/reports/morning", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  eveningReport: (payload: EveningReportRequest) =>
    request<EveningReportResponse>("/tools/reports/evening", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
