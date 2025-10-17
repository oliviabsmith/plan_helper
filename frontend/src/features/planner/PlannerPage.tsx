import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { api, PlanItem, PlanRequest, PlannedBlock } from "../../api/client";
import { Button } from "../../components/Button";
import { TextInput } from "../../components/Input";
import { AsyncState } from "../../components/AsyncState";
import { SubtaskIdChip } from "../../components/SubtaskIdChip";

interface PlannerFormValues {
  start_date: string;
  days: number;
  max_contexts_per_day: number;
  max_focus_blocks_per_day: number;
  buffer_ratio: number;
  ticket_ids: string;
  clear_existing_from_start: boolean;
}

export function PlannerPage() {
  const queryClient = useQueryClient();
  const [generatedPlan, setGeneratedPlan] = useState<PlannedBlock[] | null>(null);

  const form = useForm<PlannerFormValues>({
    defaultValues: {
      start_date: "",
      days: 10,
      max_contexts_per_day: 2,
      max_focus_blocks_per_day: 4,
      buffer_ratio: 0.2,
      ticket_ids: "",
      clear_existing_from_start: true,
    },
  });

  const existingPlanQuery = useQuery({
    queryKey: ["planner", "list"],
    queryFn: () => api.listPlan(),
  });

  const makePlanMutation = useMutation({
    mutationFn: async (values: PlannerFormValues) => {
      const payload: PlanRequest = {
        start_date: values.start_date || undefined,
        days: Number(values.days) || undefined,
        clear_existing_from_start: values.clear_existing_from_start,
        ticket_ids: values.ticket_ids ? values.ticket_ids.split(/[,\s]+/).filter(Boolean) : undefined,
        constraints: {
          max_contexts_per_day: Number(values.max_contexts_per_day),
          max_focus_blocks_per_day: Number(values.max_focus_blocks_per_day),
          buffer_ratio: Number(values.buffer_ratio),
        },
      };
      return api.makePlan(payload);
    },
    onSuccess: (plan) => {
      toast.success(`Generated ${plan.length} plan blocks`);
      setGeneratedPlan(plan);
      queryClient.invalidateQueries({ queryKey: ["planner", "list"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to generate plan";
      toast.error(message);
    },
  });

  const renderTimeline = (blocks: PlannedBlock[]) => {
    if (!blocks.length) {
      return (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-6 text-sm text-slate-400">
          Plan response was empty.
        </div>
      );
    }

    const grouped = blocks.reduce<Record<string, PlannedBlock[]>>((acc, block) => {
      acc[block.date] = acc[block.date] ?? [];
      acc[block.date].push(block);
      return acc;
    }, {});

    const dates = Object.keys(grouped).sort();

    return (
      <div className="space-y-5">
        {dates.map((date) => (
          <section key={date} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{date}</h3>
              <div className="h-px flex-1 translate-y-1 border-b border-dashed border-slate-800/70" />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {grouped[date].map((block) => (
                <PlanBlockCard
                  key={`${block.date}-${block.bucket}-${block.note ?? ""}`}
                  bucket={block.bucket}
                  note={block.note}
                  subtaskIds={block.subtask_ids}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    );
  };

  const renderExistingPlan = (items: PlanItem[]) => {
    if (!items.length) {
      return (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-6 text-sm text-slate-400">
          No plan persisted yet. Generate one to populate the database.
        </div>
      );
    }

    const grouped = items.reduce<Record<string, PlanItem[]>>((acc, item) => {
      acc[item.date] = acc[item.date] ?? [];
      acc[item.date].push(item);
      return acc;
    }, {});

    const dates = Object.keys(grouped).sort();

    return (
      <div className="space-y-5">
        {dates.map((date) => (
          <section key={date} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{date}</h3>
              <div className="h-px flex-1 translate-y-1 border-b border-dashed border-slate-800/70" />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {grouped[date].map((item) => (
                <PlanBlockCard
                  key={item.id}
                  bucket={item.bucket}
                  note={item.notes}
                  subtaskIds={item.subtask_ids}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
        <div className="flex flex-col gap-2 pb-4">
          <h2 className="text-lg font-semibold text-slate-100">Two-week planner</h2>
          <p className="text-sm text-slate-400">
            Configure constraints and generate a fresh schedule. Submitting will persist plan items in the backend.
          </p>
        </div>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={form.handleSubmit((values) => makePlanMutation.mutate(values))}>
          <TextInput type="date" label="Start date" {...form.register("start_date")} />
          <TextInput type="number" label="Days" min={1} {...form.register("days", { valueAsNumber: true })} />
          <TextInput
            type="number"
            label="Max contexts/day"
            min={1}
            {...form.register("max_contexts_per_day", { valueAsNumber: true })}
          />
          <TextInput
            type="number"
            label="Max focus blocks/day"
            min={1}
            {...form.register("max_focus_blocks_per_day", { valueAsNumber: true })}
          />
          <TextInput
            type="number"
            step={0.05}
            label="Buffer ratio"
            min={0}
            max={1}
            {...form.register("buffer_ratio", { valueAsNumber: true })}
          />
          <TextInput label="Ticket IDs" placeholder="FOO-1 BAR-2" {...form.register("ticket_ids")} />
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" {...form.register("clear_existing_from_start")} />
            Clear existing items from start date
          </label>
          <div className="md:col-span-3 flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => form.reset()}>
              Reset
            </Button>
            <Button type="submit" loading={makePlanMutation.isPending}>
              Generate & persist
            </Button>
          </div>
        </form>
      </section>

      {generatedPlan && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
          <h2 className="text-lg font-semibold text-slate-100">Latest generated plan</h2>
          <p className="mb-4 text-sm text-slate-400">This is the direct response from the planner endpoint.</p>
          {renderTimeline(generatedPlan)}
        </section>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
        <h2 className="text-lg font-semibold text-slate-100">Persisted plan timeline</h2>
        <p className="mb-4 text-sm text-slate-400">Data pulled from <code className="font-mono">/tools/planner/list</code>.</p>
        <AsyncState
          isLoading={existingPlanQuery.isLoading}
          isError={existingPlanQuery.isError}
          errorMessage={existingPlanQuery.error instanceof Error ? existingPlanQuery.error.message : undefined}
        >
          <div className="space-y-6">
            {renderExistingPlan(existingPlanQuery.data ?? [])}
            {existingPlanQuery.data && existingPlanQuery.data.length > 0 && (
              <PlanCalendar items={existingPlanQuery.data} />
            )}
          </div>
        </AsyncState>
      </section>
    </div>
  );
}

export default PlannerPage;

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MAX_COLLAPSED_SUBTASKS = 6;

interface PlanBlockCardProps {
  bucket: string;
  note: string | null;
  subtaskIds: string[];
}

function PlanBlockCard({ bucket, note, subtaskIds }: PlanBlockCardProps) {
  return (
    <article className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-inner shadow-slate-900/30">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-lg font-semibold text-slate-100">{bucket}</p>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Focus block</p>
        </div>
        <span className="rounded-full border border-primary-500/40 bg-primary-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary-200">
          {subtaskIds.length} subtasks
        </span>
      </header>
      {note && (
        <div className="rounded-lg border border-slate-800/60 bg-slate-900/70 p-3 text-sm leading-relaxed text-slate-200">
          {note}
        </div>
      )}
      {subtaskIds.length > 0 && (
        <div className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
          <div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-500">
            <span>Subtasks</span>
            {subtaskIds.length > MAX_COLLAPSED_SUBTASKS && (
              <span>{subtaskIds.length} total</span>
            )}
          </div>
          <div className="mt-2">
            <ExpandableSubtaskList ids={subtaskIds} />
          </div>
        </div>
      )}
    </article>
  );
}

function ExpandableSubtaskList({ ids }: { ids: string[] }) {
  const [expanded, setExpanded] = useState(false);

  if (!ids.length) {
    return null;
  }

  const visible = expanded ? ids : ids.slice(0, MAX_COLLAPSED_SUBTASKS);
  const remaining = ids.length - visible.length;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {visible.map((id) => (
        <SubtaskIdChip key={id} value={id} className="px-2 py-0.5 text-[11px]" />
      ))}
      {remaining > 0 && !expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="rounded-full border border-dashed border-slate-700 px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-slate-400 transition hover:border-primary-400 hover:text-primary-200"
        >
          +{remaining} more
        </button>
      )}
      {expanded && ids.length > MAX_COLLAPSED_SUBTASKS && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="rounded-full border border-slate-700 px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-slate-400 transition hover:border-primary-400 hover:text-primary-200"
        >
          Show less
        </button>
      )}
    </div>
  );
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function parseIsoDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, (month ?? 1) - 1, day ?? 1);
}

function toDateKey(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildCalendarWeeks(month: Date) {
  const weeks: Date[][] = [];
  const start = startOfMonth(month);
  const offset = (start.getDay() + 6) % 7; // convert to Monday start
  const cursor = new Date(start);
  cursor.setDate(cursor.getDate() - offset);

  for (let week = 0; week < 6; week += 1) {
    const days: Date[] = [];
    for (let day = 0; day < 7; day += 1) {
      days.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(days);
  }

  return weeks;
}

function PlanCalendar({ items }: { items: PlanItem[] }) {
  const itemsByDate = useMemo(() => {
    const map = new Map<string, PlanItem[]>();
    items.forEach((item) => {
      const key = item.date;
      const next = map.get(key) ?? [];
      next.push(item);
      map.set(key, next);
    });
    return map;
  }, [items]);

  const initialMonth = useMemo(() => {
    if (!items.length) {
      return startOfMonth(new Date());
    }
    const sorted = [...items].sort((a, b) => a.date.localeCompare(b.date));
    return startOfMonth(parseIsoDate(sorted[0].date));
  }, [items]);

  const [currentMonth, setCurrentMonth] = useState<Date>(initialMonth);

  useEffect(() => {
    setCurrentMonth(initialMonth);
  }, [initialMonth]);

  const weeks = useMemo(() => buildCalendarWeeks(currentMonth), [currentMonth]);
  const monthLabel = new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(currentMonth);

  const handleMonthChange = (delta: number) => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  };

  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-6 text-sm text-slate-400">
        Generate and persist a plan to unlock the calendar view.
      </div>
    );
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-100">Calendar view</h3>
          <p className="text-xs text-slate-400">Navigate by month to spot crowded days at a glance.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" className="px-3 py-1 text-xs" onClick={() => handleMonthChange(-1)}>
            Prev
          </Button>
          <span className="rounded-md bg-slate-800 px-3 py-1 text-sm font-medium text-slate-100">{monthLabel}</span>
          <Button variant="ghost" className="px-3 py-1 text-xs" onClick={() => handleMonthChange(1)}>
            Next
          </Button>
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="grid grid-cols-7 gap-2 text-center text-[11px] uppercase tracking-wide text-slate-500">
          {WEEKDAY_LABELS.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-2">
          {weeks.flat().map((day, index) => {
            const key = toDateKey(day);
            const dayItems = itemsByDate.get(key) ?? [];
            const inMonth = day.getMonth() === currentMonth.getMonth();
            const baseClass = "flex min-h-[150px] flex-col gap-2 rounded-lg border p-3";
            const stateClass = inMonth
              ? "border-slate-800 bg-slate-900/70"
              : "border-slate-900/40 bg-slate-900/30 text-slate-500";
            return (
              <div
                key={`${key}-${index}`}
                className={`${baseClass} ${stateClass}`}
              >
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                  <span>{day.getDate()}</span>
                  {dayItems.length > 0 && (
                    <span className="rounded-full bg-primary-500/10 px-2 py-0.5 text-[10px] font-semibold text-primary-200">
                      {dayItems.length} blocks
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-2 overflow-y-auto pr-1">
                  {dayItems.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-md border border-slate-800/60 bg-slate-900/80 p-2 text-[11px] text-slate-200"
                    >
                      <p className="font-semibold text-slate-100">{item.bucket}</p>
                      {item.notes && (
                        <p className="mt-1 text-[10px] text-slate-400">{item.notes}</p>
                      )}
                      <div className="mt-2 flex flex-wrap items-center gap-1">
                        {item.subtask_ids.slice(0, 2).map((id) => (
                          <SubtaskIdChip key={id} value={id} className="px-2 py-0.5 text-[10px]" />
                        ))}
                        {item.subtask_ids.length > 2 && (
                          <span className="text-[10px] uppercase tracking-wide text-slate-500">
                            +{item.subtask_ids.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                  {dayItems.length === 0 && <span className="text-[10px] text-slate-600">No focus blocks</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
