import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { DotBackdrop } from '../components/DotBackdrop'
import { AuthPanel } from '../components/AuthPanel'
import { TextAnimate } from '@/components/ui/text-animate'
import { Logo, SyntheticBadge } from '../components/ui'

export default function Login() {
  const { me } = useAuth()
  const loc = useLocation() as any
  if (me) return <Navigate to={loc.state?.from ?? '/app'} replace />
  return (
    <div className="login-wrap">
      <DotBackdrop />
      <div className="card" style={{ width: 'min(480px, 100%)' }}>
        <Link to="/" className="brand" style={{ marginBottom: '1rem' }}><Logo /> SAMANVAY</Link>
        <TextAnimate as="h1" animation="blurInUp" by="word" className="" style={{ fontSize: '1.6rem' }}>Sign in</TextAnimate>
        <p><SyntheticBadge /></p>
        <AuthPanel from={loc.state?.from ?? '/app'} start={new URLSearchParams(loc.search ?? '').get('mode') === 'up' ? 'up' : 'in'} />
      </div>
    </div>
  )
}
