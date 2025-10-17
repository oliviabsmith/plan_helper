import { useMemo, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { api, Ticket, TicketSearchRequest, TicketUploadRow } from "../../api/client";
import { Button } from "../../components/Button";
import { TextArea, TextInput } from "../../components/Input";
import { Table } from "../../components/Table";
import { StatusBadge } from "../../components/StatusBadge";
import { AsyncState } from "../../components/AsyncState";

interface UploadTicketFormRow {
  id: string;
  title: string;
  description: string;
  story_points: string;
  labels: string;
  components: string;
  tech: string;
  due_date: string;
  sprint: string;
  status: string;
}

interface UploadFormValues {
  tickets: UploadTicketFormRow[];
}

interface SearchFormValues {
  ids: string;
  status: string;
  text: string;
  tech: string;
}

export function TicketsPage() {
  const emptyTicket: UploadTicketFormRow = {
    id: "",
    title: "",
    description: "",
    story_points: "",
    labels: "",
    components: "",
    tech: "",
    due_date: "",
    sprint: "",
    status: "",
  };

  const uploadForm = useForm<UploadFormValues>({
    defaultValues: { tickets: [{ ...emptyTicket }] },
  });

  const ticketFields = useFieldArray({
    control: uploadForm.control,
    name: "tickets",
  });
  const searchForm = useForm<SearchFormValues>({
    defaultValues: { ids: "", status: "", text: "", tech: "" },
  });

  const [searchParams, setSearchParams] = useState<TicketSearchRequest>({});

  const uploadMutation = useMutation({
    mutationFn: async (values: UploadFormValues) => {
      const parseList = (value: string) =>
        value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

      const tickets: TicketUploadRow[] = values.tickets.map((ticket, index) => {
        const id = ticket.id.trim();
        if (!id) {
          throw new Error(`Ticket ${index + 1} is missing an ID.`);
        }

        const storyPointsValue = ticket.story_points.trim();
        let story_points: number | undefined;
        if (storyPointsValue) {
          const parsed = Number(storyPointsValue);
          if (Number.isNaN(parsed)) {
            throw new Error(`Story points for ticket ${id} must be a number`);
          }
          story_points = parsed;
        }

        const labels = ticket.labels.trim() ? parseList(ticket.labels) : undefined;
        const components = ticket.components.trim() ? parseList(ticket.components) : undefined;
        const tech = ticket.tech.trim() ? parseList(ticket.tech) : undefined;

        const dueDate = ticket.due_date.trim();
        const sprint = ticket.sprint.trim();
        const status = ticket.status.trim();

        return {
          id,
          title: ticket.title.trim() || undefined,
          description: ticket.description.trim() || undefined,
          story_points,
          labels,
          components,
          tech,
          due_date: dueDate ? dueDate : undefined,
          sprint: sprint || undefined,
          status: status || undefined,
        } satisfies TicketUploadRow;
      });

      if (tickets.length === 0) {
        throw new Error("Add at least one ticket with an ID before uploading.");
      }

      return api.uploadTickets({ tickets });
    },
    onSuccess: (result) => {
      toast.success(`Uploaded ${result.inserted} inserted / ${result.updated} updated tickets.`);
      uploadForm.reset({ tickets: [{ ...emptyTicket }] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to upload tickets";
      toast.error(message);
    },
  });

  const ticketsQuery = useQuery({
    queryKey: ["tickets", searchParams],
    queryFn: () => api.searchTickets(searchParams),
    enabled: Object.keys(searchParams).length > 0,
  });

  const tickets = ticketsQuery.data ?? [];

  const tableColumns = useMemo(
    () => [
      {
        key: "id",
        header: "ID",
        render: (ticket: Ticket) => <span className="font-mono text-xs text-primary-200">{ticket.id}</span>,
      },
      {
        key: "title",
        header: "Title",
        render: (ticket: Ticket) => (
          <div className="flex flex-col gap-1">
            <span className="font-medium text-slate-100">{ticket.title}</span>
            {ticket.description && (
              <p className="text-xs text-slate-400 max-h-16 overflow-hidden text-ellipsis">
                {ticket.description}
              </p>
            )}
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        render: (ticket: Ticket) => <StatusBadge status={ticket.status} />, 
      },
      {
        key: "story_points",
        header: "SP",
        render: (ticket: Ticket) => <span>{ticket.story_points ?? "-"}</span>,
      },
      {
        key: "tech",
        header: "Tech",
        render: (ticket: Ticket) => (
          <div className="flex flex-wrap gap-1">
            {ticket.tech?.map((tag) => (
              <span key={tag} className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                {tag}
              </span>
            ))}
          </div>
        ),
      },
      {
        key: "sprint",
        header: "Sprint",
        render: (ticket: Ticket) => ticket.sprint ?? "-",
      },
    ],
    [],
  );

  const handleSearch = (values: SearchFormValues) => {
    const params: TicketSearchRequest = {};
    if (values.ids) params.ids = values.ids.split(/[,\s]+/).filter(Boolean);
    if (values.status) params.status = values.status.split(/[,\s]+/).filter(Boolean);
    if (values.tech) params.tech = values.tech.split(/[,\s]+/).filter(Boolean);
    if (values.text) params.text = values.text.trim();
    setSearchParams(params);
  };

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
        <div className="flex flex-col gap-2 pb-4">
          <h2 className="text-lg font-semibold text-slate-100">Upload Tickets</h2>
          <p className="text-sm text-slate-400">
            Fill in the ticket details below. Data is sent to <code className="font-mono">/tools/tickets/load_manual</code>.
          </p>
        </div>
        <form className="space-y-6" onSubmit={uploadForm.handleSubmit((values) => uploadMutation.mutate(values))}>
          <div className="space-y-4">
            {ticketFields.fields.map((field, index) => (
              <div key={field.id} className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/80 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200">Ticket {index + 1}</h3>
                  {ticketFields.fields.length > 1 && (
                    <Button type="button" variant="ghost" onClick={() => ticketFields.remove(index)}>
                      Remove
                    </Button>
                  )}
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <TextInput
                    label="Ticket ID"
                    placeholder="FOO-123"
                    {...uploadForm.register(`tickets.${index}.id`, {
                      required: "Ticket ID is required",
                      validate: (value) => value.trim().length > 0 || "Ticket ID is required",
                    })}
                    error={uploadForm.formState.errors.tickets?.[index]?.id?.message}
                  />
                  <TextInput
                    label="Title"
                    placeholder="Implement feature"
                    {...uploadForm.register(`tickets.${index}.title`)}
                  />
                </div>
                <TextArea
                  label="Description"
                  rows={4}
                  placeholder="Short description of the work"
                  {...uploadForm.register(`tickets.${index}.description`)}
                />
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  <TextInput
                    label="Story points"
                    placeholder="5"
                    {...uploadForm.register(`tickets.${index}.story_points`)}
                  />
                  <TextInput
                    label="Status"
                    placeholder="todo"
                    {...uploadForm.register(`tickets.${index}.status`)}
                  />
                  <TextInput
                    label="Sprint"
                    placeholder="Sprint 24"
                    {...uploadForm.register(`tickets.${index}.sprint`)}
                  />
                  <TextInput
                    label="Due date"
                    placeholder="2024-05-01"
                    {...uploadForm.register(`tickets.${index}.due_date`)}
                    hint="YYYY-MM-DD"
                  />
                  <TextInput
                    label="Tech tags"
                    placeholder="python,react"
                    {...uploadForm.register(`tickets.${index}.tech`)}
                    hint="Comma separated"
                  />
                  <TextInput
                    label="Labels"
                    placeholder="backend,api"
                    {...uploadForm.register(`tickets.${index}.labels`)}
                    hint="Comma separated"
                  />
                  <TextInput
                    label="Components"
                    placeholder="auth,ui"
                    {...uploadForm.register(`tickets.${index}.components`)}
                    hint="Comma separated"
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Button type="button" variant="secondary" onClick={() => ticketFields.append({ ...emptyTicket })}>
              Add another ticket
            </Button>
            <div className="flex items-center gap-4">
              <span className="text-xs text-slate-500">Warnings will be returned in the response toast.</span>
              <Button type="submit" loading={uploadMutation.isPending}>
                Upload tickets
              </Button>
            </div>
          </div>
        </form>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-900/30">
        <div className="flex flex-col gap-2 pb-4">
          <h2 className="text-lg font-semibold text-slate-100">Search Tickets</h2>
          <p className="text-sm text-slate-400">Filter tickets stored in the backend ticket store and explore key details.</p>
        </div>
        <form
          className="grid gap-4 md:grid-cols-2"
          onSubmit={searchForm.handleSubmit((values) => handleSearch(values))}
        >
          <TextInput label="IDs" placeholder="FOO-1, FOO-2" {...searchForm.register("ids")} />
          <TextInput label="Status" placeholder="todo,in_progress" {...searchForm.register("status")} />
          <TextInput label="Text search" placeholder="search terms" {...searchForm.register("text")} />
          <TextInput label="Tech tags" placeholder="python,react" {...searchForm.register("tech")} />
          <div className="md:col-span-2 flex items-center justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => searchForm.reset()}>
              Reset
            </Button>
            <Button type="submit" variant="secondary">
              Run search
            </Button>
          </div>
        </form>

        <div className="mt-6">
          <AsyncState
            isLoading={ticketsQuery.isLoading}
            isError={ticketsQuery.isError}
            errorMessage={ticketsQuery.error instanceof Error ? ticketsQuery.error.message : undefined}
          >
            <Table<Ticket>
              data={tickets}
              columns={tableColumns}
              emptyMessage="No tickets matched your filters."
            />
          </AsyncState>
        </div>
      </section>
    </div>
  );
}

export default TicketsPage;
