import { ReactNode } from "react";

interface TableColumn<T> {
  key: keyof T | string;
  header: ReactNode;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface TableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  emptyMessage?: ReactNode;
}

export function Table<T>({ data, columns, emptyMessage }: TableProps<T>) {
  if (!data.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/60 p-6 text-center text-sm text-slate-400">
        {emptyMessage ?? "No data available."}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60">
      <table className="min-w-full text-left text-sm text-slate-200">
        <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            {columns.map((col) => (
              <th key={String(col.key)} className={`px-4 py-3 font-medium ${col.className ?? ""}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx} className="border-t border-slate-800 hover:bg-slate-800/60">
              {columns.map((col) => (
                <td key={String(col.key)} className={`px-4 py-3 align-top ${col.className ?? ""}`}>
                  {col.render ? col.render(row) : (row as Record<string, ReactNode>)[col.key as string]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
