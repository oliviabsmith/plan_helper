import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { api, CreateSubtasksRequest, Subtask } from "../../api/client";
import { Button } from "../../components/Button";
import { TextArea, TextInput } from "../../components/Input";
import { Table } from "../../components/Table";
import { StatusBadge } from "../../components/StatusBadge";
import { AsyncState } from "../../components/AsyncState";
import { Modal } from "../../components/Modal";
import { SubtaskIdChip } from "../../components/SubtaskIdChip";

interface FilterValues {
  ticket_id: string;
  status: string;
}

interface CreateFormValues {
  ticket_id: string;
  bullets: string;
  mode: "append" | "replace";
}

export function SubtasksPage() {
  const [filters, setFilters] = useState<{ ticket_id?: string; status?: string[] }>({});
  const [openCreate, setOpenCreate] = useState(false);
  const filterForm = useForm<FilterValues>({ defaultValues: { ticket_id: "", status: "" } });
  const createForm = useForm<CreateFormValues>({
    defaultValues: { ticket_id: "", bullets: "", mode: "append" },
  });
  const queryClient = useQueryClient();
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const subtasksQuery = useQuery({
    queryKey: ["subtasks", filters],
    queryFn: () => api.listSubtasks(filters),
  });

  const createMutation = useMutation({
    mutationFn: async (values: CreateFormValues) => {
      let bullets: CreateSubtasksRequest["bullets"] | undefined;
      if (values.bullets.trim()) {
        bullets = JSON.parse(values.bullets);
        if (!Array.isArray(bullets)) {
          throw new Error("Bullets must be an array of objects {text_sub, tags?, est_hours?}");
        }
      }
      return api.createSubtasks({
        ticket_id: values.ticket_id.trim(),
        mode: values.mode,
        bullets,
      });
    },
    onSuccess: (created) => {
      toast.success(`Created ${created.length} subtasks`);
      setOpenCreate(false);
      createForm.reset();
      queryClient.invalidateQueries({ queryKey: ["subtasks"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to create subtasks";
      toast.error(message);
    },
  });

  const markDoneMutation = useMutation({
    mutationFn: async (subtaskId: string) =>
      api.markSubtasksStatus({ subtask_ids: [subtaskId], status: "done" }),
    onMutate: (subtaskId) => {
      setUpdatingId(subtaskId);
    },
    onSuccess: (result, subtaskId) => {
      const label = result.updated === 1 ? "subtask" : "subtasks";
      toast.success(`Marked ${result.updated} ${label} as done`);
      queryClient.invalidateQueries({ queryKey: ["subtasks"] });
      queryClient.invalidateQueries({ queryKey: ["planner"] });
      queryClient.invalidateQueries({ queryKey: ["affinity"] });
      setUpdatingId((current) => (current === subtaskId ? null : current));
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to update subtask";
      toast.error(message);
    },
    onSettled: () => {
      setUpdatingId(null);
    },
  });

  const columns = useMemo(
    () => [
      {
        key: "id",
        header: "Subtask",
        render: (row: Subtask) => <SubtaskIdChip value={row.id} />,
        className: "w-48",
      },
      {
        key: "ticket_id",
        header: "Ticket",
        render: (row: Subtask) => <span className="font-mono text-xs text-primary-200">{row.ticket_id}</span>,
        className: "w-32",
      },
      {
        key: "seq",
        header: "#",
        render: (row: Subtask) => row.seq,
        className: "w-12",
      },
      {
        key: "text_sub",
        header: "Description",
        render: (row: Subtask) => (
          <div className="flex flex-col gap-1">
            <span className="font-medium text-slate-100">{row.text_sub}</span>
            {row.tags?.length ? (
              <div className="flex flex-wrap gap-1">
                {row.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                    {tag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        render: (row: Subtask) => <StatusBadge status={row.status} />, 
        className: "w-32",
      },
      {
        key: "est_hours",
        header: "Est. Hours",
        render: (row: Subtask) => (row.est_hours ?? "-").toString(),
        className: "w-24",
      },
      {
        key: "actions",
        header: "Actions",
        className: "w-40",
        render: (row: Subtask) => (
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              className="px-3 py-1 text-xs"
              disabled={row.status === "done" || markDoneMutation.isPending}
              onClick={() => markDoneMutation.mutate(row.id)}
            >
              {row.status === "done"
                ? "Completed"
                : updatingId === row.id && markDoneMutation.isPending
                  ? "Updating…"
                  : "Mark done"}
            </Button>
          </div>
        ),
      },
    ],
    [markDoneMutation.isPending, updatingId],
  );

  const handleApplyFilters = (values: FilterValues) => {
    setFilters({
      ticket_id: values.ticket_id.trim() || undefined,
      status: values.status ? values.status.split(/[,\s]+/).filter(Boolean) : undefined,
    });
  };

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
        <div className="flex flex-col gap-2 pb-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Subtask Library</h2>
              <p className="text-sm text-slate-400">Filter, review, and generate subtasks for a ticket.</p>
            </div>
            <Button onClick={() => setOpenCreate(true)}>Generate subtasks</Button>
          </div>
        </div>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={filterForm.handleSubmit(handleApplyFilters)}>
          <TextInput label="Ticket ID" placeholder="FOO-1" {...filterForm.register("ticket_id")} />
          <TextInput label="Status" placeholder="todo,in_progress" {...filterForm.register("status")} />
          <div className="flex items-end justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => filterForm.reset()}>
              Clear
            </Button>
            <Button type="submit" variant="secondary">
              Apply
            </Button>
          </div>
        </form>
        <div className="mt-6">
          <AsyncState
            isLoading={subtasksQuery.isLoading}
            isError={subtasksQuery.isError}
            errorMessage={subtasksQuery.error instanceof Error ? subtasksQuery.error.message : undefined}
          >
            <Table<Subtask>
              data={subtasksQuery.data ?? []}
              columns={columns}
              emptyMessage="No subtasks found. Adjust filters or generate new ones."
            />
          </AsyncState>
        </div>
      </section>

      <Modal
        open={openCreate}
        title="Generate subtasks"
        onClose={() => setOpenCreate(false)}
        actions={
          <>
            <Button variant="ghost" onClick={() => setOpenCreate(false)}>
              Cancel
            </Button>
            <Button
              onClick={createForm.handleSubmit((values) => createMutation.mutate(values))}
              loading={createMutation.isPending}
            >
              Generate
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={createForm.handleSubmit((values) => createMutation.mutate(values))}>
          <TextInput
            label="Ticket ID"
            placeholder="FOO-1"
            {...createForm.register("ticket_id", { required: "Ticket id is required" })}
            error={createForm.formState.errors.ticket_id?.message}
          />
          <TextInput
            label="Mode"
            placeholder="append or replace"
            {...createForm.register("mode", {
              validate: (value) =>
                value === "append" || value === "replace" || "Mode must be append or replace",
            })}
          />
          <TextArea
            label="Bullets JSON (optional)"
            placeholder='[{"text_sub":"Set up project","tags":["setup"]}]'
            rows={6}
            {...createForm.register("bullets")}
          />
          <p className="text-xs text-slate-400">
            Leave bullets empty to let the backend LLM generator create them. Custom JSON is passed directly to the
            <code className="ml-1 font-mono">/tools/subtasks/create_for_ticket</code> endpoint.
          </p>
        </form>
      </Modal>
    </div>
  );
}

export default SubtasksPage;
