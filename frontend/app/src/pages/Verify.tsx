import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { DotBackdrop } from '../components/DotBackdrop'
import { Logo } from '../components/ui'
import { OrganicButton } from '@/components/ui/organic-button'

/** The page a verification link opens. */
export default function Verify() {
  const [sp] = useSearchParams()
  const token = sp.get('token') ?? ''
  const [state, setState] = useState<'working' | 'ok' | 'bad'>('working')
  const [info, setInfo] = useState('')
  useEffect(() => {
    if (!token) { setState('bad'); setInfo('This link is incomplete.'); return }
    let alive = true
    api('/auth/verify-email', { method: 'POST', body: { token } })
      .then((r) => { if (alive) { setInfo(r.email); setState('ok') } })
      .catch((e: ApiError) => { if (alive) { setInfo(e.message); setState('bad') } })
    return () => { alive = false }
  }, [token])
  return (
    <div className="login-wrap">
      <DotBackdrop />
      <div className="card" style={{ width: 'min(480px, 100%)', textAlign: 'center' }}>
        <Link to="/" className="brand" style={{ marginBottom: '1rem', justifyContent: 'center' }}><Logo /> SAMANVAY</Link>
        {state === 'working' && <p role="status">Checking your link…</p>}
        {state === 'ok' && (
          <>
            <div className="auth-mail ok" aria-hidden="true">✓</div>
            <h1 style={{ fontSize: '1.6rem' }}>E-mail verified</h1>
            <p className="muted">{info} is confirmed. Sign in to continue. You will be asked who you are right after.</p>
            <OrganicButton href="/login" label="Sign in" onClick={(e) => { e.preventDefault(); window.location.assign('/login') }} />
          </>
        )}
        {state === 'bad' && (
          <>
            <div className="auth-mail bad" aria-hidden="true">!</div>
            <h1 style={{ fontSize: '1.6rem' }}>This link did not work</h1>
            <p className="muted">{info} Sign in with your e-mail and password and we will send a new one.</p>
            <OrganicButton href="/login" label="Go to sign in" onClick={(e) => { e.preventDefault(); window.location.assign('/login') }} />
          </>
        )}
      </div>
    </div>
  )
}
