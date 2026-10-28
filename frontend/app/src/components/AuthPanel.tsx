import { useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { OrganicButton } from '@/components/ui/organic-button'

type Mode = 'in' | 'up' | 'sent' | 'forgot' | 'forgot-sent'

const Pw = ({ value, onChange, autoComplete }: { value: string; onChange: (v: string) => void; autoComplete: string }) => {
  const [show, setShow] = useState(false)
  return (
    <span className="pwrow">
      <input type={show ? 'text' : 'password'} value={value} onChange={(e) => onChange(e.target.value)} autoComplete={autoComplete} required />
      <button type="button" className="pwtoggle" onClick={() => setShow((s) => !s)} aria-pressed={show} aria-label={show ? 'Hide password' : 'Show password'}>{show ? 'Hide' : 'Show'}</button>
    </span>
  )
}

/** Sign in and create account, with the e-mail verification step in between. */
export function AuthPanel({ from = '/app', start = 'in' }: { from?: string; start?: 'in' | 'up' }) {
  const { login } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState<Mode>(start)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState<any>(null)
  const [resent, setResent] = useState('')
  const formRef = useRef<HTMLFormElement>(null)

  const run = (fn: () => Promise<void>) => async (e?: FormEvent) => {
    e?.preventDefault()
    if (busy) return
    setBusy(true); setErr(null); setResent('')
    try { await fn() } catch (x) { setErr(x as ApiError) } finally { setBusy(false) }
  }
  const signIn = run(async () => { await login(email, pw); nav(from, { replace: true }) })
  const signUp = run(async () => {
    const r = await api('/auth/register', { method: 'POST', body: { name, email, password: pw } })
    setSent(r); setMode('sent')
  })
  const forgot = run(async () => {
    const r = await api('/auth/forgot-password', { method: 'POST', body: { email } })
    setSent(r); setMode('forgot-sent')
  })
  const resend = async () => {
    setResent('')
    try {
      const r = await api('/auth/resend-verification', { method: 'POST', body: { email } })
      setSent((s: any) => ({ ...s, ...r }))
      setResent(r.email_sent === false ? 'We could not send the e-mail. See the note above.' : 'A new link is on its way.')
    } catch (x) { setResent((x as ApiError).message) }
  }
  const switchTo = (m: Mode) => { setMode(m); setErr(null); setResent('') }

  if (mode === 'forgot' || mode === 'forgot-sent') {
    return mode === 'forgot' ? (
      <form onSubmit={forgot} className="loginform">
        <h2 style={{ margin: 0 }}>Forgot your password?</h2>
        <p className="muted" style={{ margin: 0 }}>Enter the e-mail you signed up with. We will send a link to choose a new password.</p>
        <label className="f">E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required autoFocus />
        </label>
        {err && <div className="notice err" role="alert">{err.message}</div>}
        <div style={{ display: 'flex', gap: '.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn primary" disabled={busy}>{busy ? 'Sending…' : 'Send the link'}</button>
          <button type="button" className="btn" onClick={() => switchTo('in')}>Back to sign in</button>
        </div>
      </form>
    ) : (
      <div className="auth-sent">
        <div className="auth-mail" aria-hidden="true">✉</div>
        <h2>Check your e-mail</h2>
        <p>If <strong>{email}</strong> has an account, a link to choose a new password is on its way. It works once and expires in an hour. Check the spam folder too.</p>
        {sent?.dev_link && <div className="notice warn">For testing only: <a href={sent.dev_link}>open the reset link</a>.</div>}
        <p><button type="button" className="btn sm" onClick={() => switchTo('in')}>Back to sign in</button></p>
      </div>
    )
  }

  if (mode === 'sent') {
    return (
      <div className="auth-sent">
        <div className="auth-mail" aria-hidden="true">✉</div>
        <h2>Check your e-mail</h2>
        <p>We sent a verification link to <strong>{email}</strong>. Open it, then come back here and sign in. The link works once and expires in 24 hours.</p>
        {sent?.email_sent === false && (
          <div className="notice warn" role="alert">
            <strong>The e-mail could not be sent.</strong> {sent.mail_problem ?? 'E-mail sending is not set up on this server.'}
            {sent.dev_link && <> For testing, use <a href={sent.dev_link}>this verification link</a>.</>}
          </div>
        )}
        <p className="muted" style={{ marginBottom: '.4rem' }}>Not there? Check the spam folder, or ask for a new link.</p>
        <p style={{ display: 'flex', gap: '.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <button type="button" className="btn sm" onClick={resend}>Send the link again</button>
          <button type="button" className="btn sm" onClick={() => switchTo('in')}>I have verified, sign in</button>
          {resent && <span className="muted" role="status">{resent}</span>}
        </p>
      </div>
    )
  }

  const unverified = err?.code === 'email_not_verified'
  return (
    <>
      <div className="auth-tabs" role="tablist" aria-label="Sign in or create an account">
        <button type="button" role="tab" aria-selected={mode === 'in'} className={mode === 'in' ? 'on' : ''} onClick={() => switchTo('in')}>Sign in</button>
        <button type="button" role="tab" aria-selected={mode === 'up'} className={mode === 'up' ? 'on' : ''} onClick={() => switchTo('up')}>Create account</button>
      </div>
      <form ref={formRef} onSubmit={mode === 'in' ? signIn : signUp} className="loginform">
        {mode === 'up' && (
          <label className="f">Full name
            <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required minLength={2} />
          </label>
        )}
        <label className="f">E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </label>
        <label className="f">Password
          <Pw value={pw} onChange={setPw} autoComplete={mode === 'in' ? 'current-password' : 'new-password'} />
          {mode === 'up' && <small>At least 10 characters, with letters and a digit.</small>}
          {mode === 'in' && <button type="button" className="linkbtn" style={{ justifySelf: 'start', fontWeight: 600, fontSize: '.85rem' }} onClick={() => switchTo('forgot')}>Forgot your password?</button>}
        </label>
        {err && (
          <div className="notice err" role="alert">
            {err.status === 423 ? 'This account is locked for a while after too many attempts. Try again later.'
              : err.status === 401 ? 'E-mail or password is incorrect.' : err.message}
            {unverified && <> <button type="button" className="btn sm" onClick={resend}>Send a new link</button> {resent && <span>{resent}</span>}</>}
          </div>
        )}
        <button type="submit" hidden aria-hidden="true" tabIndex={-1} />
        <div><OrganicButton href="#go" label={busy ? 'Please wait…' : mode === 'in' ? 'Sign in' : 'Create account'}
          onClick={(e) => { e.preventDefault(); if (!busy) formRef.current?.requestSubmit() }} /></div>
      </form>
      <p className="muted auth-note">
        {mode === 'in'
          ? <>New here? <button type="button" className="linkbtn" onClick={() => switchTo('up')}>Create an account</button>. You will verify your e-mail, then tell us who you are.</>
          : <>Already registered? <button type="button" className="linkbtn" onClick={() => switchTo('in')}>Sign in</button>.</>}
      </p>
    </>
  )
}
