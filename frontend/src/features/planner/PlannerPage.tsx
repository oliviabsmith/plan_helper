import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { api, PlanItem, PlanRequest, PlannedBlock } from "../../api/client";
import { Button } from "../../components/Button";
import { TextInput } from "../../components/Input";
import { AsyncState } from "../../components/AsyncState";

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
      <div className="space-y-4">
        {dates.map((date) => (
          <section key={date} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{date}</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {grouped[date].map((block) => (
                <article key={`${block.date}-${block.bucket}-${block.note}`} className="rounded-md border border-slate-800 bg-slate-900/80 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-base font-semibold text-slate-100">{block.bucket}</span>
                    <span className="text-xs text-slate-400">{block.subtask_ids.length} subtasks</span>
                  </div>
                  {block.note && <p className="mt-2 text-sm text-slate-300">{block.note}</p>}
                  {block.subtask_ids.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {block.subtask_ids.map((sid) => (
                        <span key={sid} className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                          {sid}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
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
      <div className="space-y-4">
        {dates.map((date) => (
          <section key={date} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{date}</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {grouped[date].map((item) => (
                <article key={item.id} className="rounded-md border border-slate-800 bg-slate-900/80 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-base font-semibold text-slate-100">{item.bucket}</span>
                    <span className="text-xs text-slate-400">{item.subtask_ids.length} subtasks</span>
                  </div>
                  {item.notes && <p className="mt-2 text-sm text-slate-300">{item.notes}</p>}
                  {item.subtask_ids.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {item.subtask_ids.map((sid) => (
                        <span key={sid} className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                          {sid}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
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
          {renderExistingPlan(existingPlanQuery.data ?? [])}
        </AsyncState>
      </section>
    </div>
  );
}

export default PlannerPage;
