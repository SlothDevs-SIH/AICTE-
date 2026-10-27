import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api'
import { ROLE_LABEL, useAuth } from '../auth'
import { Logo, SyntheticBadge } from '../components/ui'

const DEMO = [
  ['officer.rb', 'unit_officer', 'RB'], ['supervisor.rb', 'unit_supervisor', 'RB'], ['officer.pgrc', 'unit_officer', 'PGRC'],
  ['supervisor.pgrc', 'unit_supervisor', 'PGRC'], ['regional.west', 'regional_officer', 'West'], ['management', 'management', ''],
  ['authority', 'competent_authority', ''], ['admin', 'admin', ''], ['auditor', 'auditor', ''],
]

export default function Login() {
  const { me, login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation() as any
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  if (me) return <Navigate to={loc.state?.from ?? '/app'} replace />
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await login(email, pw); nav(loc.state?.from ?? '/app', { replace: true }) }
    catch (x) { setErr((x as ApiError).status === 423 ? 'This account is locked for a while after too many attempts. Try again later.' : 'Email or password is incorrect.') }
    finally { setBusy(false) }
  }
  return (
    <div className="login-wrap">
      <div className="card" style={{ width: 'min(480px, 100%)' }}>
        <Link to="/" className="brand" style={{ marginBottom: '1rem' }}><Logo /> SAMANVAY</Link>
        <h1 style={{ fontSize: '1.6rem' }}>Sign in</h1>
        <p><SyntheticBadge /></p>
        <form onSubmit={submit} className="grid2" style={{ gridTemplateColumns: '1fr' }}>
          <label className="f">Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" required />
          </label>
          <label className="f">Password
            <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="off" required />
          </label>
          {err && <div className="notice err" role="alert">{err}</div>}
          <button className="btn primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '1.2rem 0' }} />
        <p className="muted" style={{ margin: '0 0 .5rem' }}>Demo accounts (generated). Pick one to fill the email; the demo password is in the project README.</p>
        <div className="chips">
          {DEMO.map(([u, role, unit]) => (
            <button key={u} type="button" className="chip" onClick={() => setEmail(`${u}@demo.samanvay.in`)}>{ROLE_LABEL[role]}{unit ? ` · ${unit}` : ''}</button>
          ))}
        </div>
      </div>
    </div>
  )
}
