import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { ROLE_LABEL } from '../auth'
import { ErrorBox, Loading, useFetch } from '../components/ui'

const NUMERIC_HELP: Record<string, string> = {
  pending_reminder_days: 'Days of no activity before a reminder', sla_warn_fraction: 'Share of the time limit used before a warning (0 to 1)',
  escalation_grace_days: 'Days past due before suggesting escalation', alert_budget_per_day: 'Most alerts one officer gets per day',
  coordination_days: 'Days a coordination request stays open', cluster_min_size: 'Cases needed to form a cluster', cluster_window_days: 'Cluster window in days',
}

export default function Admin() {
  const st = useFetch<any>('/admin/settings')
  const users = useFetch<any>('/admin/users')
  const sc = useFetch<any>('/admin/scenarios')
  const ref = useFetch<any>('/reference')
  const imp = useFetch<any>('/admin/jobs/import-aicte')
  useEffect(() => {
    if (imp.data?.state !== 'running') return
    const t = setInterval(imp.reload, 3000)
    return () => clearInterval(t)
  }, [imp.data?.state, imp.reload])
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [nu, setNu] = useState({ email: '', name: '', role: 'unit_officer', password: '', unit_code: 'RB' })
  const [busy, setBusy] = useState(false)
  const say = (ok: boolean, text: string) => setMsg({ ok, text })
  const wrap = async (fn: () => Promise<any>, ok: string) => {
    setBusy(true); setMsg(null)
    try { await fn(); if (ok) say(true, ok) } catch (e) { say(false, (e as ApiError).message || 'Something went wrong.') }
    finally { setBusy(false) }
  }
  const setSetting = (k: string, value: unknown) => wrap(async () => { await api(`/admin/settings/${k}`, { method: 'PUT', body: { value } }); st.reload() }, `Saved ${k}.`)
  return (
    <>
      <h1>Admin</h1>
      {(msg || busy) && (
        <div className={`notice ${busy ? 'warn' : msg!.ok ? 'ok' : 'err'}`} role="status"
          style={{ position: 'sticky', top: '4.2rem', zIndex: 6, boxShadow: 'var(--shadow)' }}>
          {busy ? 'Working… asking the model can take several seconds.' : msg!.text}
        </div>
      )}

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Check existing overlaps</h2>
        <p className="muted">The AI reading of different wording is always on when the server has a <code>GEMINI_API_KEY</code>. This asks the model about overlaps that were found before, where no known problem type matched. Only case titles and descriptions are sent, never names or contact details. Answers appear in the Match Receipt as AI-written and never act on their own.</p>
        <p><button className="btn primary" disabled={busy} onClick={() => wrap(async () => { const r = await api('/admin/jobs/ai-rescan', { method: 'POST' }); say(r.no_answer === 0, `${r.asked === 0 ? 'Nothing to ask: every open overlap already matches a known problem type or has an AI answer. ' : ''}Asked about ${r.asked} existing overlaps: ${r.now_same_issue} read as the same issue, ${r.no_answer} got no usable answer.${r.last_error ? ' Reason: ' + r.last_error : ''}`) }, '')}>Check existing overlaps</button></p>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Alerts and escalation</h2>
        {st.loading && !st.data && <Loading what="settings" />}
        {st.error && <ErrorBox error={st.error} retry={st.reload} />}
        {st.data && (
          <>
            <label style={{ display: 'flex', gap: '.6rem', alignItems: 'center' }}>
              <input type="checkbox" style={{ width: 'auto', minHeight: 0 }} checked={st.data.items.auto_escalate} onChange={(e) => setSetting('auto_escalate', e.target.checked)} />
              <span><strong>Escalate automatically</strong> to Level 2 when a case is well past its time limit. Off by default: the system then only tells a supervisor, and a person escalates. Every automatic escalation is recorded as done by "system".</span>
            </label>
            <div className="grid2" style={{ marginTop: '1rem' }}>
              {Object.entries(NUMERIC_HELP).map(([k, help]) => (
                <label className="f" key={k}>{k.replace(/_/g, ' ')}<small>{help}</small>
                  <input type="number" step={k === 'sla_warn_fraction' ? 0.05 : 1} defaultValue={st.data.items[k]} onBlur={(e) => {
                    const v = k === 'sla_warn_fraction' ? parseFloat(e.target.value) : parseInt(e.target.value, 10)
                    if (!Number.isNaN(v) && v !== st.data.items[k]) setSetting(k, v)
                  }} /></label>
              ))}
            </div>
            <p><button className="btn" onClick={() => wrap(async () => { const r = await api('/admin/jobs/sla', { method: 'POST' }); say(true, `Checked time limits: ${r.reminders} reminders, ${r.sla_approaching} approaching, ${r.sla_breached} past limit, ${r.escalation_alerts} escalation suggestions, ${r.auto_escalated} auto-escalated, ${r.threads_expired} coordination requests expired.`) }, '')}>Run the time-limit check now</button></p>
          </>
        )}
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Real AICTE colleges</h2>
        <p className="muted">Loads the public list of AICTE-approved institutions (name, AICTE ID, district, state) into the college registry from AICTE's own site. Complaints stay simulated. The server must be able to reach the AICTE site; on a free host the list is lost at each deploy unless <code>AICTE_AUTO_IMPORT=true</code> is set.</p>
        {imp.data && imp.data.state !== 'idle' && (
          <p role="status">
            <strong>{imp.data.state === 'running' ? 'Loading…' : 'Finished.'}</strong> {imp.data.done_states} of {imp.data.total_states} states · {imp.data.added} colleges added, {imp.data.updated} updated.
            {imp.data.errors.length > 0 && <><br /><span className="muted">Problems: {imp.data.errors.slice(0, 4).join(' | ')}{imp.data.errors.length > 4 ? ` … and ${imp.data.errors.length - 4} more` : ''}</span></>}
          </p>
        )}
        <button className="btn" disabled={busy || imp.data?.state === 'running'} onClick={() => wrap(async () => { await api('/admin/jobs/import-aicte', { method: 'POST' }); imp.reload() }, 'Started. Progress shows here.')}>Load real AICTE colleges</button>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Demo scenarios</h2>
        <p className="muted">Adds new synthetic cases so you can show a situation live. Refused if any non-synthetic data exists.</p>
        {sc.data?.items.map((s: any) => (
          <div className="row" key={s.id} style={{ margin: '.4rem 0' }}>
            <button className="btn sm" onClick={() => wrap(async () => { const r = await api(`/admin/scenarios/${s.id}/load`, { method: 'POST' }); say(true, `Loaded ${s.id}: ${r.institution}`) }, '')}>Load</button>
            <span><strong>{s.id.replace(/_/g, ' ')}</strong> <span className="muted">{s.description}</span></span>
          </div>
        ))}
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Users</h2>
        <div className="tablewrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Unit</th><th>Active</th></tr></thead>
          <tbody>{users.data?.items.map((u: any) => (
            <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{ROLE_LABEL[u.role]}</td><td>{u.unit ?? '—'}</td>
              <td><input type="checkbox" style={{ width: 'auto', minHeight: 0 }} checked={u.is_active} aria-label={`${u.name} active`}
                onChange={(e) => wrap(async () => { await api(`/admin/users/${u.id}`, { method: 'PATCH', body: { is_active: e.target.checked } }); users.reload() }, 'User updated.')} /></td></tr>))}</tbody></table></div>
        <h3 style={{ marginTop: '1rem' }}>Add a user</h3>
        <div className="grid2">
          <label className="f">Name<input value={nu.name} onChange={(e) => setNu({ ...nu, name: e.target.value })} /></label>
          <label className="f">Email<input value={nu.email} onChange={(e) => setNu({ ...nu, email: e.target.value })} /></label>
          <label className="f">Role<select value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })}>{Object.entries(ROLE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="f">Unit<select value={nu.unit_code} onChange={(e) => setNu({ ...nu, unit_code: e.target.value })}><option value="">None</option>{ref.data?.units.map((u: any) => <option key={u.id}>{u.code}</option>)}</select></label>
          <label className="f">Temporary password (10+ characters)<input type="password" autoComplete="new-password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} /></label>
        </div>
        <p><button className="btn primary" disabled={!nu.email || !nu.name || nu.password.length < 10}
          onClick={() => wrap(async () => { await api('/admin/users', { method: 'POST', body: { ...nu, unit_code: nu.unit_code || null } }); users.reload(); setNu({ ...nu, email: '', name: '', password: '' }) }, 'User created.')}>Create user</button></p>
      </section>
    </>
  )
}
