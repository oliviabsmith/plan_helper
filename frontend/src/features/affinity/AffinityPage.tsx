import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { api, AffinityComputeRequest, AffinityGroup } from "../../api/client";
import { Button } from "../../components/Button";
import { TextInput } from "../../components/Input";
import { AsyncState } from "../../components/AsyncState";

interface ComputeFormValues {
  status: string;
  ticket_ids: string;
  clear_existing: boolean;
}

export function AffinityPage() {
  const queryClient = useQueryClient();
  const form = useForm<ComputeFormValues>({
    defaultValues: {
      status: "todo,in_progress",
      ticket_ids: "",
      clear_existing: true,
    },
  });

  const listQuery = useQuery({
    queryKey: ["affinity", "list"],
    queryFn: () => api.listAffinityGroups(),
  });

  const computeMutation = useMutation({
    mutationFn: async (values: ComputeFormValues) => {
      const payload: AffinityComputeRequest = {
        clear_existing: values.clear_existing,
        status: values.status ? values.status.split(/[,\s]+/).filter(Boolean) : undefined,
        ticket_ids: values.ticket_ids ? values.ticket_ids.split(/[,\s]+/).filter(Boolean) : undefined,
      };
      return api.computeAffinity(payload);
    },
    onSuccess: (groups) => {
      toast.success(`Computed ${groups.length} affinity groups`);
      queryClient.invalidateQueries({ queryKey: ["affinity", "list"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to compute affinity";
      toast.error(message);
    },
  });

  const groups = listQuery.data ?? [];

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Affinity batching</h2>
            <p className="text-sm text-slate-400">
              Recompute backend affinity groups to batch similar subtasks for focused work.
            </p>
          </div>
          <Button onClick={() => form.handleSubmit((values) => computeMutation.mutate(values))()} loading={computeMutation.isPending}>
            Recompute groups
          </Button>
        </div>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={form.handleSubmit((values) => computeMutation.mutate(values))}>
          <TextInput label="Statuses" placeholder="todo,in_progress" {...form.register("status")} />
          <TextInput label="Ticket IDs" placeholder="FOO-1 BAR-2" {...form.register("ticket_ids")} />
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" {...form.register("clear_existing")} />
            Clear existing before saving
          </label>
          <div className="md:col-span-3 flex justify-end">
            <Button type="submit" variant="secondary" loading={computeMutation.isPending}>
              Run compute
            </Button>
          </div>
        </form>
      </section>

      <AsyncState
        isLoading={listQuery.isLoading}
        isError={listQuery.isError}
        errorMessage={listQuery.error instanceof Error ? listQuery.error.message : undefined}
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {groups.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-6 text-sm text-slate-400">
              No affinity groups found yet. Recompute to populate.
            </div>
          ) : (
            groups.map((group: AffinityGroup) => (
              <article key={group.key} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100">{group.key}</h3>
                    {group.rationale && <p className="text-xs text-slate-400">{group.rationale}</p>}
                  </div>
                  <span className="rounded-full bg-primary-500/20 px-3 py-1 text-xs font-medium text-primary-200">
                    {group.members.length} subtasks
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {group.members.map((member) => (
                    <span key={member} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                      {member}
                    </span>
                  ))}
                </div>
              </article>
            ))
          )}
        </div>
      </AsyncState>
    </div>
  );
}

export default AffinityPage;
