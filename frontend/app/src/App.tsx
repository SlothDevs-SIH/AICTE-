import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { OFFICER_ROLES, ROLE_LABEL, useAuth } from './auth'
import { CommandSearch, type CommandItem } from './components/CommandSearch'
import { TreeMenu, type MenuItem } from './components/TreeMenu'
import { Logo, NoticeTicker, useFetch } from './components/ui'
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
import { CoordinationList, CoordinationThread } from './pages/Coordination'
import Notifications from './pages/Notifications'
import Imports from './pages/Imports'
import Management from './pages/Management'
import Admin from './pages/Admin'

const ALL = ['unit_officer', 'unit_supervisor', 'regional_officer', 'management', 'competent_authority', 'admin', 'auditor']
const OFFICE = [...OFFICER_ROLES, 'admin']
const OVERSIGHT = [...OFFICER_ROLES, 'management', 'competent_authority', 'admin', 'auditor']
type Leaf = MenuItem & { roles: string[] }
type Group = { id: string; label: string; icon: string; to?: string; roles?: string[]; children?: Leaf[] }
// Related pages sit together so the menu stays short; a group with one visible page collapses into that page.
const TREE: Group[] = [
  { id: 'dash', label: 'Dashboard', icon: '▦', to: '/app', roles: ALL },
  { id: 'complaints', label: 'Complaints', icon: '☰', children: [
    { id: 'c-search', label: 'Search complaints', to: '/app/complaints', roles: ALL },
    { id: 'c-new', label: 'New complaint', to: '/app/new', roles: OFFICE },
    { id: 'c-import', label: 'Import cases', to: '/app/imports', roles: OFFICE },
  ] },
  { id: 'coord', label: 'Overlaps and action', icon: '⇄', children: [
    { id: 'o-overlaps', label: 'Overlaps', to: '/app/overlaps', roles: OVERSIGHT },
    { id: 'o-gate', label: 'Action Gate', to: '/app/gate', roles: [...OFFICER_ROLES, 'competent_authority'] },
    { id: 'o-coord', label: 'Coordination', to: '/app/coordination', roles: OVERSIGHT },
    { id: 'o-esc', label: 'Escalations', to: '/app/escalations', roles: ['unit_supervisor', 'competent_authority', 'management', 'admin'] },
  ] },
  { id: 'colleges', label: 'Colleges', icon: '◧', to: '/app/colleges', roles: ALL },
  { id: 'insight', label: 'Insights', icon: '◈', children: [
    { id: 'i-mgmt', label: 'Management view', to: '/app/management', roles: ['management', 'competent_authority', 'admin', 'auditor'] },
    { id: 'i-reports', label: 'Reports', to: '/app/reports', roles: ALL },
  ] },
  { id: 'oversight', label: 'Oversight', icon: '✓', children: [
    { id: 'v-audit', label: 'Audit & Verify', to: '/app/audit', roles: ['auditor', 'admin', 'competent_authority'] },
    { id: 'v-status', label: 'System status', to: '/app/status', roles: ALL },
  ] },
  { id: 'admin', label: 'Admin', icon: '⚙', to: '/app/admin', roles: ['admin'] },
]

function menuFor(role: string): MenuItem[] {
  const out: MenuItem[] = []
  for (const g of TREE) {
    if (g.to) { if (g.roles?.includes(role)) out.push({ id: g.id, label: g.label, icon: g.icon, to: g.to }); continue }
    const kids: MenuItem[] = (g.children ?? []).filter((c) => c.roles.includes(role)).map((c) => ({ id: c.id, label: c.label, to: c.to }))
    if (kids.length === 1) out.push({ ...kids[0], icon: g.icon })
    else if (kids.length > 1) out.push({ id: g.id, label: g.label, icon: g.icon, children: kids })
  }
  return out
}
const flat = (items: MenuItem[]): MenuItem[] => items.flatMap((i) => (i.children ? flat(i.children) : [i]))
const activeLeaf = (items: MenuItem[], path: string): string | null => {
  const leaves = flat(items).filter((l) => l.to && (l.to === '/app' ? path === '/app' : path === l.to || path.startsWith(l.to + '/')))
  leaves.sort((x, y) => (y.to?.length ?? 0) - (x.to?.length ?? 0))
  return leaves[0]?.id ?? null
}
const initials = (name: string) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('') || '?'

function Shell() {
  const { me, ready, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  const notes = useFetch<any>(me ? '/notifications' : null, [loc.pathname])
  useEffect(() => setOpen(false), [loc.pathname])
  const menu = useMemo(() => (me ? menuFor(me.role) : []), [me])
  const commands = useMemo<CommandItem[]>(() => {
    const pages = flat(menu).map((l) => ({ id: l.id, title: l.label, section: 'Suggestions', icon: l.icon, action: () => nav(l.to!) }))
    return [
      ...pages,
      { id: 'x-notes', title: 'Notifications', section: 'Settings', icon: '◔', action: () => nav('/app/notifications') },
      { id: 'x-out', title: 'Sign out', section: 'Settings', icon: '↩', action: async () => { await logout(); nav('/') } },
      { id: 'x-home', title: 'Landing page', section: 'Help', icon: '⌂', action: () => nav('/') },
    ]
  }, [menu, nav, logout])
  const findCases = useCallback((q: string): CommandItem[] => [
    { id: 'q-cases', title: `Search complaints for “${q}”`, section: 'Search', icon: '☰', action: () => nav(`/app/complaints?q=${encodeURIComponent(q)}`) },
    { id: 'q-colleges', title: `Search colleges for “${q}”`, section: 'Search', icon: '◧', action: () => nav(`/app/colleges?q=${encodeURIComponent(q)}`) },
  ], [nav])
  if (!ready) return <p style={{ padding: '2rem' }} role="status">Loading…</p>
  if (!me) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />
  return (
    <div className="shell">
      <a className="skip" href="#main">Skip to content</a>
      <aside className={`side ${open ? 'open' : ''}`} aria-label="Primary">
        <Link to="/" className="brand"><Logo /> SAMANVAY</Link>
        <div className="profile">
          <span className="avatar" aria-hidden="true">{initials(me.name)}</span>
          <div className="who">
            <strong>{me.name}</strong>
            <span>{ROLE_LABEL[me.role]}</span>
          </div>
          <button type="button" className="signout" onClick={async () => { await logout(); nav('/') }} aria-label="Sign out" title="Sign out">⏻</button>
        </div>
        <nav aria-label="Pages">
          <TreeMenu menuData={menu} activeId={activeLeaf(menu, loc.pathname)} onSelect={(i) => i.to && nav(i.to)} />
        </nav>
      </aside>
      <div className="main">
        <header className="top">
          <button className="btn sm menu-btn" onClick={() => setOpen(!open)} aria-label="Toggle menu">☰</button>
          <CommandSearch items={commands} extra={findCases} />
          <NoticeTicker />
          <Link className="btn sm" to="/app/notifications" aria-label={`Notifications, ${notes.data?.unread ?? 0} unread`}>◔ {notes.data?.unread ? <strong>{notes.data.unread} unread</strong> : 'Notifications'}</Link>
        </header>
        <main id="main" className="content page-in" key={loc.pathname}><Outlet /></main>
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
        <Route path="coordination" element={<CoordinationList />} />
        <Route path="coordination/:id" element={<CoordinationThread />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="imports" element={<Imports />} />
        <Route path="management" element={<Management />} />
        <Route path="admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
