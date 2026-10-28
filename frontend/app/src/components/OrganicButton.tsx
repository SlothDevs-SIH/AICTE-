import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

type Props = {
  label?: string
  children?: ReactNode
  to?: string
  href?: string
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  variantColor?: 'primary' | 'secondary'
  arrow?: boolean
  className?: string
}

/** Pill button with fixed SVG end caps; its colours come from CSS variables set by `variantColor`. */
export function OrganicButton({ label, children, to, href, onClick, type = 'button', disabled, size = 'md', variantColor = 'primary', arrow, className = '' }: Props) {
  const cls = `obtn obtn-${size} obtn-${variantColor} ${className}`.trim()
  const inner = (
    <>
      <svg className="obtn-cap obtn-l" viewBox="0 0 18 56" preserveAspectRatio="none" aria-hidden="true"><path d="M18 0C8 0 0 12 0 28s8 28 18 28z" /></svg>
      <span className="obtn-body">{children ?? label}{arrow && <span className="obtn-arrow" aria-hidden="true">→</span>}</span>
      <svg className="obtn-cap obtn-r" viewBox="0 0 18 56" preserveAspectRatio="none" aria-hidden="true"><path d="M0 0c10 0 18 12 18 28S10 56 0 56z" /></svg>
    </>
  )
  if (to) return <Link className={cls} to={to}>{inner}</Link>
  if (href) return <a className={cls} href={href}>{inner}</a>
  return <button className={cls} type={type} disabled={disabled} onClick={onClick}>{inner}</button>
}
