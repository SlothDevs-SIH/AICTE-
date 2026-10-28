import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { DotBackdrop } from '../components/DotBackdrop'
import { Logo } from '../components/ui'

/** The page a password reset link opens. */
export default function ResetPassword() {
  const [sp] = useSearchParams()
  const token = sp.get('token') ?? ''
  const [pw, setPw] = useState('')
  const [show, setShow] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await api('/auth/reset-password', { method: 'POST', body: { token, password: pw } }); setDone(true) }
    catch (x) { setErr((x as ApiError).message) } finally { setBusy(false) }
  }
  return (
    <div className="login-wrap">
      <DotBackdrop />
      <div className="card" style={{ width: 'min(480px, 100%)' }}>
        <Link to="/" className="brand" style={{ marginBottom: '1rem' }}><Logo /> SAMANVAY</Link>
        {done ? (
          <>
            <div className="auth-mail ok" aria-hidden="true">✓</div>
            <h1 style={{ fontSize: '1.6rem' }}>Password changed</h1>
            <p className="muted">You were signed out everywhere else. Sign in with the new password.</p>
            <Link className="btn primary" to="/login">Go to sign in</Link>
          </>
        ) : (
          <form onSubmit={submit} className="loginform">
            <h1 style={{ fontSize: '1.6rem', margin: 0 }}>Choose a new password</h1>
            {!token && <div className="notice err" role="alert">This link is incomplete. Ask for a new one from the sign-in page.</div>}
            <label className="f">New password
              <span className="pwrow">
                <input type={show ? 'text' : 'password'} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" required minLength={10} />
                <button type="button" className="pwtoggle" onClick={() => setShow((s) => !s)} aria-pressed={show}>{show ? 'Hide' : 'Show'}</button>
              </span>
              <small>At least 10 characters, with letters and a digit.</small>
            </label>
            {err && <div className="notice err" role="alert">{err}</div>}
            <div><button className="btn primary" disabled={busy || !token}>{busy ? 'Saving…' : 'Save the new password'}</button></div>
          </form>
        )}
      </div>
    </div>
  )
}
