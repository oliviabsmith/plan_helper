import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  api,
  EveningReportRequest,
  EveningReportResponse,
  MorningReportRequest,
  MorningReportResponse,
} from "../../api/client";
import { Button } from "../../components/Button";
import { TextArea, TextInput } from "../../components/Input";

interface MorningFormValues {
  date: string;
  narrative: string;
}

interface EveningFormValues {
  date: string;
  completed: string;
  partial: string;
  blocked: string;
}

type ActiveTab = "morning" | "evening";

export function ReportsPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("morning");
  const [morningReport, setMorningReport] = useState<MorningReportResponse | null>(null);
  const [eveningReport, setEveningReport] = useState<EveningReportResponse | null>(null);

  const morningForm = useForm<MorningFormValues>({
    defaultValues: { date: "", narrative: "disabled" },
  });
  const eveningForm = useForm<EveningFormValues>({
    defaultValues: { date: "", completed: "", partial: "", blocked: "" },
  });

  const morningMutation = useMutation({
    mutationFn: async (values: MorningFormValues) => {
      const payload: MorningReportRequest = {
        date: values.date || undefined,
      };
      if (values.narrative === "disabled") {
        payload.narrative = false;
      } else if (values.narrative === "enabled") {
        payload.narrative = true;
      } else if (values.narrative) {
        payload.narrative = values.narrative;
      }
      return api.morningReport(payload);
    },
    onSuccess: (data) => {
      setMorningReport(data);
      toast.success("Morning report ready");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to fetch morning report";
      toast.error(message);
    },
  });

  const eveningMutation = useMutation({
    mutationFn: async (values: EveningFormValues) => {
      let blocked: EveningReportRequest["blocked"] | undefined;
      if (values.blocked) {
        try {
          const parsed = JSON.parse(values.blocked);
          if (!Array.isArray(parsed)) {
            throw new Error("Blocked value must be an array of {id,note} objects");
          }
          blocked = parsed;
        } catch (err) {
          const message = err instanceof Error ? err.message : "Invalid blocked JSON";
          throw new Error(message);
        }
      }
      const payload: EveningReportRequest = {
        date: values.date || undefined,
        completed: values.completed ? values.completed.split(/[,\s]+/).filter(Boolean) : undefined,
        partial: values.partial ? values.partial.split(/[,\s]+/).filter(Boolean) : undefined,
        blocked,
      };
      return api.eveningReport(payload);
    },
    onSuccess: (data) => {
      setEveningReport(data);
      toast.success("Evening update processed");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to process evening update";
      toast.error(message);
    },
  });

  const renderMorningReport = () => {
    if (!morningReport) return null;
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Checklist</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {morningReport.checklist.map((item) => (
              <li key={item.subtask_id} className="rounded-md border border-slate-800/80 bg-slate-900/70 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-xs text-primary-200">{item.ticket_id} · {item.seq}</span>
                  <span className="text-xs text-slate-400">{item.tags.join(", ")}</span>
                </div>
                <p className="mt-2 text-slate-100">{item.text_sub}</p>
                {item.why_now && <p className="mt-1 text-xs text-slate-400">Why now: {item.why_now}</p>}
              </li>
            ))}
          </ul>
        </div>
        {morningReport.batches.length > 0 && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Batches</h3>
            <ul className="mt-2 space-y-2 text-sm">
              {morningReport.batches.map((batch) => (
                <li key={batch.note} className="rounded-md border border-slate-800/80 bg-slate-900/70 p-3">
                  <p className="font-semibold text-slate-100">{batch.note}</p>
                  {batch.rationale && <p className="text-xs text-slate-400">{batch.rationale}</p>}
                  <p className="mt-1 text-xs text-slate-400">Members: {batch.members.join(", ")}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
        {morningReport.narrative && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Narrative</h3>
            <p className="text-sm leading-relaxed text-slate-100 whitespace-pre-line">{morningReport.narrative.text}</p>
            {morningReport.narrative.error && (
              <p className="mt-2 text-xs text-rose-300">Narrative error: {morningReport.narrative.error}</p>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderEveningReport = () => {
    if (!eveningReport) return null;
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Plan delta</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {eveningReport.plan_delta.map((item) => (
              <li key={item.id ?? `${item.date}-${item.bucket}`}
                className="rounded-md border border-slate-800/80 bg-slate-900/70 p-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>{item.date}</span>
                  <span>{item.bucket}</span>
                </div>
                {item.notes && <p className="mt-2 text-sm text-slate-100">{item.notes}</p>}
                {item.subtask_ids.length > 0 && (
                  <p className="mt-2 text-xs text-slate-400">Subtasks: {item.subtask_ids.join(", ")}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
        {eveningReport.notes.length > 0 && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Notes</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-100">
              {eveningReport.notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        )}
        {eveningReport.summary && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Summary</h3>
            <p className="text-sm leading-relaxed text-slate-100 whitespace-pre-line">{eveningReport.summary}</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant={activeTab === "morning" ? "primary" : "secondary"} onClick={() => setActiveTab("morning")}>
          Morning report
        </Button>
        <Button variant={activeTab === "evening" ? "primary" : "secondary"} onClick={() => setActiveTab("evening")}>
          Evening update
        </Button>
      </div>

      {activeTab === "morning" ? (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
          <h2 className="text-lg font-semibold text-slate-100">Request morning report</h2>
          <p className="mb-4 text-sm text-slate-400">Pulls checklist, batches, and optional narrative context.</p>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={morningForm.handleSubmit((values) => morningMutation.mutate(values))}>
            <TextInput type="date" label="Date" {...morningForm.register("date")} />
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Narrative
              <select
                className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                {...morningForm.register("narrative")}
              >
                <option value="disabled">Disabled</option>
                <option value="enabled">Enabled</option>
                <option value="summary">Request summary narrative</option>
              </select>
              <span className="text-xs text-slate-500">Toggles the backend LLM narrative block.</span>
            </label>
            <div className="md:col-span-2 flex justify-end gap-2">
              <Button type="submit" loading={morningMutation.isPending}>
                Fetch report
              </Button>
            </div>
          </form>
          <div className="mt-6">{renderMorningReport()}</div>
        </section>
      ) : (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
          <h2 className="text-lg font-semibold text-slate-100">Submit evening update</h2>
          <p className="mb-4 text-sm text-slate-400">Summarise the day and optionally mark subtask outcomes.</p>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={eveningForm.handleSubmit((values) => eveningMutation.mutate(values))}>
            <TextInput type="date" label="Date" {...eveningForm.register("date")} />
            <TextInput label="Completed IDs" placeholder="subtask ids" {...eveningForm.register("completed")} />
            <TextInput label="Partial IDs" placeholder="subtask ids" {...eveningForm.register("partial")} />
            <TextArea
              label="Blocked JSON"
              placeholder='[{"id":"subtask-id","note":"Waiting for review"}]'
              rows={4}
              {...eveningForm.register("blocked")}
            />
            <div className="md:col-span-2 flex justify-end gap-2">
              <Button type="submit" loading={eveningMutation.isPending}>
                Process update
              </Button>
            </div>
          </form>
          <div className="mt-6">{renderEveningReport()}</div>
        </section>
      )}
    </div>
  );
}

export default ReportsPage;
