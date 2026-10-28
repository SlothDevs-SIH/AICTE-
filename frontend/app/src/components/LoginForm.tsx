import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api'
import { ROLE_LABEL, useAuth } from '../auth'
import { OrganicButton } from './OrganicButton'

const DEMO = [
  ['officer.rb', 'unit_officer', 'RB'], ['supervisor.rb', 'unit_supervisor', 'RB'], ['officer.pgrc', 'unit_officer', 'PGRC'],
  ['supervisor.pgrc', 'unit_supervisor', 'PGRC'], ['regional.west', 'regional_officer', 'West'], ['management', 'management', ''],
  ['authority', 'competent_authority', ''], ['admin', 'admin', ''], ['auditor', 'auditor', ''],
]

/** Sign-in form shared by the /login page and the panel that opens from the landing page. */
export function LoginForm({ from = '/app' }: { from?: string }) {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [show, setShow] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await login(email, pw); nav(from, { replace: true }) }
    catch (x) { setErr((x as ApiError).status === 423 ? 'This account is locked for a while after too many attempts. Try again later.' : 'Email or password is incorrect.') }
    finally { setBusy(false) }
  }
  return (
    <>
      <form onSubmit={submit} className="loginform">
        <label className="f">Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" required />
        </label>
        <label className="f">Password
          <span className="pwrow">
            <input type={show ? 'text' : 'password'} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="off" required />
            <button type="button" className="pwtoggle" onClick={() => setShow((s) => !s)} aria-pressed={show} aria-label={show ? 'Hide password' : 'Show password'}>{show ? 'Hide' : 'Show'}</button>
          </span>
        </label>
        {err && <div className="notice err" role="alert">{err}</div>}
        <div><OrganicButton type="submit" size="md" disabled={busy} label={busy ? 'Signing in…' : 'Sign in'} /></div>
      </form>
      <p className="muted" style={{ margin: '1.1rem 0 .5rem' }}>Demo accounts (generated). Pick one to fill the email; the demo password is in the project README.</p>
      <div className="chips">
        {DEMO.map(([u, role, unit]) => (
          <button key={u} type="button" className="chip" onClick={() => setEmail(`${u}@demo.samanvay.in`)}>{ROLE_LABEL[role]}{unit ? ` · ${unit}` : ''}</button>
        ))}
      </div>
    </>
  )
}
