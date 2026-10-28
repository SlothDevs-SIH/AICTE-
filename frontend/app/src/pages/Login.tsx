import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { LoginForm } from '../components/LoginForm'
import { Logo, SyntheticBadge } from '../components/ui'

export default function Login() {
  const { me } = useAuth()
  const loc = useLocation() as any
  if (me) return <Navigate to={loc.state?.from ?? '/app'} replace />
  return (
    <div className="login-wrap">
      <div className="card" style={{ width: 'min(480px, 100%)' }}>
        <Link to="/" className="brand" style={{ marginBottom: '1rem' }}><Logo /> SAMANVAY</Link>
        <h1 style={{ fontSize: '1.6rem' }}>Sign in</h1>
        <p><SyntheticBadge /></p>
        <LoginForm from={loc.state?.from ?? '/app'} />
      </div>
    </div>
  )
}
