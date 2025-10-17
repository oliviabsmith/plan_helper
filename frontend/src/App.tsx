import { Navigate, Route, Routes } from "react-router-dom";
import { AppProviders } from "./providers/AppProviders";
import { AppLayout } from "./layouts/AppLayout";
import TicketsPage from "./features/tickets/TicketsPage";
import SubtasksPage from "./features/subtasks/SubtasksPage";
import AffinityPage from "./features/affinity/AffinityPage";
import PlannerPage from "./features/planner/PlannerPage";
import ReportsPage from "./features/reports/ReportsPage";

function App() {
  return (
    <AppProviders>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/tickets" replace />} />
          <Route path="tickets" element={<TicketsPage />} />
          <Route path="subtasks" element={<SubtasksPage />} />
          <Route path="affinity" element={<AffinityPage />} />
          <Route path="planner" element={<PlannerPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/tickets" replace />} />
      </Routes>
    </AppProviders>
  );
}

export default App;
