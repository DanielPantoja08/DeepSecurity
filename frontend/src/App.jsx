import { useState } from "react";
import Recognition from "./pages/Recognition";
import Identities from "./pages/Identities";
import SystemInfo from "./pages/SystemInfo";
import Logs from "./pages/Logs";
import "./index.css";

const NAV = [
  {
    id: "recognition",
    label: "Reconocimiento",
    icon: (
      <svg className="nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.882V15.118a1 1 0 01-1.447.906L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
      </svg>
    ),
  },
  {
    id: "identities",
    label: "Identidades",
    icon: (
      <svg className="nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    id: "logs",
    label: "Historial",
    icon: (
      <svg className="nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
  {
    id: "sysinfo",
    label: "Sistema",
    icon: (
      <svg className="nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

const PAGES = {
  recognition: <Recognition />,
  identities: <Identities />,
  logs: <Logs />,
  sysinfo: <SystemInfo />,
};

export default function App() {
  const [active, setActive] = useState("recognition");

  return (
    <div className="layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>🛡️ DeepSecurity</h1>
          <span>Sistema de Identificación AI</span>
        </div>
        <ul className="sidebar-nav">
          {NAV.map((item) => (
            <li key={item.id}>
              <button
                className={active === item.id ? "active" : ""}
                onClick={() => setActive(item.id)}
              >
                {item.icon}
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* ── Page content ── */}
      <main className="main">{PAGES[active]}</main>
    </div>
  );
}
