import { NavLink, Outlet } from "react-router-dom";
import { clsx } from "clsx";

const navigation = [
  { to: "/tickets", label: "Tickets" },
  { to: "/subtasks", label: "Subtasks" },
  { to: "/affinity", label: "Affinity" },
  { to: "/planner", label: "Planner" },
  { to: "/reports", label: "Reports" },
];

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex min-h-screen flex-col lg:flex-row">
        <aside className="w-full border-b border-slate-800 bg-slate-900/80 px-4 py-3 backdrop-blur lg:h-screen lg:w-64 lg:border-b-0 lg:border-r">
          <h1 className="text-xl font-semibold tracking-tight text-primary-400">Plan Helper</h1>
          <p className="mt-1 text-sm text-slate-400">Frontend control center for the planning tools.</p>
          <nav className="mt-6 flex flex-wrap gap-2 lg:flex-col">
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    "rounded-md px-3 py-2 text-sm font-medium transition",
                    isActive
                      ? "bg-primary-500/20 text-primary-200"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="flex-1 bg-slate-950/60 px-4 pb-10 pt-6 lg:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
