import { useEffect, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { OFFICER_ROLES, ROLE_LABEL, useAuth } from './auth'
import { Logo, SyntheticBadge } from './components/ui'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Complaints from './pages/Complaints'
import NewComplaint from './pages/NewComplaint'
import CaseDetail from './pages/CaseDetail'
import Overlaps from './pages/Overlaps'
import Gate from './pages/Gate'
import Colleges, { College360 } from './pages/Colleges'
import Escalations from './pages/Escalations'
import Reports from './pages/Reports'
import Audit from './pages/Audit'
import Status from './pages/Status'

const ALL = ['unit_officer', 'unit_supervisor', 'regional_officer', 'management', 'competent_authority', 'admin', 'auditor']
const NAV: { to: string; label: string; icon: string; roles: string[] }[] = [
  { to: '/app', label: 'Dashboard', icon: '▦', roles: ALL },
  { to: '/app/complaints', label: 'Complaints', icon: '☰', roles: ALL },
  { to: '/app/new', label: 'New complaint', icon: '＋', roles: [...OFFICER_ROLES, 'admin'] },
  { to: '/app/overlaps', label: 'Overlaps', icon: '⇄', roles: [...OFFICER_ROLES, 'management', 'competent_authority', 'admin', 'auditor'] },
  { to: '/app/gate', label: 'Action Gate', icon: '⛨', roles: [...OFFICER_ROLES, 'competent_authority'] },
  { to: '/app/colleges', label: 'Colleges', icon: '🏛', roles: ALL },
  { to: '/app/escalations', label: 'Escalations', icon: '↑', roles: ['unit_supervisor', 'competent_authority', 'management', 'admin'] },
  { to: '/app/reports', label: 'Reports', icon: '▤', roles: ALL },
  { to: '/app/audit', label: 'Audit & Verify', icon: '🔒', roles: ['auditor', 'admin', 'competent_authority'] },
  { to: '/app/status', label: 'System status', icon: '◉', roles: ALL },
]

function Shell() {
  const { me, ready, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  const [dark, setDark] = useState(document.documentElement.getAttribute('data-theme') === 'dark')
  useEffect(() => setOpen(false), [loc.pathname])
  if (!ready) return <p style={{ padding: '2rem' }} role="status">Loading…</p>
  if (!me) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />
  const toggle = () => {
    const d = !dark
    setDark(d)
    document.documentElement.setAttribute('data-theme', d ? 'dark' : 'light')
    try { localStorage.setItem('theme', d ? 'dark' : 'light') } catch {}
  }
  return (
    <div className="shell">
      <a className="skip" href="#main">Skip to content</a>
      <aside className={`side ${open ? 'open' : ''}`} aria-label="Primary">
        <Link to="/" className="brand"><Logo /> SAMANVAY</Link>
        <nav>
          {NAV.filter((n) => n.roles.includes(me.role)).map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/app'}><span aria-hidden="true">{n.icon}</span> {n.label}</NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="top">
          <div className="row">
            <button className="btn sm menu-btn" onClick={() => setOpen(!open)} aria-label="Toggle menu">☰</button>
            <SyntheticBadge />
          </div>
          <div className="row">
            <button className="btn sm" onClick={toggle} aria-pressed={dark}>{dark ? '☀ Light' : '☾ Dark'}</button>
            <span><strong>{me.name}</strong> <span className="badge b-neutral">{ROLE_LABEL[me.role]}</span></span>
            <button className="btn sm" onClick={async () => { await logout(); nav('/') }}>Sign out</button>
          </div>
        </header>
        <main id="main" className="content"><Outlet /></main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/app" element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="complaints" element={<Complaints />} />
        <Route path="complaints/:id" element={<CaseDetail />} />
        <Route path="new" element={<NewComplaint />} />
        <Route path="overlaps" element={<Overlaps />} />
        <Route path="gate" element={<Gate />} />
        <Route path="colleges" element={<Colleges />} />
        <Route path="colleges/:id" element={<College360 />} />
        <Route path="escalations" element={<Escalations />} />
        <Route path="reports" element={<Reports />} />
        <Route path="audit" element={<Audit />} />
        <Route path="status" element={<Status />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
