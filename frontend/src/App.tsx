import { createContext, useContext } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, useApi } from "./api";
import type { Enums, MetaConfig, User } from "./types";
import Dashboard from "./pages/Dashboard";
import LookupPage from "./pages/LookupPage";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import ActorsPage from "./pages/ActorsPage";
import ActorDetailPage from "./pages/ActorDetailPage";
import MessagesPage from "./pages/MessagesPage";
import AuditPage from "./pages/AuditPage";
import SettingsPage from "./pages/SettingsPage";
import LoginPage from "./pages/LoginPage";

const FALLBACK: Enums = {
  actor_types: ["unknown"],
  channel_types: ["other"],
  case_statuses: ["open", "tracking", "awaiting_response", "responded", "closed"],
  priorities: ["low", "medium", "high", "critical"],
  directions: ["inbound", "outbound"],
};

const EnumsContext = createContext<Enums>(FALLBACK);
export const useEnums = () => useContext(EnumsContext);

const UserContext = createContext<User | null>(null);
export const useUser = () => useContext(UserContext);

export default function App() {
  const { data: enums } = useApi<Enums>("/meta/enums");
  const { data: config } = useApi<MetaConfig>("/meta/config");
  const { data: user, error: userError, refetch: refetchUser } = useApi<User>("/auth/me");

  // wait until we know whether login is required
  if (config === null) {
    return <div className="empty">Loading…</div>;
  }
  const loggedIn = user !== null && userError === null;
  if (config.require_login && !loggedIn) {
    return <LoginPage onDone={refetchUser} />;
  }

  return (
    <EnumsContext.Provider value={enums ?? FALLBACK}>
      <UserContext.Provider value={loggedIn ? user : null}>
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
            <NavLink to="/messages" className="nav-link">
              ✉ Messages
            </NavLink>
            <NavLink to="/audit" className="nav-link">
              ⧗ Audit
            </NavLink>
            <div className="spacer" />
            {loggedIn && (
              <div className="nav-user">
                <span>{user.display_name || user.username}</span>
                <button
                  className="btn ghost sm"
                  onClick={async () => {
                    await api.post("/auth/logout", {});
                    refetchUser();
                  }}
                >
                  Sign out
                </button>
              </div>
            )}
            <NavLink to="/settings" className="nav-link">
              ⚙ Settings
            </NavLink>
            <a className="nav-link" href="/api/docs" target="_blank" rel="noreferrer">
              ↗ API docs
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
              <Route path="/messages" element={<MessagesPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<div className="empty">Not found</div>} />
            </Routes>
          </main>
        </div>
      </UserContext.Provider>
    </EnumsContext.Provider>
  );
}
