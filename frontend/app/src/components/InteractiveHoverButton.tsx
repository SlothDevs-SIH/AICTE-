import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

// Ported from magic ui "interactive-hover-button": a dot that floods the button on hover while the label slides
// out and a copy with an arrow slides in. Plain CSS classes instead of Tailwind.
type Props = {
  children: ReactNode
  to?: string
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  as?: 'button' | 'span'
  className?: string
}

const Arrow = () => (
  <svg className="ihb-arrow" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
)

export function InteractiveHoverButton({ children, to, onClick, type = 'button', disabled, as = 'button', className = '' }: Props) {
  const cls = `ihb ${className}`.trim()
  const inner = (
    <>
      <span className="ihb-in">
        <span className="ihb-dot" />
        <span className="ihb-t">{children}</span>
      </span>
      <span className="ihb-over" aria-hidden="true"><span>{children}</span><Arrow /></span>
    </>
  )
  if (to) return <Link className={cls} to={to}>{inner}</Link>
  if (as === 'span') return <span className={cls}>{inner}</span>
  return <button className={cls} type={type} disabled={disabled} onClick={onClick}>{inner}</button>
}
