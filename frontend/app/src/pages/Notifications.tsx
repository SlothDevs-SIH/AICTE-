import { Link } from 'react-router-dom'
import { api } from '../api'
import { Empty, ErrorBox, Loading, fmtDateTime, useFetch } from '../components/ui'

const KIND: Record<string, [string, string]> = {
  REMINDER: ['b-info', 'Reminder'], SLA_APPROACHING: ['b-warn', 'Time limit close'], SLA_BREACHED: ['b-danger', 'Past time limit'],
  ESCALATION_SUGGESTED: ['b-orange', 'Consider escalating'], COORDINATION_REQUEST: ['b-violet', 'Coordination request'],
  COORDINATION_MESSAGE: ['b-violet', 'Coordination note'], COORDINATION_EXPIRED: ['b-danger', 'Coordination expired'], CONFLICT: ['b-danger', 'Conflict'],
  ROLE_REQUEST: ['b-warn', 'Access request'], ROLE_DECISION: ['b-info', 'Access decision'],
}
export function target(n: any) {
  if (n.ref_type === 'user') return n.kind === 'ROLE_REQUEST' ? '/app/admin' : '/app'
  return n.ref_type === 'complaint' ? `/app/complaints/${n.ref_id}` : n.ref_type === 'coordination' ? `/app/coordination/${n.ref_id}` : '/app'
}

export default function Notifications() {
  const l = useFetch<any>('/notifications')
  const mark = async (id: string) => { await api(`/notifications/${id}/read`, { method: 'POST' }); l.reload() }
  return (
    <>
      <h1>Notifications</h1>
      <p className="muted">Reminders and time-limit alerts. Nothing here is acted on automatically, and the number sent per day is capped so important items stay visible.</p>
      {l.error && <ErrorBox error={l.error} retry={l.reload} />}
      {l.loading && !l.data && <Loading what="notifications" />}
      {l.data && l.data.items.length === 0 && <Empty>You have no notifications.</Empty>}
      <div style={{ display: 'grid', gap: '.6rem' }}>
        {l.data?.items.map((n: any) => {
          const [cls, label] = KIND[n.kind] ?? ['b-neutral', n.kind]
          return (
            <div key={n.id} className="card" style={{ opacity: n.read ? .65 : 1 }}>
              <span className={`badge ${cls}`}>{label}</span> {!n.read && <span className="badge b-neutral">unread</span>}
              <p style={{ margin: '.4rem 0' }}>{n.message}</p>
              <span className="muted">{fmtDateTime(n.created_at)}</span>{' '}
              <Link to={target(n)} onClick={() => !n.read && mark(n.id)}>Open</Link>{' '}
              {!n.read && <button className="btn sm" onClick={() => mark(n.id)}>Mark read</button>}
            </div>
          )
        })}
      </div>
    </>
  )
}
