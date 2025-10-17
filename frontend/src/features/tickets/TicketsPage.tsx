import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { api, Ticket, TicketSearchRequest, TicketUploadRow } from "../../api/client";
import { Button } from "../../components/Button";
import { TextArea, TextInput } from "../../components/Input";
import { Table } from "../../components/Table";
import { StatusBadge } from "../../components/StatusBadge";
import { AsyncState } from "../../components/AsyncState";

interface UploadFormValues {
  payload: string;
}

interface SearchFormValues {
  ids: string;
  status: string;
  text: string;
  tech: string;
}

export function TicketsPage() {
  const uploadForm = useForm<UploadFormValues>({
    defaultValues: { payload: "" },
  });
  const searchForm = useForm<SearchFormValues>({
    defaultValues: { ids: "", status: "", text: "", tech: "" },
  });

  const [searchParams, setSearchParams] = useState<TicketSearchRequest>({});

  const uploadMutation = useMutation({
    mutationFn: async (values: UploadFormValues) => {
      const data = JSON.parse(values.payload) as TicketUploadRow[] | { tickets: TicketUploadRow[] };
      const tickets = Array.isArray(data) ? data : data.tickets;
      if (!Array.isArray(tickets)) {
        throw new Error("Payload must be an array of tickets or { tickets: [...] }");
      }
      return api.uploadTickets({ tickets });
    },
    onSuccess: (result) => {
      toast.success(`Uploaded ${result.inserted} inserted / ${result.updated} updated tickets.`);
      uploadForm.reset();
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
            Paste an array of ticket objects or a JSON payload with a <code className="font-mono">tickets</code> property. Data is
            sent to <code className="font-mono">/tools/tickets/load_manual</code>.
          </p>
        </div>
        <form className="space-y-4" onSubmit={uploadForm.handleSubmit((values) => uploadMutation.mutate(values))}>
          <TextArea
            label="Ticket JSON"
            rows={10}
            placeholder='[{"id":"FOO-1","title":"Implement feature"}]'
            {...uploadForm.register("payload", { required: "Paste at least one ticket" })}
            error={uploadForm.formState.errors.payload?.message}
          />
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-slate-500">Warnings will be returned in the response toast.</span>
            <Button type="submit" loading={uploadMutation.isPending}>
              Upload tickets
            </Button>
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
