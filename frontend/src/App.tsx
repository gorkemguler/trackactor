import { createContext, useContext } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useApi } from "./api";
import type { Enums } from "./types";
import Dashboard from "./pages/Dashboard";
import LookupPage from "./pages/LookupPage";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import ActorsPage from "./pages/ActorsPage";
import ActorDetailPage from "./pages/ActorDetailPage";

const FALLBACK: Enums = {
  actor_types: ["unknown"],
  channel_types: ["other"],
  case_statuses: ["open", "tracking", "awaiting_response", "responded", "closed"],
  priorities: ["low", "medium", "high", "critical"],
  directions: ["inbound", "outbound"],
};

const EnumsContext = createContext<Enums>(FALLBACK);
export const useEnums = () => useContext(EnumsContext);

export default function App() {
  const { data: enums } = useApi<Enums>("/meta/enums");

  return (
    <EnumsContext.Provider value={enums ?? FALLBACK}>
      <div className="app">
        <nav className="sidebar">
          <div className="brand">
            track<span>actor</span>
          </div>
          <NavLink to="/dashboard" className="nav-link">
            ▚ Dashboard
          </NavLink>
          <NavLink to="/lookup" className="nav-link">
            ⌕ Lookup
          </NavLink>
          <NavLink to="/cases" className="nav-link">
            ▤ Cases
          </NavLink>
          <NavLink to="/actors" className="nav-link">
            ☠ Actors
          </NavLink>
          <div className="spacer" />
          <a className="nav-link" href="/api/docs" target="_blank" rel="noreferrer">
            ⚙ API docs
          </a>
        </nav>
        <main className="main">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/lookup" element={<LookupPage />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/cases/:id" element={<CaseDetailPage />} />
            <Route path="/actors" element={<ActorsPage />} />
            <Route path="/actors/:id" element={<ActorDetailPage />} />
            <Route path="*" element={<div className="empty">Not found</div>} />
          </Routes>
        </main>
      </div>
    </EnumsContext.Provider>
  );
}
